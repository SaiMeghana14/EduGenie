"""
EduGenieAgent - supports OpenAI (local testing) and Amazon Bedrock (production / hackathon).
- chat_with_bedrock implements a robust invoke_model using boto3 bedrock-runtime client.
- generate_structured_quiz requests JSON-formatted quizzes from the LLM and parses them.
- Fallbacks provided if LLM or parsing fails.
"""

import os
import json
import time
import logging
from typing import List, Dict, Any, Optional

# LLM provider selection
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")  # "openai" or "bedrock"
DEFAULT_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))
DEFAULT_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "512"))

# OpenAI client (optional quick local testing)
openai = None
if LLM_PROVIDER == "openai":
    try:
        import openai as _openai
        openai = _openai
        openai.api_key = os.getenv("OPENAI_API_KEY", None)
    except Exception:
        openai = None

# Bedrock / boto3
bedrock_client = None
if LLM_PROVIDER == "bedrock":
    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError
        bedrock_client = boto3.client("bedrock-runtime")
    except Exception:
        bedrock_client = None

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# ------------------------------
# Helpers: Bedrock invoke wrapper
# ------------------------------
def _invoke_bedrock_model(model_id: str, input_text: str, 
                          content_type: str = "application/json",
                          accept: str = "application/json",
                          max_tokens: int = DEFAULT_MAX_TOKENS,
                          temperature: float = DEFAULT_TEMPERATURE) -> str:
    """
    Invoke a Bedrock model via boto3 bedrock-runtime client.
    Sends a JSON body with a standard "input" field. Handles common response shapes
    and returns the generated text as a single string. Robust to variations in response.
    Requires AWS credentials set in the environment/instance profile and proper IAM: bedrock:InvokeModel.
    See Bedrock docs for model-specific parameter shapes. :contentReference[oaicite:1]{index=1}
    """
    if bedrock_client is None:
        raise RuntimeError("Bedrock client not initialized. Ensure LLM_PROVIDER=bedrock and boto3 configured.")

    # The request body structure differs by model; many accept {"input": "..."} for text prompts.
    payload = {
        "input": input_text,
        "maxTokens": max_tokens,
        "temperature": temperature
    }
    body_bytes = json.dumps(payload).encode("utf-8")

    try:
        resp = bedrock_client.invoke_model(
            modelId=model_id,
            contentType=content_type,
            accept=accept,
            body=body_bytes
        )
    except Exception as e:
        logger.exception("Bedrock invoke_model failed")
        raise

    # Read response body (stream-like)
    raw = None
    try:
        # For many SDK versions: resp['body'] is a StreamingBody
        body_stream = resp.get("body")
        if body_stream is not None:
            raw = body_stream.read().decode("utf-8")
        else:
            # some responses may be in 'blob' or direct fields
            raw = json.dumps(resp)
    except Exception:
        raw = json.dumps(resp)

    # Try to parse known response shapes
    # Common Bedrock text output shapes:
    # 1) {"outputs":[{"content":[{"type":"text/plain","text":"..."}]}]}
    # 2) Amazon titan returns {"output":"..."} or raw text
    # 3) Anthropic or other vendor wrappers may vary.
    try:
        parsed = json.loads(raw)
        # shape 1
        if isinstance(parsed, dict):
            # Check outputs.content.text
            outputs = parsed.get("outputs")
            if outputs and isinstance(outputs, list):
                for o in outputs:
                    content = o.get("content")
                    if isinstance(content, list):
                        for c in content:
                            if isinstance(c, dict) and c.get("type") in ("text/plain", "text"):
                                text = c.get("text") or c.get("text")
                                if text:
                                    return text
            # direct text
            if "output" in parsed and isinstance(parsed["output"], str):
                return parsed["output"]
            # sometimes model returns 'results' or 'generated_text'
            for key in ("generated_text", "result", "text"):
                if key in parsed and isinstance(parsed[key], str):
                    return parsed[key]
    except Exception:
        # not JSON or unexpected shape -> fall through and return raw
        pass

    # If above parsing didn't return, attempt naive extraction
    # If raw looks like JSON but couldn't parse to text, return raw string
    return raw


# ------------------------------
# OpenAI wrapper (quick local testing)
# ------------------------------
import os
from openai import OpenAI

# Initialize the new OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DEFAULT_TEMPERATURE = 0.7

def _invoke_openai_chat(model, messages, temperature=DEFAULT_TEMPERATURE, max_tokens=400):
    """
    Modern OpenAI Chat API invocation (compatible with v1.x)
    """
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return resp.choices[0].message.content

    except Exception as e:
        print(f"⚠️ OpenAI error: {e}")
        return f"[AI unavailable, returning fallback for: {messages[-1]['content'][:40]}...]"

