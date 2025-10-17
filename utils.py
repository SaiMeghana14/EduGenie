# utils.py
import os
import json
import tempfile
from typing import Dict, Any, List
from gtts import gTTS
from base64 import b64decode
import google.generativeai as genai

# -------------------------------
# Gemini SDK Initialization
# -------------------------------
def init_gemini():
    """Initialize Gemini SDK with API key."""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("❌ GEMINI_API_KEY not found in environment variables.")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-1.5-flash")  # or "gemini-1.5-pro" for better quality

# -------------------------------
# AI Chat / Tutor
# -------------------------------
def chat_with_gemini(prompt: str, temperature: float = 0.3) -> str:
    """Simple chat interface with Gemini."""
    model = init_gemini()
    try:
        response = model.generate_content(prompt, generation_config={"temperature": temperature})
        return response.text
    except Exception as e:
        return f"[Error calling Gemini API: {e}]"

# -------------------------------
# Summarizer
# -------------------------------
def summarize_text(text: str) -> str:
    """Summarize long content with flashcard-style notes."""
    prompt = (
        "You are a study assistant. Summarize the following text in concise bullet points "
        "and generate 5 flashcard Q&A pairs for revision.\n\n"
        f"Text:\n{text}"
    )
    return chat_with_gemini(prompt)

# -------------------------------
# Quiz Generator
# -------------------------------
def generate_quiz(topic: str, difficulty: str = "Medium", n_questions: int = 5) -> List[Dict[str, Any]]:
    """Generate MCQ quiz questions in JSON format."""
    prompt = (
        f"Create {n_questions} multiple-choice questions about '{topic}'. "
        f"Difficulty: {difficulty}. Return the result as a JSON list with fields: "
        f"'question', 'options', 'correct_answer', and 'explanation'."
    )
    res = chat_with_gemini(prompt)
    try:
        data = json.loads(res)
        if isinstance(data, list):
            return data
    except Exception:
        # fallback if text is not valid JSON
        return [{"question": res, "options": [], "correct_answer": "", "explanation": ""}]
    return data

# -------------------------------
# Text-to-Speech (gTTS fallback)
# -------------------------------
def text_to_speech(text: str, lang: str = "en") -> str:
    """Convert text to audio file (MP3)."""
    tts = gTTS(text=text, lang=lang)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tts.save(tmp.name)
    return tmp.name
