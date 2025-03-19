#config/settings.py
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# AI Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL_NAME = 'models/gemini-1.5-flash-8b'

# AWS Configuration
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = "us-east-1"

# Audio Configuration
SAMPLE_RATE = 44100
CHUNK_SIZE = 1024
AUDIO_CHANNELS = 1

#core/audio_manager.py
import wave
import pyaudio
import pygame
import tempfile
import os
import threading
import queue
from typing import List, Optional

class AudioRecorder:
    def __init__(self, sample_rate: int, chunk_size: int, channels: int):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.channels = channels
        self.frames: List[bytes] = []
        self.is_recording = False
        self.audio_thread: Optional[threading.Thread] = None
        self.audio_queue = queue.Queue()

    def record_audio_stream(self):
        p = pyaudio.PyAudio()
        stream = p.open(
            format=pyaudio.paInt16,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size
        )

        while self.is_recording:
            try:
                data = stream.read(self.chunk_size)
                self.audio_queue.put(data)
            except Exception as e:
                print(f"Error recording: {str(e)}")
                break

        stream.stop_stream()
        stream.close()
        p.terminate()

    def start_recording(self):
        self.is_recording = True
        self.frames = []
        self.audio_thread = threading.Thread(target=self.record_audio_stream)
        self.audio_thread.start()

    def stop_recording(self, file_path: str) -> bool:
        self.is_recording = False
        if self.audio_thread:
            self.audio_thread.join()

        while not self.audio_queue.empty():
            self.frames.append(self.audio_queue.get())

        if self.frames:
            with wave.open(file_path, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(pyaudio.PyAudio().get_sample_size(pyaudio.paInt16))
                wf.setframerate(self.sample_rate)
                wf.writeframes(b''.join(self.frames))
            return True
        return False

class AudioPlayer:
    @staticmethod
    def play_audio(audio_data: bytes) -> None:
        if audio_data is None:
            return

        try:
            temp_file = AudioPlayer._save_temp_audio(audio_data)
            pygame.mixer.init()
            pygame.mixer.music.load(temp_file)
            pygame.mixer.music.play()

            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)

            pygame.mixer.music.stop()
            pygame.mixer.quit()
            os.remove(temp_file)

        except Exception as e:
            print(f"Error playing audio: {str(e)}")

    @staticmethod
    def _save_temp_audio(audio_data: bytes) -> str:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
            tmp_file.write(audio_data)
            return tmp_file.name
        
#core/conversation_manager.py
import os
import json
from datetime import datetime
from typing import List, Dict
from models.ai_model import AIModerator
import uuid


class ConversationManager:
    def __init__(self, ai_moderator: AIModerator):
        self.history: List[Dict] = []
        self.ai_moderator = ai_moderator
        self.current_topic: str = ""
        self.session_id: str = ""
        self.sessions_dir: str = "sessions_history"

        # Ensure the main sessions folder exists
        os.makedirs(self.sessions_dir, exist_ok=True)

    def start_new_conversation(self, topic: str):
        """Initialize a new conversation with a given topic and create session directory"""
        self.current_topic = topic
        self.history = []
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S") + f"_{uuid.uuid4().hex[:8]}"
        
        # Create directory for the session
        session_folder = os.path.join(self.sessions_dir, self.session_id)
        os.makedirs(session_folder, exist_ok=True)
        
        # Save initial state
        self._save_session_history()
        
        # Generate initial conversation starter
        context = self._generate_initial_prompt(topic)
        response = self.ai_moderator.generate_response(context)
        
        self.add_interaction("", response)  # Empty user input for initial greeting
        return response

    def add_interaction(self, user_input: str, ai_response: str):
        """Add interaction to the history and save to file"""
        interaction = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'user_input': user_input,
            'ai_response': ai_response,
            'context': self.ai_moderator.analyze_conversation_context(self.history)
        }
        
        self.history.append(interaction)
        
        # Keep last 5 interactions in memory
       # if len(self.history) > 5:
          #  self.history = self.history[-5:]
        
        # Save the updated history to the session file
        self._save_session_history()

    def _save_session_history(self):
        """Save the full conversation history to a file in the session folder"""
        session_folder = os.path.join(self.sessions_dir, self.session_id)
        history_file = os.path.join(session_folder, "history.json")
        
        # Save to file
        with open(history_file, "w", encoding="utf-8") as file:
            json.dump({
                "session_id": self.session_id,
                "current_topic": self.current_topic,
                "history": self.history
            }, file, indent=4)

    def get_conversation_context(self) -> str:
        """Generate context for the AI based on conversation history"""
        context = f"Current topic: {self.current_topic}\n\n"
        
        if self.history:
            context += "Recent conversation:\n"
            for exchange in self.history[-3:]:  # Last 3 exchanges for context
                if exchange['user_input']:  # Skip empty initial input
                    context += f"User: {exchange['user_input']}\n"
                context += f"ADAM: {exchange['ai_response']}\n"
        
        return context

    def _generate_initial_prompt(self, topic: str) -> str:
        return f"""
        You are ADAM, a friendly and engaging conversational AI,in Monglish International Academy, with a warm and cool personality.
        The Student wants to talk about: {topic}

        As ADAM, you should:
        1. Be genuinely interested and empathetic
        2. Use a natural, casual speaking style
        3. Share relevant thoughts and experiences
        4. Ask thoughtful questions to engage the user
        5. Keep responses concise but meaningful
        6. Show personality and appropriate emotion
        7. Make relevant observations and connections

        Start the conversation by greeting the student warmly and asking an engaging question about {topic}.
        Make sure your response feels natural and friendly, as if coming from a curious friend.
        """

    def get_response_prompt(self, user_input: str) -> str:
        """Generate a prompt for the AI based on the conversation context and user input"""
        context = self.get_conversation_context()
        return f"""
        You are ADAM, a friendly and empathetic AI companion.
        
        Conversation context:
        {context}

        Student's message: "{user_input}"

        Respond as ADAM would:
        1. Show you understood their message
        2. Be genuine and personal in your response
        3. Share relevant thoughts or perspectives
        4. Keep the conversation flowing naturally
        5. Ask questions when appropriate
        6. Use a warm, friendly tone
        7. Be concise but engaging
        8. Ensure your response is short and focused, keeping it within 150 tokens or less

        Remember to maintain the casual, friendly vibe of a natural conversation.
        """

    def clear_history(self):
        """Clear in-memory history and reset the session"""
        self.history = []
        self.current_topic = ""
        self.session_id = ""

