import os, json, tempfile
from typing import Dict, Any
from gtts import gTTS

USE_GENAI = False
try:
    from google import genai
    USE_GENAI = True
except:
    USE_GENAI = False

class GeminiClient:
    def __init__(self, api_key=None, model="gemini-2.5-flash"):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.available = bool(self.api_key) and USE_GENAI
        self.model = model
        if self.available:
            genai.configure(api_key=self.api_key)
            try: self.client = genai.Client()
            except: self.client = None

    def chat(self, prompt: str, temperature: float = 0.2) -> Dict[str, Any]:
        if not self.available: return {"mock": True, "text": prompt[:200]}
        try:
            if self.client:
                resp = self.client.models.generate_content(model=self.model, contents=prompt, temperature=temperature)
                return {"text": getattr(resp, "text", str(resp))}
            else:
                resp = genai.generate_text(model=self.model, prompt=prompt, temperature=temperature)
                return {"text": resp.text}
        except Exception as e:
            return {"error": str(e)}

    def tts(self, text: str, lang: str="en") -> str:
        tts = gTTS(text=text, lang=lang)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tts.save(tmp.name)
        return tmp.name
