import os, json, time
from typing import List, Dict, Any, Optional

# Use boto3 to call Bedrock runtime
try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
    HAS_BOTO3 = True
except Exception:
    HAS_BOTO3 = False

class AIAgent:
    """
    A lightweight agent wrapper that talks to Claude on Bedrock (Claude 3 Sonnet),
    and provides functions to analyze performance, generate plans and quizzes,
    evaluate responses, and run an autonomous learning cycle.
    """

    def __init__(self, region_name: str = "us-east-1", model_id: str = "anthropic.claude-3-sonnet"):
        self.region = region_name
        self.model_id = model_id
        self.client = None
        if HAS_BOTO3:
            try:
                self.client = boto3.client("bedrock-runtime", region_name=self.region)
            except Exception:
                self.client = None

    def _invoke(self, prompt: str, max_tokens: int = 800, temperature: float = 0.2) -> str:
        """
        Invoke Bedrock model. Returns model text or raises informative exception.
        """
        if not self.client:
            return "[BEDROCK_UNAVAILABLE] " + prompt[:200]
        try:
            payload = {
                "inputText": prompt
            }
            # Bedrock invoke_model API shape can vary — we use invoke_model with modelId and body as bytes
            resp = self.client.invoke_model(
                modelId=self.model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(payload).encode("utf-8"),
            )
            body = resp["body"].read()
            parsed = json.loads(body.decode("utf-8"))
            # different models return different keys; try common ones
            # For Claude-style responses, look for "outputText" or "completion"
            if isinstance(parsed, dict):
                for k in ("outputText", "completion", "result", "body", "text"):
                    if k in parsed:
                        val = parsed[k]
                        if isinstance(val, dict):
                            return val.get("content", "") or json.dumps(val)
                        return val
                # fallback: try top-level keys concatenation
                return json.dumps(parsed)
            return str(parsed)
        except (BotoCoreError, ClientError) as e:
            return f"[BEDROCK_ERROR] {str(e)}"
        except Exception as e:
            return f"[BEDROCK_EXCEPTION] {str(e)}"

    def analyze_performance(self, quiz_history: List[Dict[str, Any]], top_k: int = 3) -> List[str]:
        """
        Given user's quiz_history (list of {topic,score,total}), return top_k weak topics.
        """
        if not quiz_history:
            return []
        # compute correctness ratio per topic
        scores = {}
        counts = {}
        for rec in quiz_history:
            t = rec.get("topic", "General")
            scores[t] = scores.get(t, 0) + rec.get("score", 0)
            counts[t] = counts.get(t, 0) + max(1, rec.get("total", 1))
        ratios = {t: scores[t] / counts[t] for t in scores}
        # sort ascending (weakest first)
        sorted_topics = sorted(ratios.items(), key=lambda kv: kv[1])
        return [t for t, _ in sorted_topics[:top_k]]

    def generate_learning_plan(self, user: str, weak_topics: List[str], days: int = 3) -> str:
        """
        Use Bedrock Claude to generate a day-by-day learning plan for the weak topics.
        """
        if not weak_topics:
            return "No weak topics detected — keep practicing and take a diagnostic quiz!"
        prompt = (
            f"Create a concise {days}-day study plan for a learner who needs to strengthen: {', '.join(weak_topics)}. "
            "For each day, give short study objectives, 2 practice activities (one conceptual, one practical), and 1 micro-quiz question."
        )
        return self._invoke(prompt)

    def generate_quiz(self, topic: str, n_questions: int = 5, difficulty: str = "Medium") -> List[Dict[str, Any]]:
        """
        Ask the model to generate a JSON array of MCQs for the topic.
        Falls back to a simple text if model doesn't return JSON.
        """
        prompt = (
            f"Generate {n_questions} multiple-choice questions about '{topic}'. "
            f"Difficulty: {difficulty}. Output as JSON array with keys: q, options (list), answer (index or text), explanation."
        )
        txt = self._invoke(prompt)
        try:
            parsed = json.loads(txt)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            # best-effort parse: return a single open Q
            return [{"q": txt[:240], "options": [], "answer": "", "explanation": ""}]
        return []

    def evaluate_answer(self, question: str, user_answer: str, correct_answer: str) -> Dict[str, Any]:
        """
        Ask model to grade user's answer and produce short feedback.
        """
        prompt = (
            f"Grade this student answer. Q: {question}\nCorrect Answer: {correct_answer}\nStudent Answer: {user_answer}\n"
            "Respond in JSON: {correct: true/false, feedback: 'brief feedback'}"
        )
        txt = self._invoke(prompt)
        try:
            return json.loads(txt)
        except Exception:
            # fallback naive check
            correct = user_answer.strip().lower() == str(correct_answer).strip().lower()
            return {"correct": correct, "feedback": "Well done." if correct else f"Expected: {correct_answer}"}

    def run_learning_cycle(self, user: str, quiz_history: List[Dict[str, Any]], db) -> Dict[str, Any]:
        """
        High-level agent cycle: analyze → plan → generate quiz → return plan and quiz.
        Requires a db object that exposes save_learning_plan and other methods.
        """
        weak = self.analyze_performance(quiz_history)
        plan = self.generate_learning_plan(user, weak)
        # create a starter quiz for the top weak topic if exists
        starter_quiz = []
        if weak:
            starter_quiz = self.generate_quiz(weak[0], n_questions=5, difficulty="Easy")
        # store plan in DB (if db provided)
        if db is not None:
            try:
                db.save_learning_plan(user, {"plan": plan, "generated_at": int(time.time()), "weak_topics": weak})
            except Exception:
                pass
        return {"weak_topics": weak, "plan": plan, "starter_quiz": starter_quiz}