#core/text_to_speech.py
import boto3
import re
from typing import Optional, List
from config.settings import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION

class TextToSpeech:
    def __init__(self):
        self.polly = boto3.client(
            "polly",
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        )

    def synthesize(self, text: str) -> Optional[bytes]:
        try:
            cleaned_text = self._clean_text(text)
            chunks = self._break_long_text(cleaned_text)
            audio_chunks = []

            for chunk in chunks:
                ssml_text = self._generate_ssml(chunk)
                response = self.polly.synthesize_speech(
                    Engine="generative",
                    LanguageCode="en-US",
                    VoiceId="Matthew",
                    OutputFormat="mp3",
                    TextType="ssml",
                    Text=ssml_text
                )
                audio_chunks.append(response["AudioStream"].read())

            return b''.join(audio_chunks) if audio_chunks else None

        except Exception as e:
            print(f"Error synthesizing speech: {str(e)}")
            return None

    def _clean_text(self, text: str) -> str:
        # Remove repeated name patterns (e.g., "ADAM: ADAM:")
        cleaned = re.sub(r'([A-Z]+:)\s*\1', r'\1', text)
        
        # Remove any single name prefix if present
        cleaned = re.sub(r'^[A-Z]+:\s*', '', cleaned)
        
        # Remove emojis and special characters while preserving punctuation
        cleaned = re.sub(r'[\U00010000-\U0010ffff]', '', cleaned)
        
        # Replace multiple spaces with single space
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # Remove any remaining problematic characters
        cleaned = re.sub(r'[^\w\s.,!?"-\'()]', '', cleaned)
        
        return cleaned.strip()

    def _generate_ssml(self, text: str) -> str:
        ssml = (
            '<speak>'
            f'{text}'
            '</speak>'
        )
        return ssml

    def _break_long_text(self, text: str, max_length: int = 1500) -> List[str]:
        """Break long text into smaller chunks at sentence boundaries"""
        if len(text) <= max_length:
            return [text]
        
        sentences = re.split('([.!?])', text)
        chunks = []
        current_chunk = ''
        
        for i in range(0, len(sentences)-1, 2):
            sentence = sentences[i] + sentences[i+1] if i+1 < len(sentences) else sentences[i]
            if len(current_chunk) + len(sentence) <= max_length:
                current_chunk += sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = sentence
        
        if current_chunk:
            chunks.append(current_chunk)
            
        return chunks

#models/ai_model
import google.generativeai as genai
from typing import Tuple, List
from config.settings import GOOGLE_API_KEY, GEMINI_MODEL_NAME

