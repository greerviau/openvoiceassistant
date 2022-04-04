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
from utils import clean_text
import base64

config = json.load(open('server_config.json', 'r'))

SetLogLevel(0)

vosk_model = Model(config['vosk_model'])

host = config['host']
port = config['port']
debug = config['debug']

app = FastAPI()

VA = VirtualAssistant(name=config['name'], 
                    address=config['address'], 
                    mqtt_broker=(config['mqtt_broker_ip'], config['mqtt_broker_port']),
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

def log(text, end='\n'):
    if debug:
        print(text, end=end)

@app.get('/is_va_hub')
def is_va_hub():
    return {
        'ip':host,
        'port':port
    }

@app.get('/get_hub_details')
def get_name_and_address():
    name = VA.name()
    address = VA.address()

    return {
        'name':name,
        'address':address
    }

@app.get('/reset_chat', status_code=201)
def reset_chat():
    VA.reset_chat()

@app.get('/predict_intent/{text}')
def predict_intent(text: str):
    command = clean_text(text)
    log(command)
    intent, conf = VA.predict_intent(command)
    return {
        'intent':intent,
        'conf':conf
    }

@app.post('/transcribe')
async def transcribe(audio_file: UploadFile = File(...)):
    file_data = audio_file.file.read()
    with open('server_command.wav', 'wb') as fd:
        fd.write(file_data)
    wf = wave.open('server_command.wav', 'rb')
    rec = KaldiRecognizer(vosk_model, wf.getframerate())
    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            res = json.loads(rec.Result())
    res = json.loads(rec.FinalResult())
    command = res['text']
    log(command)
    return {
        'text': text
    }

@app.post('/understand_from_audio')
async def understand_from_audio(audio_file: UploadFile = File(...)):
    file_data = audio_file.file.read()
    with open('server_command.wav', 'wb') as fd:
        fd.write(file_data)
    wf = wave.open('server_command.wav', 'rb')
    rec = KaldiRecognizer(vosk_model, wf.getframerate())
    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            res = json.loads(rec.Result())
    res = json.loads(rec.FinalResult())
    command = res['text']
    if not command:
        raise HTTPException(
                status_code=404,
                detail='command invalid',
                headers={'X-Error': 'There goes my error'})

    command = clean_text(command)
    log(command)
    response, intent, conf = VA.understand(command)
    return {
        'command': command,
        'response':response,
        'intent':intent,
        'conf':conf
    }

@app.post('/understand_from_audio_and_synth')
async def understand_from_audio_and_synth(data: Data):
    audio_file = data.audio_file
    samplerate = data.samplerate
    callback = data.callback

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
            
    if res is None:
        res = rec.FinalResult()
    log('Final ', res)
    if res:
        command = json.loads(res)['text']
        if not command:
            raise HTTPException(
                    status_code=404,
                    detail='command invalid',
                    headers={'X-Error': 'There goes my error'})

        command = clean_text(command)
        log('Command: ',command)
        response, intent, conf = VA.understand(command)
        log('Intent: ',intent,' - conf: ',conf)
        if response:
            log('Response: ',response.to_string())
            tts.save_to_file(response.response, 'server_response.wav')
            tts.runAndWait()

        return {
            'command': command,
            'packet':response,
            'intent':intent,
            'conf':conf,
            'synth':base64.b64encode(open('server_response.wav', 'rb').read())
        }
    else:
        raise HTTPException(
                    status_code=404,
                    detail='invalid audio',
                    headers={'X-Error': 'There goes my error'})

@app.get('/understand_from_text/{text}')
def understand_from_text(text: str):
    command = clean_text(text)
    log(command)
    response, intent, conf = VA.understand(command)
    return {
        'command': text,
        'response':response,
        'intent':intent,
        'conf':conf
    }

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