# ------------------------------
# EduGenieAgent class
# ------------------------------
class EduGenieAgent:
    def __init__(self, persona: Optional[str] = None, bedrock_model: Optional[str] = None):
        self.persona = persona or ("You are EduGenie, a friendly patient AI tutor. "
                                   "Provide clear, step-by-step explanations, short examples, "
                                   "and short quizzes when appropriate.")
        self.history: List[Dict[str, str]] = []
        self.bedrock_model = bedrock_model or os.getenv("BEDROCK_MODEL_ID", "amazon.titan-text-express-v1")
        logger.info("EduGenieAgent initialized with provider=%s model=%s", LLM_PROVIDER, self.bedrock_model)

    def ask(self, user_text: str, max_tokens: int = DEFAULT_MAX_TOKENS) -> str:
        """
        Generic chat interface. Keeps a small local conversation history (session).
        """
        # append user
        self.history.append({"role": "user", "content": user_text})
        # build messages (last few turns)
        messages = self.history[-6:]  # keep last 6 for context

        if LLM_PROVIDER == "openai":
            resp = _invoke_openai_chat(self.persona, messages, temperature=DEFAULT_TEMPERATURE, max_tokens=max_tokens)
        else:
            # For bedrock we convert messages to a single prompt text
            prompt = self._messages_to_prompt(messages)
            resp = _invoke_bedrock_model(self.bedrock_model, prompt, max_tokens=max_tokens, temperature=DEFAULT_TEMPERATURE)
        # append assistant answer
        self.history.append({"role": "assistant", "content": resp})
        return resp

    def _messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
        """
        Convert messages list to a single text prompt for Bedrock models.
        This is a simple format: persona + conversation turn markers.
        """
        lines = [f"System: {self.persona}", ""]
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            prefix = "User" if role == "user" else "Assistant"
            lines.append(f"{prefix}: {content}")
        lines.append("\nAssistant:")
        return "\n".join(lines)

    # --------------------------
    # Structured quiz generation
    # --------------------------
    def generate_structured_quiz(self, topic: str, difficulty: str = "easy", num_questions: int = 3) -> Dict[str, Any]:
        """
        Ask LLM to return a JSON object with quizzes:
        {
          "topic": "...",
          "questions": [
             { "question": "...", "options": ["a","b","c","d"], "answer_index": 1, "explain": "..." }
          ]
        }
        This method tries to parse the returned JSON. If parsing fails, it provides a fallback simple quiz.
        """
        system = ("You are EduGenie, an expert teacher. Return valid JSON only. "
                  "Format exactly: {\"topic\":\"...\",\"questions\":[{\"question\":\"..\",\"options\":[\"..\",\"..\",\"..\",\"..\"],\"answer_index\":<0-3>,\"explain\":\"...\"}, ...] }")
        user_prompt = (f"Create {num_questions} multiple-choice questions on the topic '{topic}' at '{difficulty}' difficulty. "
                       "Each question must have 4 options. Provide the correct option's index with 0-based indexing. "
                       "Return JSON only with the schema described.")
        # For bedrock combine system + user into a single prompt string
        if LLM_PROVIDER == "openai":
            messages = [{"role": "system", "content": system}, {"role": "user", "content": user_prompt}]
            raw = _invoke_openai_chat(system, messages, max_tokens=800)
        else:
            prompt = system + "\n\n" + user_prompt
            raw = _invoke_bedrock_model(self.bedrock_model, prompt, max_tokens=800)
        # Try to extract JSON substring (robust)
        parsed = None
        try:
            # Sometimes models add text before/after JSON. Extract first JSON-like block.
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start != -1 and end != -1 and end > start:
                json_blob = raw[start:end]
                parsed = json.loads(json_blob)
        except Exception:
            parsed = None

        # Validate parsed structure
        if parsed and isinstance(parsed, dict) and "questions" in parsed:
            # basic sanity checks - ensure options lists and answer_index exist
            questions = parsed.get("questions", [])
            valid_questions = []
            for q in questions:
                if all(k in q for k in ("question", "options", "answer_index")) and isinstance(q["options"], list) and len(q["options"]) >= 2:
                    valid_questions.append(q)
            if len(valid_questions) >= 1:
                return {"topic": parsed.get("topic", topic), "questions": valid_questions}

        # Fallback: simple rule-based quiz generator (very basic)
        logger.warning("Structured quiz parsing failed. Using fallback generator. Raw LLM output: %s", raw[:200])
        fallback = {"topic": topic, "questions": []}
        for i in range(num_questions):
            fallback["questions"].append({
                "question": f"SAMPLE: {topic} question {i+1} (fallback)",
                "options": ["Option A", "Option B", "Option C", "Option D"],
                "answer_index": 0,
                "explain": "Fallback explanation: placeholder."
            })
        return fallback