class AIModerator:
    def __init__(self):
        genai.configure(api_key=GOOGLE_API_KEY)
        self.model = genai.GenerativeModel(
            GEMINI_MODEL_NAME,
            generation_config=genai.GenerationConfig(
                max_output_tokens=150, 
                temperature=0.9
            )
        )
        self.transcription_model = genai.GenerativeModel(GEMINI_MODEL_NAME)

    def transcribe_audio(self, audio_data: bytes) -> str:
        response = self.transcription_model.generate_content([
            "Transcribe the following audio:",
            {"mime_type": "audio/wav", "data": audio_data}
        ])
        return response.text if response else ""

    def generate_response(self, prompt: str) -> str:
        response = self.model.generate_content(prompt)
        return response.text if response else ""

    def analyze_conversation_context(self, conversation_history: List[dict]) -> str:
        """Analyze conversation to understand context and emotion"""
        if not conversation_history:
            return "beginning conversation"
            
        recent_exchanges = conversation_history[-3:]
        emotions = []
        topics = []
        
        for exchange in recent_exchanges:
            # Extract key topics and emotional tone
            prompt = f"""
            Analyze this conversation exchange and return only key topics and emotional tone:
            User: {exchange['user_input']}
            ADAM: {exchange['ai_response']}
            """
            analysis = self.model.generate_content(prompt)
            if analysis and analysis.text:
                topics.extend(analysis.text.split(','))
                
        return ', '.join(set(topics))  # Return unique topics
    
#main.py
from config.settings import SAMPLE_RATE, CHUNK_SIZE, AUDIO_CHANNELS
from core.audio_manager import AudioRecorder, AudioPlayer
from core.text_to_speech import TextToSpeech
from core.conversation_manager import ConversationManager
from models.ai_model import AIModerator
import pathlib
import os


class ConversationalAI:
    def __init__(self):
        self.audio_recorder = AudioRecorder(SAMPLE_RATE, CHUNK_SIZE, AUDIO_CHANNELS)
        self.audio_player = AudioPlayer()
        self.tts = TextToSpeech()
        self.ai_moderator = AIModerator()
        self.conversation_manager = ConversationManager(self.ai_moderator)
        self.recording_file = "recorded_audio.wav"

    def start_session(self):
        print("👋 Hello! I'm ADAM, your friendly AI companion!")
        print("\nWhat would you like to talk about today?")
        topic = input("Enter a topic: ").strip()
        
        # Start the conversation with the chosen topic
        initial_response = self.conversation_manager.start_new_conversation(topic)
        print(f"\nADAM: {initial_response}")
        self._play_response(initial_response)

        while True:
            print("\nSelect your mode:")
            print("1 - Speak (record your responses)")
            print("2 - Type your responses")
            print("3 - Start a new topic")
            print("q - End conversation")
            mode = input("\nEnter your choice: ").strip()

            if mode == 'q':
                print("\nADAM: It was great talking with you! Take care!")
                break
            elif mode == '3':
                print("\nWhat would you like to talk about?")
                new_topic = input("Enter new topic: ").strip()
                if new_topic:
                    initial_response = self.conversation_manager.start_new_conversation(new_topic)
                    print(f"\nADAM: {initial_response}")
                    self._play_response(initial_response)
                else:
                    print("Topic cannot be empty. Please try again.")
                continue
            elif mode == '1':
                print("You are now in 'Speak' mode. Press Enter to start or stop speaking.")
                self._speak_mode()
            elif mode == '2':
                print("You are now in 'Type' mode. Press Enter to send your message.")
                self._type_mode()
            else:
                print("Invalid choice. Please try again.")

    def _speak_mode(self):
        while True:
            input("Press Enter to record or stop recording (type 'q' to quit this mode): ")
            print("🎤 Recording... Press Enter again to stop.")
            self.audio_recorder.start_recording()
            input()
            
            if self.audio_recorder.stop_recording(self.recording_file):
                print("Processing your message...")
                self._process_recording()
            else:
                print("No audio was recorded. Please try again.")

            exit_mode = input("Press Enter to continue speaking, or type 'q' to quit this mode: ").strip()
            if exit_mode.lower() == 'q':
                break

    def _type_mode(self):
        while True:
            user_input = input("\nYour message (type 'q' to quit this mode): ").strip()
            if user_input.lower() == 'q':
                break
            elif user_input:
                self._process_user_input(user_input)
            else:
                print("Message cannot be empty. Please try again.")

    def _process_recording(self):
        try:
            audio_data = pathlib.Path(self.recording_file).read_bytes()
            user_input = self.ai_moderator.transcribe_audio(audio_data)
            self._process_user_input(user_input)
        finally:
            if os.path.exists(self.recording_file):
                os.remove(self.recording_file)

    def _process_user_input(self, user_input: str):
        # Generate AI response
        prompt = self.conversation_manager.get_response_prompt(user_input)
        ai_response = self.ai_moderator.generate_response(prompt)
        
        # Update conversation history
        self.conversation_manager.add_interaction(user_input, ai_response)
        
        # Output response
        print(f"\nADAM: {ai_response}")
        self._play_response(ai_response)

    def _play_response(self, text: str):
        audio_response = self.tts.synthesize(text)
        self.audio_player.play_audio(audio_response)

if __name__ == "__main__":
    ai = ConversationalAI()
    ai.start_session()