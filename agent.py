# agent.py
import os
import json
import time
from typing import List, Dict, Any, Optional

# Primary LLM wrapper: supports OpenAI (default) and pluggable methods for AWS Bedrock
try:
    import openai
except Exception:
    openai = None

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", None)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")  # or "bedrock"

# Safety: Use relatively small tokens in hackathon setting
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # change if you don't have access
DEFAULT_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))

if LLM_PROVIDER == "openai" and OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY

def chat_with_openai(system_prompt: str, messages: List[Dict[str,str]], max_tokens=512, temperature=DEFAULT_TEMPERATURE) -> str:
    """
    Send chat to OpenAI. messages: [{'role':'user'/'assistant'/'system', 'content':'...'}]
    """
    if openai is None:
        raise RuntimeError("openai package not installed. Install from requirements or set LLM_PROVIDER.")
    # note: model naming might vary based on your access
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    payload_messages = [{"role":"system", "content": system_prompt}] + messages
    resp = openai.ChatCompletion.create(
        model=model,
        messages=payload_messages,
        max_tokens=max_tokens,
        temperature=temperature
    )
    text = resp.choices[0].message.content
    return text

# Placeholder Bedrock interface (commented) - fill in with actual AWS calls if you have access.
def chat_with_bedrock(system_prompt: str, messages: List[Dict[str,str]], max_tokens=512, temperature=DEFAULT_TEMPERATURE) -> str:
    """
    Implement Bedrock call here using boto3 client for bedrock-runtime.
    For hackathon, you can replace with OpenAI above if Bedrock not available.
    """
    # Example pseudocode:
    # import boto3
    # client = boto3.client('bedrock-runtime')
    # request_payload = { ... }
    # response = client.invoke_model(...)
    raise NotImplementedError("Bedrock integration not implemented. Use OpenAI or implement Bedrock API call here.")

class EduGenieAgent:
    def __init__(self, persona: Optional[str]=None):
        self.persona = persona or "You are EduGenie, a friendly, patient AI tutor. Keep answers clear, concise and pedagogical."
        # simple memory - not persistent; full persistence handled elsewhere
        self.conversation_history: List[Dict[str,str]] = []

    def ask(self, user_text: str, context: Optional[List[Dict[str,str]]]=None) -> str:
        """
        Main method to ask the LLM. Keeps conversation memory for the session.
        """
        context = context or []
        self.conversation_history.append({"role":"user", "content":user_text})
        messages = context + self.conversation_history[-6:]  # keep last few messages
        if LLM_PROVIDER == "openai":
            out = chat_with_openai(self.persona, messages)
        else:
            out = chat_with_bedrock(self.persona, messages)
        self.conversation_history.append({"role":"assistant", "content":out})
        return out

    def explain_step_by_step(self, concept: str, style: str="simple") -> str:
        prompt = f"Explain the concept '{concept}' in a {style} manner with examples and a short 2-question quiz at the end."
        return self.ask(prompt)

    def generate_quiz(self, topic: str, difficulty: str="easy", num_q: int=3) -> Dict[str, Any]:
        """
        Basic prompt to generate multiple choice quizzes; fallback to local heuristics if LLM not configured.
        """
        prompt = f"Create {num_q} multiple choice questions (4 options each) on '{topic}' at {difficulty} difficulty. Provide answer and 1-line explanation for each."
        resp = self.ask(prompt)
        # Try to parse structured output; if not, return text block
        return {"raw": resp}
