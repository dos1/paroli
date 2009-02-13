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
from tichy.service import Service
import dbus
import ecore
import ecore.evas
      

class MsgsApp(tichy.Application):
    name = 'Msgs'
    icon = 'icon.png'
    category = 'launcher' # So that we see the app in the launcher
    
    def run(self, parent, standalone=False):
        
        self.standalone = standalone
        
        ##create main edje object, the evas object used to generate edje objects
        self.main = parent

    #try:
        ##set the title of the window
        if self.main.etk_obj.title_get() != 'Home':
            self.main.etk_obj.title_set('Msgs')

      
        ##set edje file to be used
        ##TODO: make one edje file per plugin
        self.edje_file = os.path.join(os.path.dirname(__file__),'msgs.edj')

        ##get message service and list of all messages
        self.msgs_service = tichy.Service('Messages')
        self.messages = self.msgs_service.messages

        ##sort messages by date
        def comp(m1, m2):
            return cmp(m2.timestamp, m1.timestamp)

        self.messages.sort(comp)

        self.list_label = [('label','peer'),('label-number','text')]
        self.messages_list = gui.EvasList(self.messages, self.main, self.edje_file, "message_item", self.list_label)

        self.messages_swallow = self.messages_list.get_swallow_object()

        self.messages_list.add_callback("contact_details", "contacts", self.open_msg_detail_window)

        self.edje_obj = gui.EdjeWSwallow(self.main, self.edje_file, 'messages', "message-items")
        
        self.edje_obj.embed(self.messages_swallow,self.messages_list.box,"message-items")
        #sms_service = tichy.Service('SMS')
        sms = empty_sms()
        self.edje_obj.add_callback("create_message", "message-items", self.open_enter_number, sms)
        
        if self.standalone:
            self.edje_obj.Edje.size_set(480,550)
            self.edje_obj.Edje.pos_set(0,30)
        else:
            self.edje_obj.Edje.size_set(480,590)
        
        self.edje_obj.show()

        ##wait until main object emits back signal or delete is requested
        yield tichy.WaitFirst(tichy.Wait(self.main, 'delete_request'),tichy.Wait(self.main, 'back_Msgs'))
        logger.info('Msgs closing')
        ##remove all children -- edje elements

    #finally:
        if self.standalone:
          #try:
          self.edje_obj.delete()
          #except Exception, e:
              #print Exception, e
        else:
            self.edje_obj.delete()
            self.main.etk_obj.hide()   # Don't forget to close the window

    ##DEBUG FUNCTIONS 
    ## general output check
    def self_test(self, *args, **kargs):
        txt = "self test called with args: ", args, "and kargs: ", kargs
        logger.info(txt)
    
    ## SUBWINDOW FUNCTIONS
    ## open subwindow showing message-details
    def open_msg_detail_window(self, emission, signal, source, item):
        canvas = item[2]
        edje_obj = item[1]
        message = item[0]
        
        new_edje = gui.EdjeWSwallow(self.main, self.edje_file, 'message_details', 'message', self.edje_obj.Windows )
        
        ##set sender/recipient
        new_edje.Edje.part_text_set('name-text',str(message.peer).encode('utf8'))
        
        ##set time of message sent/received
        new_edje.Edje.part_text_set('name-info',str(message.timestamp))
    
        ##set number
        new_edje.Edje.part_text_set('number-text',str(message.peer.value).encode('utf8'))
    
        ##set text
        ##generate text field edje
        text_obj = gui.EdjeObject(self.main, self.edje_file, 'text_grp', new_edje.Windows )
        ##set text field in edje
        text_obj.Edje.part_text_set('message-block', unicode(message.text).encode('utf8'))
        ##show edje object
        text_obj.show()
        ##get text size - hack to make scrollable
        message_length = text_obj.Edje.part_object_get("message-block").size_get()
        ##set edje obj size to make scrollable
        text_obj.Edje.size_set(message_length[0],message_length[1])
        ##create scroll object
        text_obj_scroller = gui.ScrollerEdje(text_obj.Edje)
        ##embed scroll object
        new_edje.embed(text_obj_scroller.scrollbox, text_obj_scroller.box, 'message')
        ##show contents of scroll object - Needed?
        text_obj_scroller.box.show_all()
        ##add callback for back button
        new_edje.Edje.signal_callback_add("close_details", "*", new_edje.delete)
        ##add callback for delete button
        new_edje.Edje.signal_callback_add("delete_message", "*", self.delete_sms, item)
        ##set layer of edje object
        new_edje.Edje.layer_set(3)
        ##move edje object down to show top-bar
        new_edje.Edje.pos_set(0,40)
        ##show edje window
        new_edje.Edje.show()   
    
    ## open subwindow to create new message (enter recipients)
    def open_enter_number(self, emission, signal, source, sms):
        ##load main gui
        new_edje = gui.EdjeObject(self.main,self.edje_file,'dialpad', self.edje_obj.Windows)
        
        ##set dialpad value to '' to not have NoneType problems
        new_edje.Edje.part_text_set('num_field-text','')
        ## show main gui
        new_edje.Edje.layer_set(3)
        #if self.standalone == 1:
        new_edje.Edje.size_set(480,540)
        new_edje.Edje.pos_set(0,40)
        new_edje.Edje.show()   
        ##add window actions
        ##close window
        new_edje.Edje.signal_callback_add("close_details", "*", new_edje.delete)
        ##add contact from phonebook
        #new_edje.Edje.signal_callback_add("num_field_pressed", "*", self.load_phone_book)
        ##go to next step
        new_edje.Edje.signal_callback_add("next-button", "*", sms.set_number, 'num_field-text')
        new_edje.Edje.signal_callback_add("next-button", "*", self.open_new_msg_text_entry, sms, new_edje)
    
    ## open subwindow to create new message (text entry)
    def open_new_msg_text_entry(self, emission, signal, source, sms, window):
        logger.info('got empty_sms with number ' + str(sms.number))
        new_edje = gui.EdjeWSwallow(self.main, self.edje_file, 'message_details', 'message', self.edje_obj.Windows, True)
            
        new_edje.Windows.append(window)
        new_edje.Edje.part_text_set("reply-button-text",'send')
        ##embed scroll object
        tview = gui.etk.TextView()
        tview.theme_file_set(self.edje_file)
        tview.theme_group_set("text_view")
        new_edje.embed(tview, None, 'message')
        ##add callback for back button and send
        new_edje.Edje.signal_callback_add("close_details", "*", new_edje.back)
        new_edje.Edje.signal_callback_add("reply", "*", sms.set_text_from_obj, tview.textblock_get())
        new_edje.Edje.signal_callback_add("reply", "*", self._on_send_sms, sms, new_edje )
        ##set layer of edje object
        new_edje.Edje.layer_set(3)
        ##move edje object down to show top-bar
        new_edje.Edje.pos_set(0,40)
        ##show edje window
        new_edje.Edje.show()
        tview.focus()
        
    ##MISC FUNCTIONS
    #sending
    def _on_send_sms(self, emission, signal, source, sms, window):
        """Called when the user click the send button

        The function will simply start the send_message tasklet
        """
        sending = self.send_sms(emission, signal, source, sms, window).start(err_callback=self.throw)

    @tichy.tasklet.tasklet
    def send_sms(self, emission, signal, source, sms, window):
        """tasklet that performs the sending process
        
        connects to SIM service and tries sending the sms, if it fails it opens an error dialog, if it succeeds it deletes the edje window it it given
        """
        logger.debug("send message called")

        try:
            message_service = tichy.Service('Messages')
            message = message_service.create(number=sms.number, text=sms.text, direction='out')
            logger.info("sending message: %s to : %s", sms.text, sms.number)
            yield message.send()

        except Exception, ex:
            # XXX: we should differentiate between different errors
            # DON'T raise here, as it will close the app and that only half way
            logger.error("Got error %s", ex)
            yield tichy.Service('Dialog').error(self.main, ex)
            # XXX: at this point we should show an error box or do something
            
        else:
            
            #self.contact_objects_list.box.box.redraw_queue()
            #self.contact_objects_list.box.box.show_all()
            window.delete()
  
    #deleting
    def delete_sms(self, emission, signal, source, item):
        logger.info("delete message called")
        canvas = item[2]
        edje_obj = item[1]
        message = item[0]
        
        try:
            messages_service = Service('Messages')
            messages_service.remove(message).start()
        except Exception, ex:
            logger.error("Got error %s", str(ex))
            #yield tichy.Service('Dialog').error(self.main, ex)
        else:    
            #canvas.remove_all()
            emission.data['EdjeObject'].delete()
  
