#    Paroli
#
#    copyright 2008 OpenMoko
#
#    This file is part of Paroli.
#
#    Paroli is free software: you can redistribute it and/or modify it
#    under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Paroli is distributed in the hope that it will be useful, but
#    WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#    General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Paroli.  If not, see <http://www.gnu.org/licenses/>.
import os
import logging
logger = logging.getLogger('app.msgs')

import tichy
from tichy import gui
import sys
import dbus
import ecore
import ecore.evas

from tichy.tasklet import Wait, WaitFirst

class MsgsApp2(tichy.Application):
    name = 'Msgs'
    icon = 'icon.png'
    category = 'launcher' # So that we see the app in the launcher
    launcher_info = [tichy.Service.get('Messages').unread]

    def run(self, parent, standalone=False):

        ##set edje file to be used
        ##TODO: make one edje file per plugin
        self.edje_file = os.path.join(os.path.dirname(__file__),'msgs.edj')

        ##get message service and list of all messages
        self.contact_service = tichy.Service.get('Contacts')
        self.contacts = self.contact_service.contacts
        ##sort contact by date
        def comp2(m1, m2):
            return cmp(str(m1.name).lower(), str(m2.name).lower())
         
        self.contacts.sort(comp2)

        ##get message service and list of all messages
        self.msgs_service = tichy.Service.get('Messages')

        self.messages = self.msgs_service.messages

        self.window = gui.elm_list_window(self.edje_file, "main", "list", None, None, True)
        self.edje_obj = self.window.main_layout

        ##sort messages by date
        def comp(m1, m2):
            return cmp(m2.timestamp, m1.timestamp)

        self.list_label = [('label','peer'),('label-number','text'),('status','status'),('direction','direction')]
        
        self.item_list = gui.elm_list(self.messages, self.window, self.edje_file, "item", self.list_label, comp)

        self.edje_obj.add_callback("*", "messaging", self.create_msg)
        self.item_list.add_callback("*", "messaging", self.adv_msg)
        self.item_list.add_callback("save", "*", self.create_contact)
        
        self.contacts.connect('inserted', self.item_list._redraw_view)
        #self.item_list.add_callback("*", "embryo", self.self_test)
        
        self.item_list.add_callback("details", "*", self.msg_details)

        yield tichy.WaitFirst(tichy.Wait(self.window, 'delete_request'),tichy.Wait(self.window, 'back'))
        logger.info('People closing')
        
        del self.item_list
        self.window.delete()
      
    ##DEBUG FUNCTIONS
    ## general output check
    def self_test(self, *args, **kargs):
        txt = "self test called with args: ", args, "and kargs: ", kargs
        logger.info(txt)  
      
    def create_contact(self, emission, source, param, item):
        service = tichy.Service.get('ContactCreate')
        service.create(self.window, item[0].peer).start()  
      
    def create_msg(self, emission, signal, source, item=None):
        service = tichy.Service.get('MessageCreate')
        service.write(self.window, signal).start()
    
    def msg_details(self, emission, signal, source, item):
        number = item[0].peer
        text = item[0].text
        timestamp = item[0].timestamp.local_repr()
        
        detail_layout =  gui.elm_layout(self.window.window, self.edje_file, "message_details")              
        edje_obj = detail_layout.elm_obj.edje_get()
        edje_obj.part_text_set('name-text',str(number).encode('utf8'))
        edje_obj.part_text_set('name-info',str(timestamp).encode('utf8'))
        detail_layout.elm_obj.show()

        textbox = gui.elementary.Entry(self.window.window.elm_obj)
        textbox.entry_set(str(text))
        
        textbox.size_hint_weight_set(1.0, 1.0)
        textbox.editable_set(False)
        textbox.show()
        
        sc = gui.elementary.Scroller(self.window.window.elm_obj)
        sc.content_set(textbox)
        
        detail_layout.elm_obj.content_set('message', sc)
        sc.show()
        
        self.window.main_layout.elm_obj.hide()
        self.window.bg.elm_obj.content_set("content-swallow", detail_layout.elm_obj)
        
        ##add callback for delete button
        edje_obj.signal_callback_add("delete_message", "*", self.delete_msg, item[0], detail_layout)
        
        ##add callback for messaging buttons
        edje_obj.signal_callback_add("*", "messaging", self.adv_msg, item, detail_layout)
        
        ##add callbacks for back button
        edje_obj.signal_callback_add("close_details", "*", detail_layout.delete)
        edje_obj.signal_callback_add("close_details", "*", self.window.restore_orig)
        
        if item[0].direction == 'in' and item[0].status == 'unread':
            item[0].read()
            self.item_list._redraw_view()
            
        
    def adv_msg(self, emission, signal, source, item=None, layout=None):
        service = tichy.Service.get('MessageCreate')
        service.write(self.window, signal, item[0].peer, item[0].text, layout).start()
        
    def delete_msg(self, emission, signal, source, item, layout):
        logger.info("delete message called")
        message = item
        try:
            messages_service = tichy.Service.get('Messages')
            messages_service.remove(message).start()
        except Exception, ex:
            logger.error("Got error %s", str(ex))
        else:
            layout.delete()
            self.window.restore_orig()

