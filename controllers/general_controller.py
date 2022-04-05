import pywhatkit
import datetime
import wikipedia
import json
import requests
import geocoder
import os
import wolframalpha
from nlp_utils import extract_noun_chunks, extract_subject, try_parse_word_number
from utils import get_after
from response_model import *

class GeneralController(object):
    def __init__(self, address, location, debug=False):
        self.DEBUG = debug
        self.ADDRESS = address
        self.hot = 85
        self.cold = 55
        self.LOCATION = location
        self.OWM_API_KEY = os.environ['OWM_API_KEY']
        self.wolf_client = wolframalpha.Client(os.environ['WOLFRAM_API_KEY'])

    def log(self, text, end='\n'):
        if self.DEBUG:
            print(text, end=end)

    def search(self, command):
        subject = extract_subject(command)
        if subject:
            self.log(f'Searching {subject}...')
            try:
                return wikipedia.summary(subject, 1)
            except:
                return Response(f'I had trouble finding information on {subject}')
        else:
            return Response(f'I didnt catch that {self.ADDRESS}, what did you want to know?')

    def get_time(self, command):
        time = datetime.datetime.now().strftime('%I:%M %p')
        return Response(f'It is {time}')

    def play(self, command):
        components = extract_subject(command)
        song = ' by '.join(components)
        if song:
            pywhatkit.playonyt(song)
            return Response(f'Playing {song}')
        else:
            return Response(f'I didnt catch that {self.ADDRESS}, did you want me to play something?')

    def get_weather(self, command):
        city = None
        location = ''
        if 'in' in command.split():
            city = get_after(command, 'in')
            location = f'in {city}'
        elif self.LOCATION:
            city = self.LOCATION
        else:
            city = geocoder.ip('me').city
            location = f'in {city}'
        # Query weather api
        weather_json = requests.get(f'http://api.openweathermap.org/data/2.5/weather?q={city}&appid={self.OWM_API_KEY}&units=imperial').json()
        # Parse results
        city = weather_json['name']
        temp = int(weather_json['main']['temp'])
        feels = int(weather_json['main']['feels_like'])
        description = weather_json['weather'][0]['main'].lower()
        #Create response
        response = ''
        temp_str = f'the temperature {location} is {temp} degrees'
        if temp != feels:
            temp_str += f', it feels like {feels}'

        if 'clouds' in description:
            description = 'it is overcast'
        if 'clear' in description:
            description = 'the skies are clear'

        command_words = command.split()

        if 'weather' in command_words:
            return Response(f'{response} {temp_str} and {description}')
        
        '''
        better way to do this
        1. determine if the question is an 'is it' question
        2. determine what the 'is it' is about (hot, cold, comfortable)
        3. determine if the response is Yes, No
        4. build the rest of the response
        '''
        if 'hot' in command_words or 'warm' in command_words:
            if temp > self.hot:
                response = f'Yes, it is quite hot {location}, {temp} degrees to be exact'
            elif temp > self.cold:
                response = f'No, {location} it is actually a comfortable {temp} degrees'
            else:
                response = f'No, it is actually quite cold {location}, {temp} degrees to be exact'

        elif 'cold' in command_words or 'cool' in command_words or 'chilly' in command_words:
            if temp > self.hot:
                response = f'No, it is actually quite hot {location}, {temp} degrees to be exact'
            elif temp > self.cold:
                response = f'No, {location} it is actually a comfortable {temp} degrees'
            else:
                response = f'Yes, it is quite cold {location}, {temp} degrees to be exact'
        
        elif 'comfortable' in command_words or 'nice' in command_words:
            if temp > self.hot:
                response = f'No, it is actually quite hot {location}, {temp} degrees to be exact'
            elif temp > self.cold:
                response = f'Yes, {location} it is a comfortable {temp} degrees'
            else:
                response = f'No, it is actually quite cold {location}, {temp} degrees to be exact'

        elif 'temp' in command_words or 'temperature' in command_words:
            response = temp_str

        if ' skies ' in command_words or ' sky ' in command_words:
            if not response:
                response = f'{description} {location}'
            else:
                response += f', and {description}'

        return Response(response)

    def volume(self, text):
        for word in text.split(' '):
            value = try_parse_word_number(word)
            if value != None:
                response = f'Setting the volume to {value}'
                if value <= 10:
                    value *= 10
                action = Action('set_volume',value)
                return Response(response, action)
        return Response('What level should I set the volume too?')

    def answer_math(self, text):
        #todo
        res = self.wolf_client.query(text)
        answer = next(res.results).text
        for word in answer.split():
            answer_number = try_parse_word_number
            if answer_number:
                if type(answer_number) == float:
                    answer_number = '{:.2f}'.format(answer_number)
                answer.replace(word, f'{answer_number}')
        return Response(f'{answer}')