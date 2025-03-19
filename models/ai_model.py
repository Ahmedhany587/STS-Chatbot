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