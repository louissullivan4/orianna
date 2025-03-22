import os
import logging
import re
import requests
import speech_recognition as sr
import pyttsx3

# Configure logging for detailed output.
logging.basicConfig(level=logging.INFO)

# Allow the server URL to be set via an environment variable.
SERVER_URL = os.getenv("SERVER_URL", "http://localhost:8012/process")

# Expanded wake word list with different spellings and variations.
WAKE_WORDS = [
    "hey orianna",
    "orianna",
    "ok orianna",
    "hello orianna",
    "hi orianna",
    "hey oriana",    # common mis-spelling
    "oriana",        # alternative pronunciation
    "hai orianna",   # phonetic variant
    "oh orianna",
    "hey, orianna",  # with punctuation
    "hey oryanna",   # another mis-spelling
    "rihanna",
    "ariana"
]

def init_tts_engine():
    """
    Initialize and configure the text-to-speech engine.
    Chooses the second available voice if possible, sets a moderate speaking rate, and full volume.
    """
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    chosen_voice = voices[1].id if len(voices) > 1 else voices[0].id
    engine.setProperty('voice', chosen_voice)
    engine.setProperty('rate', 150)
    engine.setProperty('volume', 1.0)
    return engine

tts_engine = init_tts_engine()

def process_tts_text(text):
    """
    Processes the text to be spoken by replacing 'Louis' with 'Louie'
    to enforce the desired pronunciation.
    
    Parameters:
        text (str): The original text.
    
    Returns:
        str: The processed text with replacements applied.
    """
    # Replace whole word "louis" (case-insensitive) with "louie"
    return re.sub(r'\blouis\b', 'louie', text, flags=re.IGNORECASE)

def speak_text(text):
    """
    Uses the TTS engine to speak the provided text after processing it
    for custom pronunciations.
    
    Parameters:
        text (str): The text to be spoken.
    """
    processed_text = process_tts_text(text)
    try:
        tts_engine.say(processed_text)
        tts_engine.runAndWait()
    except Exception as e:
        logging.error(f"Error in text-to-speech: {e}")

def record_and_transcribe(timeout=10000, phrase_time_limit=15):
    """
    Records audio from the microphone and transcribes it using Google's Speech Recognition.
    
    Parameters:
        timeout (int): Maximum seconds to wait for a phrase to start.
        phrase_time_limit (int): Maximum seconds for recording once a phrase starts.
    
    Returns:
        str or None: The transcribed text if successful; otherwise, None.
    """
    recognizer = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            # logging.info("Adjusting for ambient noise...")
            # recognizer.adjust_for_ambient_noise(source, duration=1)
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
    """
    Sends the transcribed text to the server and returns the JSON response.
    
    Parameters:
        user_text (str): The text to be sent to the server.
    
    Returns:
        dict or None: Parsed JSON response if successful; otherwise, None.
    """
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
    """
    Continuously listens for any wake word from the provided list.
    
    Parameters:
        wake_words (list): Phrases that will trigger the assistant.
    
    Returns:
        bool: Returns True when a wake word is detected.
    """
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
                continue  # No speech detected within the timeout.
            except sr.UnknownValueError:
                continue  # Speech was unintelligible.
            except Exception as e:
                logging.error(f"Error in wake word detection: {e}")
                continue

def voice_activation_loop():
    """
    Main loop that continuously listens for the wake word. Once triggered, it responds,
    listens for a command, sends the command to the server, and then speaks the server's response.
    """
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
