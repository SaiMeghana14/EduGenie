"""
EduGenieAgent – Dual LLM Support (OpenAI / Bedrock)
---------------------------------------------------
- chat_with_bedrock: invoke_model via boto3 bedrock-runtime client
- generate_structured_quiz: JSON-based quiz generation
- Graceful fallbacks for offline / keyless mode
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional

# ---------------------------------
# Configuration
# ---------------------------------
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()  # "openai" or "bedrock"
DEFAULT_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
DEFAULT_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "512"))
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ---------------------------------
# OpenAI Setup
# ---------------------------------
client = None
try:
    from openai import OpenAI
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        client = OpenAI(api_key=api_key)
    else:
        logger.warning("⚠️ OPENAI_API_KEY not set – using offline mock mode.")
except Exception as e:
    logger.warning(f"⚠️ OpenAI client not available: {e}")
    client = None

# ---------------------------------
# Bedrock Setup
# ---------------------------------
bedrock_client = None
if LLM_PROVIDER == "bedrock":
    try:
        import boto3
        bedrock_client = boto3.client("bedrock-runtime")
    except Exception as e:
        logger.warning(f"⚠️ Bedrock client unavailable: {e}")
        bedrock_client = None

# ---------------------------------
# OpenAI Invocation (modern API)
# ---------------------------------

def _invoke_openai_chat(system_prompt, messages, model="gpt-4o-mini", temperature=0.7, max_tokens=500):
    """
    Handles communication with the OpenAI chat model using the new v1 API.
    Compatible with openai>=1.0.
    """
    client = OpenAI()

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                *messages
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )

        # ✅ Extract model's response
        reply = response.choices[0].message.content.strip()
        return reply

    except Exception as e:
        print(f"❌ Error calling OpenAI API: {e}")
        return "Sorry, I ran into an issue while generating a response."

# ---------------------------------
# Bedrock Invocation
# ---------------------------------
def _invoke_bedrock_model(model_id, input_text, max_tokens=DEFAULT_MAX_TOKENS, temperature=DEFAULT_TEMPERATURE):
    if bedrock_client is None:
        return f"[Bedrock unavailable – fallback for: {input_text[:50]}...]"

    try:
        body = json.dumps({"input": input_text, "maxTokens": max_tokens, "temperature": temperature}).encode("utf-8")
        resp = bedrock_client.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=body
        )
        raw = resp.get("body").read().decode("utf-8")
        parsed = json.loads(raw)
        return parsed.get("output", raw)
    except Exception as e:
        logger.error(f"Bedrock invoke failed: {e}")
        return "[Bedrock error: fallback text]"

# ---------------------------------
# EduGenieAgent Class
# ---------------------------------
class EduGenieAgent:
    def __init__(self, persona: Optional[str] = None, bedrock_model: Optional[str] = None):
        self.persona = persona or (
            "You are EduGenie, a friendly AI tutor who explains simply and clearly."
        )
        self.history: List[Dict[str, str]] = []
        self.bedrock_model = bedrock_model or os.getenv("BEDROCK_MODEL_ID", "amazon.titan-text-express-v1")
        logger.info("EduGenieAgent initialized with provider=%s", LLM_PROVIDER)

    def ask(self, user_text: str, max_tokens: int = DEFAULT_MAX_TOKENS) -> str:
        self.history.append({"role": "user", "content": user_text})
        messages = self.history[-6:]

        if LLM_PROVIDER == "openai":
            resp = _invoke_openai_chat(DEFAULT_MODEL, messages, temperature=DEFAULT_TEMPERATURE, max_tokens=max_tokens)
        else:
            prompt = self._messages_to_prompt(messages)
            resp = _invoke_bedrock_model(self.bedrock_model, prompt, max_tokens=max_tokens)
        
        self.history.append({"role": "assistant", "content": resp})
        return resp

    def _messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
        lines = [f"System: {self.persona}", ""]
        for m in messages:
            role = m.get("role", "user")
            prefix = "User" if role == "user" else "Assistant"
            lines.append(f"{prefix}: {m.get('content', '')}")
        lines.append("\nAssistant:")
        return "\n".join(lines)

    def generate_structured_quiz(self, topic: str, difficulty: str = "easy", num_questions: int = 3) -> Dict[str, Any]:
        system = (
            "You are EduGenie, an expert teacher. Return valid JSON only in this schema: "
            '{"topic":"...","questions":[{"question":"...","options":["a","b","c","d"],"answer_index":0,"explain":"..."}]}'
        )
        user_prompt = (
            f"Create {num_questions} multiple-choice questions on '{topic}' ({difficulty} level). "
            "Each question must have 4 options and one correct answer. Return JSON only."
        )

        if LLM_PROVIDER == "openai":
            messages = [{"role": "system", "content": system}, {"role": "user", "content": user_prompt}]
            raw = _invoke_openai_chat(DEFAULT_MODEL, messages, max_tokens=800)
        else:
            raw = _invoke_bedrock_model(self.bedrock_model, system + "\n\n" + user_prompt, max_tokens=800)

        try:
            start, end = raw.find("{"), raw.rfind("}") + 1
            if start != -1 and end > start:
                parsed = json.loads(raw[start:end])
                if "questions" in parsed:
                    return parsed
        except Exception:
            pass

        logger.warning("⚠️ LLM JSON parse failed – using fallback quiz.")
        return {
            "topic": topic,
            "questions": [
                {"question": f"SAMPLE: {topic} Q{i+1}", "options": ["A", "B", "C", "D"], "answer_index": 0, "explain": "Sample explanation."}
                for i in range(num_questions)
            ]
        }
