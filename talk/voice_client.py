import os
import logging
import re
import requests
import speech_recognition as sr
import pyttsx3

logging.basicConfig(level=logging.INFO)

SERVER_URL = os.getenv("SERVER_URL", "http://localhost:8012/process")

WAKE_WORDS = [
    "hey orianna",
    "orianna",
    "ok orianna",
    "hello orianna",
    "hi orianna",
    "hey oriana",
    "oriana",
    "hai orianna",
    "oh orianna",
    "hey, orianna",
    "hey oryanna",
    "rihanna",
    "ariana"
]

def init_tts_engine():
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    chosen_voice = voices[1].id if len(voices) > 1 else voices[0].id
    engine.setProperty('voice', chosen_voice)
    engine.setProperty('rate', 150)
    engine.setProperty('volume', 1.0)
    return engine

tts_engine = init_tts_engine()

def process_tts_text(text):
    return re.sub(r'\blouis\b', 'louie', text, flags=re.IGNORECASE)

def speak_text(text):
    processed_text = process_tts_text(text)
    try:
        tts_engine.say(processed_text)
        tts_engine.runAndWait()
    except Exception as e:
        logging.error(f"Error in text-to-speech: {e}")

def record_and_transcribe(timeout=10000, phrase_time_limit=15):
    recognizer = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            logging.info("Listening for your command...")
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
    except sr.WaitTimeoutError:
        logging.error("Listening timed out while waiting for your command.")
        return None
    except Exception as e:
        logging.error(f"Error accessing microphone: {e}")
        return None

    try:
        transcript = recognizer.recognize_google(audio)
        logging.info(f"Transcription: {transcript}")
        return transcript
    except sr.RequestError as e:
        logging.error(f"API unavailable: {e}")
    except sr.UnknownValueError:
        logging.error("Could not understand audio.")
    return None

def send_to_server(user_text):
    try:
        headers = {"Content-Type": "text/plain"}
        response = requests.post(SERVER_URL, data=user_text, headers=headers, timeout=100000)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error sending to server: {e}")
    except ValueError:
        logging.error("Server response is not in JSON format.")
    return None

def listen_for_wake_word(wake_words=WAKE_WORDS):
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        logging.info("Calibrating microphone for wake word detection...")
        recognizer.adjust_for_ambient_noise(source, duration=1)
        while True:
            try:
                logging.info("Listening for wake word...")
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=3)
                transcript = recognizer.recognize_google(audio).lower()
                logging.info(f"Heard: {transcript}")
                if any(wake_word in transcript for wake_word in wake_words):
                    logging.info("Wake word detected!")
                    return True
            except sr.WaitTimeoutError:
                continue
            except sr.UnknownValueError:
                continue
            except Exception as e:
                logging.error(f"Error in wake word detection: {e}")
                continue

def voice_activation_loop():
    while True:
        if listen_for_wake_word():
            speak_text("Yes?")
            command = record_and_transcribe()
            if command:
                logging.info(f"Command recorded: {command}")
                speak_text("Of course Louis")
                server_response = send_to_server(command)
                if server_response:
                    decision_message = server_response.get("decision", {}).get("summary", "No response from server.")
                    logging.info(f"Orianna says: {decision_message}")
                    speak_text(decision_message)
                    speak_text("Is there anything else I can help you with?")
                else:
                    logging.error("No response from server.")
            else:
                logging.error("No command recorded.")

if __name__ == "__main__":
    voice_activation_loop()
