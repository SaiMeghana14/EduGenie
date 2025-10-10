from tutor_agent import bedrock_generate

def generate_class_summary(student_data):
    prompt = f"""
    Summarize class performance from this data:
    {student_data}
    Highlight weak areas and suggest interventions.
    """
    return bedrock_generate(prompt)
