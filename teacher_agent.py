"""
Teacher Dashboard Utilities for EduGenie
- Generates class performance summaries
- Exports results to CSV
"""

import pandas as pd
import json
from io import BytesIO
from agent import EduGenieAgent

# Initialize a shared agent instance
tutor_agent = EduGenieAgent()

def generate_class_summary(student_scores):
    """
    student_scores: list of dicts -> [{"student": "Alice", "score": 80, "quiz_topic": "AI Basics"}, ...]
    Returns a pandas DataFrame summary + overall statistics.
    """
    if not student_scores or not isinstance(student_scores, list):
        return None, "No data provided"

    df = pd.DataFrame(student_scores)
    # Basic stats
    summary = {
        "Total Students": len(df),
        "Average Score": round(df["score"].mean(), 2),
        "Highest Score": df["score"].max(),
        "Lowest Score": df["score"].min(),
        "Topics Covered": list(df["quiz_topic"].unique())
    }

    # Generate AI feedback (optional)
    feedback_prompt = (
        f"Summarize the overall class performance briefly and give actionable feedback for the teacher:\n\n"
        f"Summary stats: {json.dumps(summary)}"
    )
    try:
        ai_feedback = tutor_agent.ask(feedback_prompt)
    except Exception as e:
        ai_feedback = f"(AI feedback unavailable: {e})"

    return df, ai_feedback


def export_class_performance_csv(df):
    """
    Converts class performance DataFrame to downloadable CSV bytes.
    """
    if df is None:
        return None
    buffer = BytesIO()
    df.to_csv(buffer, index=False)
    buffer.seek(0)
    return buffer