##Service to store some info
class MessageCreate(tichy.Service):
    service = 'MessageCreate'

    def __init__(self):
        super(MessageCreate, self).__init__()
    
    @tichy.tasklet.tasklet
    def init(self):
        yield self._do_sth()
        
    def _do_sth(self):
        pass    
        
    def write(self, window, mode, number="", txt="", layout=None):
        sms_service = tichy.Service.get('SMS')
        sms = sms_service.create(number, txt)
        return MsgsWrite(window, sms, mode, layout)

class MsgsWrite(tichy.Application):

    ###modes:
    # reply - get number, only allow editing of text
    # forward - get text, add recipient number and fill entry with reply text
    # new - new text, new number

    name = 'MsgsWriteApp'
    
    def run(self, parent, sms, mode, layout=None, *args, **kargs):
        try:
          self.edje_file = os.path.join(os.path.dirname(__file__), 'msgs.edj')
          number_layout = 0
          text_layout = 0
          send = 0
          number = ""
          full = False
          
          self.window = parent
          
          if layout != None:
              layout.elm_obj.hide()
          
          if mode != "reply":
              full = True
              number = ""
          else:
              sms.text = ""
          
          while True:
          
              if full:
                
                  if number_layout == 0:

                      number_layout =  gui.elm_layout(parent.window, self.edje_file, "edit_number")
                          
                      edje_obj = number_layout.elm_obj.edje_get()
                  
                      edje_obj.part_text_set('num_field-text', number)
                  
                      number_layout.elm_obj.show()
                      
                      parent.main_layout.elm_obj.hide()
                      
                  else:
                      logger.info("back pressed in text")
                      number_layout.elm_obj.show()
                  
                  edje_obj.signal_callback_add("num_field_pressed", "*", self.num_field_action)
                  self.number_layout = number_layout
                  parent.bg.elm_obj.content_set("content-swallow", number_layout.elm_obj)
                  
                  i, args = yield tichy.WaitFirst(Wait(number_layout, 'back'), Wait(number_layout, 'next'))
                  
                  if i == 0: #back
                      break
                      
                  if i == 1: #next
                      number_layout.elm_obj.hide()
                      number = edje_obj.part_text_get('num_field-text')
                      sms.peer = number
                  
              if sms.text == "" or mode == "forward":
                  
                  text_layout = gui.elm_layout(parent.window, self.edje_file, "CreateText")
                  
                  text_layout.elm_obj.layer_set(99)
                  
                  edje_obj = text_layout.elm_obj.edje_get()
                  
                  text_layout.elm_obj.show()
                  
                  parent.main_layout.elm_obj.hide()
                  
                  parent.bg.elm_obj.content_set("content-swallow", text_layout.elm_obj)
                  
                  textbox = gui.elementary.Entry(parent.window.elm_obj)
          
                  textbox.color_set(255, 255, 255, 255)
          
                  textbox.entry_set("Just a stupid test text")
                  
                  textbox.size_hint_weight_set(1.0, 1.0)
        
                  sc = gui.elementary.Scroller(parent.window.elm_obj)
                  sc.content_set(textbox)
                  
                  text_layout.elm_obj.content_set('entry', sc)
                  
                  sc.show()
                  
                  textbox.editable_set(True)        
                  
                  textbox.focus()
                  textbox.show()
              
              logger.info("just before waiting")
              i, args = yield tichy.WaitFirst(Wait(text_layout, 'back'), Wait(text_layout, 'send'))
              if i == 0: #back
                  if full:
                      text_layout.elm_obj.hide()
                      continue
                  else:
                      print "breaking"
                      break
              if i == 1: #send
                  send = 1
                  break
          
          logger.info("broke loop")
          if send == 1:
              text = str(textbox.entry_get()).replace("<br>","")
              sms.text = text.strip()
              text_layout.elm_obj.edje_get().signal_emit("save-notice","*")
              yield self.send_sms(sms)
        
          if number_layout:
              number_layout.delete()
              
          if text_layout:
              text_layout.delete()
              parent.window.elm_obj.keyboard_win_set(0)
          
          if layout != None:
              layout.elm_obj.show()
          else:
              parent.restore_orig()    
          
          ret = "done"
          
          yield ret
          
        except Exception, e:
            print e
            print Exception
    
    ## switch to either open contacts or save number
    def num_field_action(self, emission, signal, source):
        self.num_field(emission, signal, source).start()
    
    @tichy.tasklet.tasklet
    def num_field(self, emission, signal, source):
        logger.info("num field pressed")
        number = emission.part_text_get('num_field-text')
        
        if number == None or len(number) == 0:
            logger.info("no number found")
            createService = tichy.Service.get('ContactCreate')
            num = yield createService.contactList(self.window, self.number_layout)
            emission.part_text_set('num_field-text', str(num.tel))
    
    @tichy.tasklet.tasklet
    def send_sms(self, sms):
        """tasklet that performs the sending process

        connects to SIM service and tries sending the sms, if it fails it opens an error dialog, if it succeeds it deletes the edje window it it given
        """
        logger.info("send message called")
        try:
            message_service = tichy.Service.get('Messages')
            message = message_service.create(number=sms.peer, text=sms.text, direction='out')
            logger.info("sending message: %s to : %s", sms.text, sms.peer)
            yield message.send()
        except Exception, ex:
            logger.error("Got error %s", ex)
    
    def callback(self, *args, **kargs):
        print args
        print kargs
    
    def err_callback(self, *args, **kargs):
        print args
        print kargs