import datetime
import os
from nlp_utils import extract_noun_chunks, extract_subject, try_parse_word_number
from utils import get_after
from response_model import *
import paho.mqtt.client as mqtt

class IOTController(object):
    def __init__(self, address, broker, debug=False):
        self.DEBUG = debug
        self.ADDRESS = address

        self.client = mqtt.Client("iot_controller")
        
        self.client.connect(*broker)
        self.client.loop_start()

    def log(self, text, end='\n'):
        if self.DEBUG:
            print(text, end=end)

    def light_control(self, command):
        word_list = command.split()
        if 'on' in word_list or 'max' in word_list:
            self.client.publish('home/virtual_assistant/bedroom_lights_state', 1)
        elif 'off' in word_list:
            self.client.publish('home/virtual_assistant/bedroom_lights_state', 0)
        elif 'dim' in word_list or 'down' in word_list:
            self.client.publish('home/virtual_assistant/bedroom_lights_dim', 1)
        return Response(f'Ok {self.ADDRESS}')