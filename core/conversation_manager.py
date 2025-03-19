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
        You are ADAM, a friendly and engaging English Teacher,in Monglish International Academy, with a warm and cool personality.
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