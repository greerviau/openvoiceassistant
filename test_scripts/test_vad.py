import speech_recognition as sr
import time

r = sr.Recognizer()

# Words that sphinx should listen closely for. 0-1 is the sensitivity
# of the wake word.
keywords = [("david", 1), ("hey david", 1), ]

source = sr.Microphone(device_index=1)

def callback(recognizer, audio):  # this is called from the background thread

    try:
        speech_as_text = recognizer.recognize_sphinx(audio)
        print(speech_as_text)

        # Look for your "Ok Google" keyword in speech_as_text
        if "david" in speech_as_text or "hey david":
            print('Hotword!')
            recognize_main()

    except sr.UnknownValueError:
        print("Oops! Didn't catch that")


def recognize_main():
    print("Recognizing Main...")
    audio_data = r.listen(source)
    print('Done Listening')
    # interpret the user's words however you normally interpret them


def start_recognizer():
    r.listen_in_background(source, callback)
    time.sleep(1000000)


start_recognizer()