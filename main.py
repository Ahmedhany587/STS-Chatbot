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