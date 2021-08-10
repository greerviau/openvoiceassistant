import pywhatkit
import datetime
import wikipedia
import json
import requests
import geocoder
from utils import extract_subject
from creds import OWM_API_KEY

class GeneralController(object):
    def __init__(self, address, location):
        self.ADDRESS = address
        self.hot = 85
        self.cold = 55
        self.LOCATION = location
        self.OWM_API_KEY = os.environ['OWM_API_KEY']

    def search(self, command):
        subject = extract_subject(command)
        if subject:
            print(f'Searching {subject}...')
            try:
                return wikipedia.summary(subject, 1)
            except:
                return f'I had trouble finding information on {subject}'
        else:
            return f'I didnt catch that {self.ADDRESS}, what did you want to know?'

    def get_time(self, command):
        time = datetime.datetime.now().strftime('%I:%M %p')
        return f'It is {time}'

    def play(self, command):
        subject = extract_subject(command)
        if subject:
            pywhatkit.playonyt(subject)
            return f'Playing {subject}'
        else:
            return f'I didnt catch that {self.ADDRESS}, did you want me to play something?'

    def get_weather(self, command):
        city = None
        location = ''
        if 'in' in command:
            city = get_after(command, 'in')
            location = f' in {city} '
        elif self.LOCATION:
            city = self.LOCATION
        else:
            city = geocoder.ip('me').city
            location = f' in {city} '
        # Query weather api
        weather_json = requests.get(f'http://api.openweathermap.org/data/2.5/weather?q={city}&appid={self.OWM_API_KEY}&units=imperial').json()
        # Parse results
        city = weather_json['name']
        temp = int(weather_json['main']['temp'])
        feels = int(weather_json['main']['feels_like'])
        description = weather_json['weather'][0]['main'].lower()
        #Create response
        response = ''
        temp_str = f'the temperature {location}is {temp} degrees'
        if temp != feels:
            temp_str += f', it feels like {feels}'

        if 'clouds' in description:
            description = 'it is overcast'
        if 'clear' in description:
            description = 'the skies are clear'

        if 'weather' in command:
            return f'{response}{temp_str} and {description}'
        
        '''
        better way to do this
        1. determine if the question is an 'is it' question
        2. determine what the 'is it' is about (hot, cold, comfortable)
        3. determine if the response is Yes, No
        4. build the rest of the response
        '''
        if ' hot ' in command or ' warm ' in command:
            if temp > self.hot:
                response = f'Yes, it is quite hot{location}, {temp} degrees to be exact'
            elif temp > self.cold:
                response = f'No, {location}it is actually a comfortable {temp} degrees'
            else:
                response = f'No, it is actually quite cold{location}, {temp} degrees to be exact'

        elif ' cold ' in command or ' cool ' in command or ' chilly ' in command:
            if temp > self.hot:
                response = f'No, it is actually quite hot{location}, {temp} degrees to be exact'
            elif temp > self.cold:
                response = f'No, {location}it is actually a comfortable {temp} degrees'
            else:
                response = f'Yes, it is quite cold{location}, {temp} degrees to be exact'
        
        elif ' comfortable ' in command or ' nice ' in command:
            if temp > self.hot:
                response = f'No, it is actually quite hot{location}, {temp} degrees to be exact'
            elif temp > self.cold:
                response = f'Yes, {location}it is a comfortable {temp} degrees'
            else:
                response = f'No, it is actually quite cold{location}, {temp} degrees to be exact'

        elif ' temp ' in command or ' temperature ' in command:
            response = temp_str

        if ' skies ' in command or ' sky ' in command:
            if not response:
                response = f'{description}{location}'
            else:
                response += f', and {description}'

        return response

    def answer_math(self, text):
        #todo
        return ''