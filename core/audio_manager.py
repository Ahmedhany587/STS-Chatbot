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
        
#########################################################################################################