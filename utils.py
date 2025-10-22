import os
import json
import tempfile
from typing import Dict, Any, List
from gtts import gTTS
import google.generativeai as genai  

class GeminiClient:
    """
    Wrapper for Google Gemini AI API.
    Uses the official google-generativeai SDK.
    Falls back gracefully if API key missing.
    """
    def __init__(self, api_key: str = None, model: str = "gemini-1.5-flash"):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.model = model
        self.available = bool(self.api_key)

        if self.available:
            genai.configure(api_key=self.api_key)

    def chat(self, prompt: str, temperature: float = 0.2) -> Dict[str, Any]:
        if not self.available:
            return {"mock": True, "text": f"[MOCK RESPONSE] {prompt[:200]}"}
    
        try:
            response = genai.GenerativeModel(self.model).generate_content(prompt)
            return {"text": response.text}
        except Exception as e:
            return {"error": str(e)}

    def summarize(self, text: str, max_tokens: int = 400) -> str:
        if not text:
            return ""
        prompt = f"Summarize the following text into study notes and generate 5 flashcards:\n\n{text[:2000]}"
        return self.chat(prompt).get("text", "")

    def generate_quiz(self, topic: str, difficulty: str = "Medium", n_questions: int = 5) -> List[Dict[str, Any]]:
        if not topic:
            return []

        prompt = (
            f"Generate {n_questions} multiple-choice questions on the topic '{topic}' "
            f"with difficulty '{difficulty}'. Return JSON array of objects with keys: "
            "'q', 'options', 'answer', and 'explanation'."
        )
        res = self.chat(prompt)
        text = res.get("text", "")
        try:
            quiz = json.loads(text)
            if isinstance(quiz, list):
                return quiz
        except json.JSONDecodeError:
            pass
        return [{"q": topic, "options": [], "answer": "", "explanation": text[:200]} for _ in range(n_questions)]

    def tts(self, text: str, lang: str = "en") -> str:
        try:
            tts = gTTS(text=text, lang=lang)
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            tts.save(tmp.name)
            tmp.close()
            return tmp.name
        except Exception as e:
            return f"Error generating TTS: {str(e)}"
