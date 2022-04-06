import datetime
import os
from nlp_utils import extract_noun_chunks, extract_subject, try_parse_word_number
from utils import get_after
from response_model import *
import paho.mqtt.client as mqtt

class IOTController(object):
    def __init__(self, address, broker, user, pswd, debug=False):
        self.DEBUG = debug
        self.ADDRESS = address

        self.client = mqtt.Client('iot_controller', clean_session=True)

        self.client.username_pw_set(username=user, password=pswd)
        
        self.client.connect(*broker)
        self.client.loop_start()

    def log(self, text, end='\n'):
        if self.DEBUG:
            print(text, end=end)

    def light_control(self, command, node_id):
        word_list = command.split()
        if 'on' in word_list or 'max' in word_list:
            self.client.publish(f'home/virtual_assistant/{node_id}/lights_state', 1)
        elif 'off' in word_list:
            self.client.publish(f'home/virtual_assistant/{node_id}/lights_state', 0)
        elif 'dim' in word_list or 'down' in word_list:
            self.client.publish(f'home/virtual_assistant/{node_id}/lights_dim', 1)
        return Response(f'Ok {self.ADDRESS}')