import json
from tutor_agent import bedrock_generate

def generate_quiz(topic, difficulty="easy"):
    prompt = f"""
    Generate a {difficulty} multiple-choice quiz on {topic}.
    Format JSON as: [
      {{ "question": "...", "options": ["A","B","C","D"], "answer": "B", "explanation": "..." }}
    ]
    """
    response = bedrock_generate(prompt)
    try:
        return json.loads(response)
    except:
        return []
