import os, time, json, tempfile
from typing import Dict, Any, Optional
from gtts import gTTS
from base64 import b64decode

# Try import google genai
USE_GENAI = False
try:
    from google import genai  # official python-genai package
    USE_GENAI = True
except Exception:
    USE_GENAI = False

# For citation: examples and usage of genai python package are shown in Google GenAI docs.
# See: https://ai.google.dev/gemini-api/docs/quickstart and python-genai docs. :contentReference[oaicite:3]{index=3}

class GeminiClient:
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.5-flash"):
        # Read environment variables if not passed
        self.api_key = api_key or os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
        self.available = bool(self.api_key) and USE_GENAI
        self.model = model
        if self.available:
            # Configure client (the python-genai package reads from env but explicit configure is fine)
            genai.configure(api_key=self.api_key)

            # Create a client instance (depending on version either genai.Client() or direct calls)
            try:
                self.client = genai.Client()
            except Exception:
                # older/newer libs may not need to instantiate
                self.client = None

    def chat(self, prompt: str, temperature: float = 0.2) -> Dict[str, Any]:
        """Return a dict. If Gemini is not available, return mock response."""
        if not self.available:
            return {'mock': True, 'text': f'[MOCK] {prompt[:200]}'}
        # Using python-genai SDK model example: models.generate_content / models.generate_text (varies by version)
        # Below is a robust pattern that tries a couple API shapes.
        try:
            if self.client:
                # Example: client.models.generate_content(...)
                resp = self.client.models.generate_content(model=self.model, contents=prompt, temperature=temperature)
                # response has .text
                return {'text': getattr(resp, 'text', str(resp))}
            else:
                # fallback: genai.generate_text
                resp = genai.generate_text(model=self.model, prompt=prompt, temperature=temperature)
                return {'text': resp.text}
        except Exception as e:
            # return error info but keep app running
            return {'error': str(e)}

    def summarize(self, text: str, max_tokens: int = 400) -> str:
        if not self.available:
            return '[MOCK SUMMARY] ' + text[:400]
        prompt = f"Summarize the following text into a concise study-friendly summary and list 6 flashcard Q&A pairs:\\n\\n{text}"
        r = self.chat(prompt)
        return r.get('text', '')

    def generate_quiz(self, topic: str, difficulty: str = 'Medium', n_questions: int = 5):
        if not self.available:
            # mock data
            return [{'q': f'Mock Q about {topic}', 'a': 'Mock Answer'} for _ in range(n_questions)]
        prompt = (f"Generate {n_questions} multiple-choice questions (with correct answer) "
                  f"on the topic: {topic}. Difficulty: {difficulty}. Provide JSON array of objects "
                  f"with keys 'q', 'options', 'answer', and short 'explanation'.")
        r = self.chat(prompt)
        # attempt to parse JSON from r['text']
        txt = r.get('text','')
        try:
            # If the model returns JSON, parse it. Otherwise return a simple text-wrapped quiz.
            j = json.loads(txt)
            return j
        except Exception:
            # fallback: create simple Qs
            return [{'q': txt[:200], 'options': [], 'answer': '', 'explanation': ''}]

    def tts(self, text: str, lang: str = 'en') -> str:
        """Try to use Gemini TTS if available; else fallback to gTTS."""
        if not self.available:
            # gTTS fallback
            return tts_local(text, lang)
        # If the SDK supports speech synthesis, use it. Implementation differs across SDK versions.
        try:
            # Example pseudo-call (may need adaptation depending on SDK):
            audio_resp = genai.audio.speech.synthesize(model="gpt-4o-mini-tts", input=text)
            # audio_resp might be bytes or base64
            if hasattr(audio_resp, 'audio'):
                # save bytes
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
                tmp.write(audio_resp.audio)
                tmp.flush()
                return tmp.name
            elif isinstance(audio_resp, dict) and 'audio' in audio_resp:
                b = b64decode(audio_resp['audio'])
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
                tmp.write(b)
                tmp.flush()
                return tmp.name
        except Exception:
            # fallback to local gTTS
            return tts_local(text, lang)

def tts_local(text: str, lang: str = 'en') -> str:
    tts = gTTS(text=text, lang=lang)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
    tts.save(tmp.name)
    return tmp.name