class empty_sms():
    def __init__(self):
        self.number = None
        self.text = ''

    def set_number(self, emission, source, signal, part):
        self.number = emission.part_text_get(part)
      
    def set_text_from_obj(self, emission, source, signal, text_obj):
        self.text = text_obj.text_get(0)

        
    ##BELOW    --->     TO BE REPLACED / REWRITTEN
    ##functions for message app
    ##create new message
    ## step one (enter recipients)
    def create_message(self, emission, source, param, original_message=None, text=''):
        #print dir(emission)
        #print "create message called"
        ##load main gui
        new_edje = gui.edje_gui(self.main,'dialpad_numbers',self.edje_file)
        
        ##set dialpad value to '' to not have NoneType problems
        new_edje.edj.part_text_set('num_field-text','')
        ## show main gui
        new_edje.edj.layer_set(3)
        if self.standalone == 1:
            new_edje.edj.size_set(480,600)
        new_edje.edj.pos_set(0,40)
        new_edje.edj.show()   
        ##add num-pad actions
        ##delete digit
        new_edje.edj.signal_callback_add("del-button", "*", self.number_edit_del)
        ##add digit
        new_edje.edj.signal_callback_add("add_digit", "*", self.add_digit)
        ##add window actions
        ##close window
        new_edje.edj.signal_callback_add("close_details", "*", self._close)
        ##add contact from phonebook
        new_edje.edj.signal_callback_add("num_field_pressed", "*", self.load_phone_book)
        ##go to next step
        new_edje.edj.signal_callback_add("next-button", "*", self.create_message_2, new_edje,'num_field-text',text, original_message)
        
    ## step two (enter message)    
    def create_message_2(self, emission, source, param, step_1, part_text_field='num_field-text',message='', original_message=''):
        ##get numbers from dialpad
        numbers = emission.part_text_get(part_text_field).split(' ')
        #print numbers
        ##load main gui
        new_edje = gui.edje_gui(self.main,'create_message',self.edje_file)
        ## show main gui
        new_edje.edj.layer_set(3)
        if self.standalone:
            new_edje.edj.size_set(480,600)
        new_edje.edj.pos_set(0,40)
        new_edje.edj.show()  
        self.open_keyboard()
        text = message
        textbox = gui.etk.TextView()
        textbox.size_request_set(200,180)
        textbox.textblock_get().text_set(text,0)
        #textbox.theme_file_set(self.edje_file)
        box = gui.edje_box(self,'V',1)
        box.box.append(textbox, gui.etk.VBox.START, gui.etk.VBox.NONE,0)
        new_edje.add(box.scrolled_view,box,"message")
        textbox.focus()
        box.box.show_all()
        
        ##set window actions
        ##close window
        new_edje.edj.signal_callback_add("back", "*", new_edje.close_extra_child)
        ##go to next step
        new_edje.edj.signal_callback_add("send", "*", self._on_send_message, numbers, textbox, step_1, new_edje, original_message)
    
    
    
    ##show message details
    def show_details(self, emission, source, param, message, canvas_obj):
        print "show details called"
        time = message.timestamp
        text = str(message.text).encode('utf8')
        print text
        new_edje = gui.edje_gui(self.main,'message_details',self.edje_file)
        new_edje.edj.part_text_set('name-text',str(message.peer).encode('utf8'))
        new_edje.edj.part_text_set('name-info',str(time))
        new_edje.edj.part_text_set('number-text',str(message.peer.value).encode('utf8'))
        new_edje.edj.part_text_set('message-text',text)
        new_edje.edj.signal_callback_add("reply", "*", self.reply, message, new_edje)
        new_edje.edj.signal_callback_add("forward", "*", self.forward, message, new_edje)
        new_edje.edj.signal_callback_add("close_details", "*", self._close)
        new_edje.edj.signal_callback_add("delete_message", "*", self.delete_message, message, new_edje,emission, canvas_obj)
        message.read()
        new_edje.edj.layer_set(3)
        if self.standalone:
            new_edje.edj.size_set(480,600)
        new_edje.edj.pos_set(0,40)
        new_edje.edj.show()   

    def _on_send_message(self, emission, source, param, numbers, textbox, step_1, step_2, original_message=None):
        """Called when the user click the send button

        The function will simply start the send_message tasklet
        """
        self.send_message(emission, source, param, numbers, textbox, step_1, step_2, original_message).start(err_callback=self.throw)
    
    @tichy.tasklet.tasklet
    def send_message(self, emission, source, param, numbers, textbox, step_1, step_2, original_message=None):
        """tasklet that performs the sending process"""
        logger.debug("send message called")
        numbers = numbers
        text = textbox.textblock_get().text_get(0)

        try:
            step_2.close_extra_child(emission,source,param)
            step_1.delete(emission,source,param)
            if original_message != None:
                original_message.delete(emission, source, param)
            
            message_service = tichy.Service('SMS')
            for i in numbers:
                message = message_service.create(number=i, text=text, direction='out')
                logger.info("would send message: %s to : %s", text, i)
                yield message.send()
                self.contact_objects_list.generate_single_item_obj(i,text,message)

            self.contact_objects_list.box.box.redraw_queue()
            self.contact_objects_list.box.box.show_all()
            self.close_keyboard()
        except Exception, ex:
            logger.error("Got error %s", ex)
            raise
            # XXX: at this point we should show an error box or do something
        
    ##delete message INCOMPLETE
    def delete_message(self,emission, source, param, message, details_window, messages_edje_obj, canvas_obj):
        print "delete message called"
        canvas_obj.remove_all()
        details_window.edj.delete()
        messages_service = Service('Messages')
        #if message.direction == 'in':
        messages_service.remove(message).start()
        #else:
            #messages_service.outbox.remove(message)
    
    ##reply to message INCOMPLETE
    def reply(self, emission, source, param, message, details_window):
        print "reply called, to number: ", str(message.peer).encode('utf8')
        self.create_message_2(emission, source, param, details_window, 'number-text')
    
    ##forward message INCOMPLETE
    def forward(self, emission, source, param, message, original_message):
        text = str(message.text).encode('utf8')
        print "forward called, of message: ", text
        self.create_message(emission, source, param, original_message, text)
    
    ##general functions on module
    ##close window
    def _close(self,emission, source, param):
        emission.delete()
    
    ##load phonebook
    def load_phone_book(self, emission, source, param):
        #print "load phone book called"
        self.close_keyboard()
        try:
            new_edje = gui.edje_gui(self.main,'messages-people',self.edje_file)
            #new_edje.name = 'messages_phonebook'
            new_edje.edj.name_set('contacts_list')
        except Exception,e:
            print e
        try:
            self.extra_child = new_edje
            new_edje.edj.layer_set(3)
            if self.standalone == 1:
                new_edje.edj.size_set(480,600)
            new_edje.edj.edj.pos_set(0,40)
            new_edje.edj.show()
        except Exception,e:
            print e
        print "done"
        try:
            contacts_box = gui.edje_box(self,'V',1)
        except Exception,e:
            print e
        print "done2"
          
        try: 
            self.contact_objects_list = gui.contact_list(self.phone_book,contacts_box,self.main.etk_obj.evas,self.edje_file,'message-contacts_item',self, 'contacts' , emission)
        except Exception,e:
            print e 
        print "done3"
        
        try: 
            to_2_swallowed = contacts_box.scrolled_view
        except Exception,e:
            print e 
        print "done4"
        
        try: 
            #print "new_edje.add(to_2_swallowed,contacts_edje)"
            new_edje.add(to_2_swallowed,contacts_box,"items")
        except Exception,e:
            print e 
        print "done5"
        
        try: 
            contacts_box.box.show()
        except Exception,e:
            print e 
        print "done6"
    
    ##add contact to recipients
    def add_recipient(self, emission, source, param, contact, dial_pad):
        print "add recipient called"
        old = dial_pad.part_text_get('num_field-text')
        if len(old) == 0:
            new = str(contact.tel)
        else:
            new = old + ' ' + str(contact.tel)
        
        dial_pad.part_text_set('num_field-text', new)
        self.extra_child.close_extra_child(emission, source, param)
        #self.open_keyboard()
    
    ##add digit on dialpad like window
    def add_digit(self,emission, source, param):
        print "add digit called"
        new_sign = param
        value = emission.part_text_get('num_field-text')
        if value == None:
            new = str(new_sign)
        else:
            new = str(value)+str(new_sign)
          
        emission.part_text_set('num_field-text',new)
    
    ##delete digit on dialpad like window
    def number_edit_del(self,emission, source, param):
        print "number_edit del called"
        value = emission.part_text_get("num_field-text")
        if len(value) != 0:
            emission.part_text_set("num_field-text",value[:-1])
    
    def close_keyboard(self,*args):
        print "close keyboard called"
        self.main.etk_obj.x_window_virtual_keyboard_state_set(ecore.x.ECORE_X_VIRTUAL_KEYBOARD_STATE_OFF)
    
    def open_keyboard(self,*args):
        print "open keyboard called"
        self.main.etk_obj.x_window_virtual_keyboard_state_set(ecore.x.ECORE_X_VIRTUAL_KEYBOARD_STATE_ON)
    
    
    def listen(self, emission, source, param):
        print source
        print param
        print emission.part_drag_value_get('clickable_blocker')
    
    def call_contact(self, emission, source, param):
        number = emission.part_text_get('number-text')
        name = emission.part_text_get('name-text')
        caller_service = Service('Caller')
        my_call = caller_service.call(emission, number, name)
        my_call.start()
        try:
            emission.delete()
        except Exception,e:
            print e

    def edit_number_type(self,emission, source, param, contact, details_window):
        print "edit number type called"
    
        number = emission.part_text_get('number-text')
        
        new_edje = gui.edje_gui(self.main,'edit-number-type',self.edje_file)
        #new_edje.edj.part_text_set('num_field-text',number)
        new_edje.edj.signal_callback_add("num_type_clicked", "*", self.edit_number, number, contact, details_window,new_edje)
        new_edje.edj.signal_callback_add("back", "*", new_edje.delete)
        #new_edje.edj.signal_callback_add("add_digit", "*", self.add_digit)
        
        new_edje.edj.layer_set(4)
        if self.standalone:
            new_edje.edj.size_set(480,600)
        new_edje.edj.edj.pos_set(0,40)
        new_edje.edj.show()
    
    def edit_number(self,emission, source, param, number, contact, details_window,first_window):
        print "edit number called"
        
        #number = emission.part_text_get('number-text')
        #last_window = emission
        number_type = param
        new_edje = gui.edje_gui(self.main,'dialpad_numbers',self.edje_file)
        new_edje.edj.part_text_set('num_field-text',number)
        new_edje.edj.signal_callback_add("del-button", "*", self.number_edit_del)
        new_edje.edj.signal_callback_add("back", "*", new_edje.delete)
        new_edje.edj.signal_callback_add("add_digit", "*", self.add_digit)
        new_edje.edj.signal_callback_add("save-button", "*", self.save_contact_number, 'number' , number_type, contact, details_window)
        new_edje.edj.signal_callback_add("save_successful", "*", first_window.delete)
        
        new_edje.edj.layer_set(4)
        if self.standalone:
            new_edje.edj.size_set(480,600)
        new_edje.edj.edj.pos_set(0,40)
        new_edje.edj.show()
    
    def add_number_new_contact(self,emission, source, param):
        print "add new number called"
        
        #number = emission.part_text_get('number-text')
        #me = 'mirko'
        new_edje = gui.edje_gui(self.main,'dialpad_numbers',self.edje_file)
        #new_edje.edj.part_text_set('num_field-text',number)
        new_edje.edj.signal_emit('new_contact_mode','*')
        new_edje.edj.signal_callback_add("del-button", "*", self.number_edit_del)
        new_edje.edj.signal_callback_add("back", "*", new_edje.delete)
        new_edje.edj.signal_callback_add("add_digit", "*", self.add_digit)
        new_edje.edj.signal_callback_add("next-button", "*", self.add_name_new_contact,first_window=new_edje)
        
        new_edje.edj.layer_set(4)
        if self.standalone:
            new_edje.edj.size_set(480,600)
        new_edje.edj.edj.pos_set(0,40)
        new_edje.edj.show()
    

    
    def edit_name(self,emission, source, param, contact, first_window):
        print "edit name called"
        
        name = emission.part_text_get('name-text')
        
        new_edje = gui.edje_gui(self.main,'edit-name',self.edje_file)
        name_field = gui.entry(name,False)
        new_edje.text_field = name_field.entry
        box = gui.edje_box(self,'V',1)
        box.box.append(name_field.entry, gui.etk.VBox.START, gui.etk.VBox.NONE,0)
        new_edje.add(box.scrolled_view,box,"name-box")
        new_edje.edj.signal_emit('new_contact_mode','*')
        #new_edje.edj.part_text_set('num_field-text',number)
        new_edje.edj.signal_callback_add("next_step", "*", self.edit_name_info, contact, first_window,new_edje)
        new_edje.edj.signal_callback_add("close_w_textfield", "*", new_edje.close_extra_child)
        #new_edje.edj.signal_callback_add("del-button", "*", self.number_edit_del)
        
        new_edje.edj.layer_set(4)
        if self.standalone:
            new_edje.edj.size_set(480,600)
        new_edje.edj.edj.pos_set(0,40)
        new_edje.edj.show()
    
    def edit_name_info(self,emission, source, param, contact, first_window, last_window):
        print "edit info called"
        
        #name = emission.part_text_get('name-text')
        
        new_edje = gui.edje_gui(self.main,'edit-name',self.edje_file)
        info_field = gui.entry('info',False)
        new_edje.text_field = info_field.entry
        box = gui.edje_box(self,'V',1)
        box.box.append(info_field.entry, gui.etk.VBox.START, gui.etk.VBox.NONE,0)
        new_edje.add(box.scrolled_view,box,"name-box")
        #new_edje.edj.part_text_set('num_field-text',number)
        new_edje.edj.part_text_set('name-text','info')
        info = new_edje.text_field
        name = last_window.text_field
        #print name.text_get()
        new_edje.edj.signal_callback_add("save_contact", "*", self.save_contact_number, 'name' , new_edje.text_field, contact, first_window, name)
        new_edje.edj.signal_callback_add("close_w_textfield", "*", last_window.close_extra_child)
        new_edje.edj.signal_callback_add("save_successful", "*", new_edje.close_extra_child)
        #new_edje.edj.signal_callback_add("del-button", "*", self.number_edit_del)
        
        new_edje.edj.layer_set(4)
        if self.standalone:
            new_edje.edj.size_set(480,600)
        new_edje.edj.edj.pos_set(0,40)
        new_edje.edj.show()
    
    def add_name_new_contact(self,emission, source, param,first_window=None):
        print "add new name called"
        #print name
        number = emission.part_text_get('num_field-text')
        
        new_edje = gui.edje_gui(self.main,'edit-name',self.edje_file)
        name_field = gui.entry('Name',False)
        new_edje.text_field = name_field.entry
        box = gui.edje_box(self,'V',1)
        box.box.append(name_field.entry, gui.etk.VBox.START, gui.etk.VBox.NONE,0)
        new_edje.add(box.scrolled_view,box,"name-box")
        #new_edje.edj.part_text_set('num_field-text',number)
        new_edje.edj.signal_callback_add("close_w_textfield", "*", new_edje.close_extra_child)
        new_edje.edj.signal_callback_add("save_contact", "*", self.save_new_contact,name_object=new_edje,number=number,first_window=first_window)
        #new_edje.edj.signal_callback_add("del-button", "*", self.number_edit_del)
        
        new_edje.edj.layer_set(4)
        if self.standalone:
            new_edje.edj.size_set(480,600)
        new_edje.edj.edj.pos_set(0,40)
        new_edje.edj.show()
    
    def save_contact_number(self,emission,source,param, switch ,info, contact, details_window,name=None):
        if switch == 'number':
            number = emission.part_text_get('num_field-text')
            contact.tel = number
            details_window.edj.part_text_set('number-text', number)
            details_window.edj.part_text_set('number-info', info)
            emission.signal_emit('contact_saved','*')
        elif switch == 'name':
            cinfo = info.text_get()
            cname = name.text_get()
            print dir(emission)
            # contact.name = name
            details_window.edj.part_text_set('name-text', cname)
            details_window.edj.part_text_set('name-info', cinfo)
            emission.signal_emit('contact_name_edit_saved','*')
    
    def save_new_contact(self,emission, source, param,name_object=None,number=None,first_window=None):
        print "save new contact called"
        name = name_object.text_field.text_get()
        number = number
        
        try:
            contact = tichy.Service('Contacts').create(name=str(name), number=str(number))
        except Exception,e:
            print e
        #emission.signal_emit('save-notice','*')
        name_object.edj.delete()
        #contacts_service = Service('Contacts')
        #contacts_service.add(contact)
        #print dir (self.contact_objects_list)
        self.contact_objects_list.generate_single_item_obj(name,number,contact)
        print self.contact_objects_list.box.box.children_get()
        self.contact_objects_list.box.box.redraw_queue()
        self.contact_objects_list.box.box.show_all()
        first_window.edj.delete()
        #print contacts_service.contacts
     
    def on_key(self, w, k):
        self.text.value += k  # The view will automatically be updated
        
    def on_del(self, w):
        self.text.value = self.text.value[:-1]
        
    #def calling(self,orig,orig_parent,emission, source, param):  
        #print "calling"
        #number = emission.part_text_get("num_field-label")
        #print number
        #yield Caller(self.edje_obj, number)
        
    def on_call(self, b):
        yield Caller(self.window, self.text.value)
       
    #def self_test(self,emission, source, param):
        #print "emission: ", str(emission)
        #print "source: ", str(source)
        #print "param: ", str(param)