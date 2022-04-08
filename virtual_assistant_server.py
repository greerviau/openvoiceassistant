from typing import Optional, List
from fastapi import FastAPI, Response, File, UploadFile, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import soundfile as sf
import uvicorn
import pyttsx3
from virtual_assistant import VirtualAssistant
import wave
from vosk import Model, KaldiRecognizer, SetLogLevel
import json
import wave
import os
from utils import clean_text
import base64

config = json.load(open('server_config.json', 'r'))

SetLogLevel(0)

vosk_model = Model(config['vosk_model'])

host = config['host']
port = config['port']
debug = config['debug']
mqtt_broker_ip = config['mqtt_broker_ip']
mqtt_broker_port = config['mqtt_broker_port']
mqtt_broker_user = os.environ['MQTT_BROKER_USER']
mqtt_broker_pswd = os.environ['MQTT_BROKER_PSWD']

app = FastAPI()

VA = VirtualAssistant(name=config['name'], 
                    address=config['address'], 
                    mqtt=((mqtt_broker_ip, mqtt_broker_port), mqtt_broker_user, mqtt_broker_pswd),
                    location=config['city'],
                    intent_model=config['intent_model'],
                    vocab_file=config['vocab_file'],
                    debug=debug)

tts = pyttsx3.init()
tts.setProperty('voice', 'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices\Tokens\MSTTS_V110_enGB_GeorgeM')
tts.setProperty('rate',175)

class Data(BaseModel):
    audio_file: List[str]
    callback: str
    samplerate: int
    room_id: str

def log(text, end='\n'):
    if debug:
        print(text, end=end)

@app.get('/is_va_hub')
def is_va_hub():
    return True

@app.get('/get_hub_details')
def get_name_and_address():
    name = VA.name
    address = VA.address

    return {
        'name':name,
        'address':address,
        'mqtt_broker_ip': mqtt_broker_ip,
        'mqtt_broker_port': mqtt_broker_port,
        'mqtt_broker_user': mqtt_broker_user,
        'mqtt_broker_pswd': mqtt_broker_pswd
    }

@app.get('/reset_chat', status_code=201)
def reset_chat():
    VA.reset_chat()

@app.post('/understand_from_audio_and_synth')
async def understand_from_audio_and_synth(data: Data):
    audio_file = data.audio_file
    samplerate = data.samplerate
    callback = data.callback
    room_id = data.room_id

    rec = KaldiRecognizer(vosk_model, samplerate)
    rec.SetWords(True)
    res = None
    while True:
        if len(audio_file) == 0:
            break
        data = bytes(base64.b64decode(audio_file.pop(0).encode('utf-8')))
        if rec.AcceptWaveform(data):
            res = rec.Result()
            break
        else:
            _ = rec.PartialResult()
            
    if not res:
        res = rec.FinalResult()
    log(f'Final {res}')
    if res:
        command = json.loads(res)['text']
        if not command:
            raise HTTPException(
                    status_code=404,
                    detail='command invalid',
                    headers={'X-Error': 'There goes my error'})

        command = clean_text(command)
        log(f'Raw command: {command}')
        response, intent, conf = VA.understand(command, room_id)
        log(f'Intent: {intent} - conf: {conf}')
        if response:
            log(f'Response: {response.response_text}')
            tts.save_to_file(response.response_text, 'server_response.wav')
            tts.runAndWait()

        return {
            'command': command,
            'response_packet':response,
            'intent':intent,
            'conf':conf,
            'synth':base64.b64encode(open('server_response.wav', 'rb').read())
        }
    else:
        raise HTTPException(
                    status_code=404,
                    detail='invalid audio',
                    headers={'X-Error': 'There goes my error'})

@app.get('/understand_from_text_and_synth/{text}')
def understand_from_text_and_synth(text: str):
    command = clean_text(text)
    log(command)
    response, intent, conf = VA.understand(command)
    if not command:
        raise HTTPException(
                status_code=404,
                detail='command invalid',
                headers={'X-Error': 'There goes my error'})

    response, intent, conf = VA.understand(command)
    tts.save_to_file(response, 'server_response.wav')
    tts.runAndWait()
    return {
        'command': command,
        'response':response,
        'intent':intent,
        'conf':conf,
        'synth':base64.b64encode(open('server_response.wav', 'rb').read())
    }

@app.get('/synth_voice/{text}')
def synth_voice(text: str):
    tts.save_to_file(text, 'server_response.wav')
    tts.runAndWait()
    with open('server_response.wav', 'rb') as fd:
        contents = fd.read()
        return Response(content = contents)

if __name__ == '__main__':
    uvicorn.run(app, host=host, port=port)