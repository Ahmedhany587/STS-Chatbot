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