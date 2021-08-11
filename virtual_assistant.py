from utils import encode_word_vec, pad_sequence
import numpy as np
from keras.models import load_model
import pickle
from controllers.chat_controller import ChatController
from controllers.planning_controller import PlanningController
from controllers.general_controller import GeneralController

class VirtualAssistant(object):
    def __init__(self):
        self.NAME = 'david'
        self.ADDRESS = 'sir'

        self.intent_model = load_model('intent_model.h5')
        self.word_to_int, self.int_to_label, self.seq_length = pickle.load(open('vocab.p', 'rb'))
        self.CONF_THRESH = 85

        self.chatControl = ChatController()
        self.planningControl = PlanningController(self.ADDRESS)
        self.generalControl = GeneralController(self.ADDRESS, 'gloucester')        

        intent, conf = self.predict_intent('bigblankbig')

    def understand(self, command):

        if f'hey {self.NAME}' == command or f'yo {self.NAME}' == command or self.NAME == command:
            return (f'Yes {self.ADDRESS}?', 'wakeup', 100.0)
        elif 'shut down' in command:
            return (f'Ok {self.ADDRESS}, see you soon', 'shutdown', 100.0)
        else:
            words = command.split()
            if self.NAME in words[0]:
                words[0] = ''
            command = ' '.join(words)
        
            if command:
                response = ''
                intent, conf = self.predict_intent(command.replace(self.NAME, 'bignamebig'))
                
                print(f'intent: {intent} | conf: {conf}')

                if conf > self.CONF_THRESH:
                    if intent == 'greeting':
                        response =  self.greeting(command)

                    if intent == 'goodbye':
                        response = self.goodbye(command)

                    if intent == 'schedule':
                        response = self.planningControl.check_calendar(command)

                    if intent == 'play':
                        #need to work on extracting subject
                        response = self.generalControl.play(command)

                    if intent == 'time':
                        response = self.generalControl.get_time(command)
                    
                    if intent == 'weather':
                        response = self.generalControl.get_weather(command)

                    if intent == 'lookup':
                        response = self.generalControl.search(command)

                    if intent == 'reminder':
                        #todo
                        response = self.planningControl.set_reminder(command)

                    if intent == 'math':
                        #todo
                        response = self.generalControl.answer_math(command)
                
                if not response:
                    response = self.chatControl.chat(command)

                return (response, intent, conf)

            else:
                return (None, '', 0.0)
            

    def greeting(self, command):
        if 'morning' in command:
            return f'Good morning {self.ADDRESS}'
        elif 'afternoon' in command:
            return f'Good afternoon {self.ADDRESS}'
        elif 'night' in command:
            return f'Good night {self.ADDRESS}'
        return f'Hello {self.ADDRESS}'

    def goodbye(self, command):
        return f'Goodbye {self.ADDRESS}, I\'ll talk to you later'

    def predict_intent(self, text):
        encoded = encode_word_vec(text, self.word_to_int)
        padded = pad_sequence(encoded, self.seq_length)
        prediction = self.intent_model.predict(np.array([padded]))[0]
        argmax = np.argmax(prediction)
        return self.int_to_label[argmax], round(float(prediction[argmax])*100, 3)

    def get_name(self):
        return self.NAME

    def get_address(self):
        return self.ADDRESS

    def reset_chat(self):
        self.chatControl.reset_chat()
            
