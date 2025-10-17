import os
import json
import tempfile
from typing import Dict, Any, List
from gtts import gTTS

# Try importing Google GenAI SDK
USE_GENAI = False
try:
    from google import genai
    USE_GENAI = True
except ImportError:
    USE_GENAI = False

class GeminiClient:
    """
    Wrapper for Gemini AI API.
    Fallbacks to mock responses if GenAI not available.
    """
    def __init__(self, api_key: str = None, model: str = "gemini-2.5-flash"):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.model = model
        self.available = bool(self.api_key) and USE_GENAI

        if self.available:
            try:
                genai.configure(api_key=self.api_key)
                try:
                    self.client = genai.Client()
                except Exception:
                    self.client = None
            except Exception:
                self.available = False
                self.client = None
        else:
            self.client = None

    def chat(self, prompt: str, temperature: float = 0.2) -> Dict[str, Any]:
        """
        Send a chat prompt to Gemini. Returns dictionary with 'text'.
        """
        if not self.available:
            return {"mock": True, "text": f"[MOCK RESPONSE] {prompt[:200]}"}

        try:
            if self.client:
                resp = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    temperature=temperature
                )
                return {"text": getattr(resp, "text", str(resp))}
            else:
                resp = genai.generate_text(model=self.model, prompt=prompt, temperature=temperature)
                return {"text": getattr(resp, "text", str(resp))}
        except Exception as e:
            return {"error": str(e)}

    def summarize(self, text: str, max_tokens: int = 400) -> str:
        """
        Summarize text into concise study-friendly summary.
        """
        if not text:
            return ""
        prompt = f"Summarize the following text for learning purposes and generate 5 flashcard Q&A pairs:\n\n{text[:2000]}"
        res = self.chat(prompt)
        return res.get("text", "")

    def generate_quiz(self, topic: str, difficulty: str = "Medium", n_questions: int = 5) -> List[Dict[str, Any]]:
        """
        Generate a quiz (JSON list of Q&A) for a given topic.
        """
        if not topic:
            return []

        prompt = (
            f"Generate {n_questions} multiple-choice questions on the topic '{topic}' "
            f"with difficulty '{difficulty}'. Return as JSON array of objects "
            "with keys: 'q', 'options', 'answer', 'explanation'."
        )
        res = self.chat(prompt)
        text = res.get("text", "")
        try:
            quiz = json.loads(text)
            if isinstance(quiz, list):
                return quiz
            return []
        except json.JSONDecodeError:
            # fallback simple format
            return [{"q": topic, "options": [], "answer": "", "explanation": text[:200]} for _ in range(n_questions)]

    def tts(self, text: str, lang: str = "en") -> str:
        """
        Generate speech audio from text using gTTS.
        Returns path to temporary mp3 file.
        """
        try:
            tts = gTTS(text=text, lang=lang)
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            tts.save(tmp.name)
            tmp.close()
            return tmp.name
        except Exception as e:
            return f"Error generating TTS: {str(e)}"
