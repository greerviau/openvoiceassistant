from typing import Optional
from fastapi import FastAPI, Response, File, UploadFile, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.responses import StreamingResponse
import uvicorn
import pyttsx3
from virtual_assistant import VirtualAssistant
import wave
from  vosk import Model, KaldiRecognizer, SetLogLevel
import json
import wave
from utils import clean_text
import base64

SetLogLevel(0)
vosk_model = Model('vosk_big')

app = FastAPI()

VA = VirtualAssistant(name='jarvis', address='sir', debug=False)

host = '10.0.0.120'
port = 8000
tts = pyttsx3.init()
tts.setProperty('voice', 'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices\Tokens\MSTTS_V110_enGB_GeorgeM')
tts.setProperty('rate',175)

@app.get('/is_va_hub')
def is_va_hub():
    return {
        'ip':host,
        'port':port
    }

@app.get('/predict_intent/{text}')
def predict_intent(text: str):
    command = clean_text(text)
    print(command)
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
    print(command)
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
    print(command)
    response, intent, conf = VA.understand(command)
    return {
        'command': command,
        'response':response,
        'intent':intent,
        'conf':conf
    }

@app.post('/understand_from_audio_and_synth')
async def understand_from_audio_and_synth(audio_file: UploadFile = File(...)):
    file_data = audio_file.file.read()
    with open('server_command.wav', 'wb') as fd:
        fd.write(file_data)
    wf = wave.open('server_command.wav', 'rb')
    rec = KaldiRecognizer(vosk_model, wf.getframerate())
    rec.SetWords(True)
    res = None
    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            print('Result ', rec.Result())
        else:
            print('Partial ', rec.PartialResult())
    res = rec.FinalResult()
    print('Final ', res)
    if res:
        command = json.loads(res)['text']
        if not command:
            raise HTTPException(
                    status_code=404,
                    detail='command invalid',
                    headers={'X-Error': 'There goes my error'})

        command = clean_text(command)
        print(command)
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
    else:
        raise HTTPException(
                    status_code=404,
                    detail='invalid audio',
                    headers={'X-Error': 'There goes my error'})

@app.get('/understand_from_text/{text}')
def understand_from_text(text: str):
    command = clean_text(text)
    print(command)
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
    print(command)
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
        

@app.get('/get_hub_details')
def get_name_and_address():
    name = VA.get_name()
    address = VA.get_address()

    return {
        'name':name,
        'address':address
    }

@app.get('/reset_chat', status_code=201)
def reset_chat():
    VA.reset_chat()

if __name__ == '__main__':
    uvicorn.run(app, host=host, port=port)