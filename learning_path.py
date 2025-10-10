import json
from tutor_agent import bedrock_generate

def generate_learning_path(topic, level="beginner"):
    prompt = f"""
    Create a personalized learning roadmap for {topic} at {level} level.
    Output as JSON with keys: milestones, skills, recommended_resources.
    """
    response = bedrock_generate(prompt)
    try:
        return json.loads(response)
    except:
        return {"milestones": [], "skills": [], "recommended_resources": []}
