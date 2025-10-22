import os
import json
import tempfile
from typing import Dict, Any, List
from gtts import gTTS
import google.generativeai as genai  # ✅ Correct Gemini SDK import


class GeminiClient:
    """
    Wrapper for Google Gemini API.
    Uses google-generativeai SDK for real AI responses.
    """
    def __init__(self, api_key: str = None, model: str = "gemini-1.5-flash"):
        # Pick API key from parameter or environment
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.model = model
        self.available = bool(self.api_key)

        if self.available:
            try:
                genai.configure(api_key=self.api_key)
            except Exception as e:
                print(f"❌ Gemini configuration failed: {e}")
                self.available = False

    def chat(self, prompt: str, temperature: float = 0.3) -> Dict[str, Any]:
        """
        Send a chat prompt to Gemini and get back a text response.
        Returns a dict: {'text': response_text}
        """
        if not self.available:
            return {"mock": True, "text": f"[MOCK RESPONSE] {prompt[:200]}"}

        try:
            model = genai.GenerativeModel(self.model)
            response = model.generate_content(prompt)
            return {"text": response.text}
        except Exception as e:
            return {"error": str(e)}

    def summarize(self, text: str) -> str:
        """
        Summarize a given text and generate 5 study flashcards.
        """
        if not text:
            return ""

        prompt = (
            f"Summarize the following content in a concise way suitable for study, "
            f"and generate 5 flashcard-style Q&A pairs:\n\n{text[:2000]}"
        )
        result = self.chat(prompt)
        return result.get("text", "")

    def generate_quiz(self, topic: str, difficulty: str = "Medium", n_questions: int = 5) -> List[Dict[str, Any]]:
        """
        Generate a quiz (JSON list of Q&A) for a given topic.
        """
        if not topic:
            return []

        prompt = (
            f"Generate {n_questions} multiple-choice questions on the topic '{topic}' "
            f"with difficulty '{difficulty}'. Return as JSON array with keys: "
            f"'q', 'options', 'answer', 'explanation'."
        )
        res = self.chat(prompt)
        text = res.get("text", "")

        try:
            quiz = json.loads(text)
            if isinstance(quiz, list):
                return quiz
            else:
                return []
        except json.JSONDecodeError:
            # fallback if model didn't output JSON
            return [
                {"q": topic, "options": [], "answer": "", "explanation": text[:200]}
                for _ in range(n_questions)
            ]

    def tts(self, text: str, lang: str = "en") -> str:
        """
        Generate an MP3 speech file from given text using gTTS.
        Returns path to saved temporary file.
        """
        try:
            tts = gTTS(text=text, lang=lang)
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            tts.save(tmp.name)
            tmp.close()
            return tmp.name
        except Exception as e:
            return f"Error generating TTS: {str(e)}"
