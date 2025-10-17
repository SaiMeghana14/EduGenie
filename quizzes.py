from utils import GeminiClient
import streamlit as st
import json

gemini = GeminiClient(api_key=st.secrets["GEMINI_API_KEY"])

def generate_quiz(topic: str, n_questions: int = 5):
    prompt = f"Create {n_questions} multiple-choice questions on {topic}. Return JSON array with 'q', 'options', 'answer'."
    resp = gemini.chat(prompt).get("text", "")
    try:
        return json.loads(resp)
    except:
        # fallback
        return [{"q": f"Sample Q about {topic}", "options": ["A","B","C","D"], "answer": "A"}]
