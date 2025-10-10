import streamlit as st
import json
import os
from pathlib import Path
from typing import Dict, Any, List
from agent import EduGenieAgent
from aws_utils import USE_AWS, save_progress_dynamodb, load_progress_dynamodb, init_progress_table

# Page config
st.set_page_config(page_title="EduGenie", page_icon="🧞‍♂️", layout="wide")
BASE_DIR = Path(__file__).parent

# Load lessons
DATA_FILE = BASE_DIR / "data" / "lessons.json"
with open(DATA_FILE, "r", encoding="utf-8") as f:
    LESSONS = json.load(f)

# CSS - clean, minimal, polished
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Load custom CSS
local_css("assets/custom.css")

# Initialize agent in session
if "agent" not in st.session_state:
    st.session_state.agent = EduGenieAgent()

if "user_id" not in st.session_state:
    st.session_state.user_id = st.sidebar.text_input("Username (for progress)", value="guest_user") or "guest_user"

# Load persistent progress if AWS enabled
if "progress" not in st.session_state:
    if USE_AWS:
        table_name = os.getenv("PROGRESS_TABLE", "EduGenieProgress")
        try:
            init_progress_table(table_name)
            p = load_progress_dynamodb(table_name, st.session_state.user_id)
            st.session_state.progress = p or {}
        except Exception:
            st.session_state.progress = {}
    else:
        st.session_state.progress = {}

# Layout: Landing / Tutor / Lessons / Teacher Dashboard
tabs = st.tabs(["Landing", "Tutor", "Lessons", "Teacher Dashboard"])

# -------------------
# Landing page
# -------------------
with tabs[0]:
    col1, col2 = st.columns([2,1])
    with col1:
        st.markdown('<div class="header">EduGenie — AI tutor that grants your learning wishes</div>', unsafe_allow_html=True)
        st.markdown("**Personalized, adaptive tutoring with instant quizzes and progress tracking.**")
        st.markdown("""
        - Chat with EduGenie to explain concepts in multiple styles (step-by-step, visual hints, ELI5).
        - Auto-generate quizzes that adapt to the student's level.
        - Teacher dashboard to monitor class progress and export CSVs.
        """)
        st.markdown("### Quick demo")
        if st.button("Try a demo question"):
            demo_ans = st.session_state.agent.ask("Explain Newton's second law in a simple way with an example.")
            st.info(demo_ans)
    with col2:
        logo_path = BASE_DIR / "assets" / "logo.png"
        if logo_path.exists():
            st.image(str(logo_path), width=220)
        else:
            st.markdown("🧞‍♂️ **EduGenie**")

# -------------------
# Tutor (chat) tab
# -------------------
with tabs[1]:
    st.subheader("Talk to EduGenie")
    # Chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    chat_col, side_col = st.columns([3,1])
    with chat_col:
        for turn in st.session_state.chat_history:
            role, text = turn
            if role == "user":
                st.markdown(f'<div class="user-bubble"><b>You:</b> {text}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="agent-bubble"><b>EduGenie:</b> {text}</div>', unsafe_allow_html=True)

        user_input = st.text_input("Ask EduGenie anything...", key="input_main")
        if st.button("Send", key="send_main"):
            if user_input.strip():
                st.session_state.chat_history.append(("user", user_input))
                answer = st.session_state.agent.ask(user_input)
                st.session_state.chat_history.append(("agent", answer))
                st.experimental_rerun()

    with side_col:
        st.markdown("**Quick prompts**")
        if st.button("Explain like I'm 5"):
            text = "Explain like I'm 5: " + (st.session_state.get("input_main") or "photosynthesis")
            st.session_state.chat_history.append(("user", text))
            ans = st.session_state.agent.ask(text)
            st.session_state.chat_history.append(("agent", ans))
            st.experimental_rerun()
        if st.button("Generate 3-question quiz (topic)"):
            topic = st.text_input("Topic for quiz", value="Linear equations")
            if topic:
                quiz = st.session_state.agent.generate_structured_quiz(topic, difficulty="easy", num_questions=3)
                st.session_state.current_generated_quiz = quiz
                st.success("Quiz generated, switch to Lessons -> Generated Quiz to take it.")
        st.markdown("---")
        st.markdown("**Session controls**")
        if st.button("Reset chat"):
            st.session_state.chat_history = []
            st.session_state.agent = EduGenieAgent()
            st.success("Session reset.")

# -------------------
# Lessons tab & quiz runner
# -------------------
with tabs[2]:
    left, right = st.columns([2,1])
    with left:
        st.header("Lessons")
        for domain, topics in LESSONS.items():
            with st.expander(domain.title()):
                for topic_key, topic in topics.items():
                    st.markdown(f"**{topic['title']}** — {topic.get('level','')}")
                    st.write(topic['content'])
                    cols = st.columns([1,1,1])
                    if cols[0].button("Ask EduGenie", key=f"ask_{domain}_{topic_key}"):
                        q = f"Explain the topic: {topic['title']} in a simple way with 2 practice problems."
                        res = st.session_state.agent.ask(q)
                        st.session_state.chat_history.append(("user", q))
                        st.session_state.chat_history.append(("agent", res))
                        st.experimental_rerun()
                    if cols[1].button("Start Quiz", key=f"startquiz_{domain}_{topic_key}"):
                        st.session_state.current_quiz = topic.get("quizzes", [])
                        st.session_state.current_quiz_meta = {"domain": domain, "topic": topic_key}
                        st.session_state.quiz_index = 0
                        st.session_state.quiz_score = 0
                        st.experimental_rerun()
                    if cols[2].button("Generate AI Quiz", key=f"aiquiz_{domain}_{topic_key}"):
                        quiz = st.session_state.agent.generate_structured_quiz(topic['title'], difficulty="easy", num_questions=3)
                        st.session_state.current_generated_quiz = quiz
                        st.success("AI quiz generated. Scroll to the right panel to take it.")

    with right:
        st.header("Quizzes & Progress")
        # If generated quiz active
        if st.session_state.get("current_generated_quiz"):
            gq = st.session_state.current_generated_quiz
            st.subheader(f"Generated Quiz: {gq.get('topic')}")
            if "gq_index" not in st.session_state:
                st.session_state.gq_index = 0
                st.session_state.gq_score = 0
            idx = st.session_state.gq_index
            questions = gq.get("questions", [])
            if idx < len(questions):
                q = questions[idx]
                st.write(q["question"])
                choice = st.radio("Options", q["options"], key=f"gq_choice_{idx}")
                if st.button("Submit answer", key=f"gq_submit_{idx}"):
                    selected_index = q["options"].index(choice) if choice in q["options"] else None
                    if selected_index == q.get("answer_index"):
                        st.success("Correct!")
                        st.session_state.gq_score += 1
                    else:
                        st.error(f"Wrong. Correct: {q['options'][q['answer_index']]}")
                        st.write("Explain:", q.get("explain", ""))
                    st.session_state.gq_index += 1
                    if st.session_state.gq_index >= len(questions):
                        st.success(f"Quiz done! Score {st.session_state.gq_score}/{len(questions)}")
                        # save to progress
                        st.session_state.progress.setdefault("quizzes", []).append({
                            "topic": gq.get("topic"),
                            "score": st.session_state.gq_score,
                            "total": len(questions)
                        })
                        # reset generated quiz
                        st.session_state.current_generated_quiz = None
                        st.session_state.gq_index = 0
                        st.session_state.gq_score = 0
            else:
                st.write("No questions in generated quiz.")
        elif st.session_state.get("current_quiz"):
            quiz = st.session_state.current_quiz
            idx = st.session_state.quiz_index
            qobj = quiz[idx]
            st.markdown(f"**Question {idx+1}/{len(quiz)}**")
            st.write(qobj["question"])
            choice = st.radio("Choose an option", qobj["options"], key=f"quiz_choice_{idx}")
            if st.button("Submit", key=f"quiz_submit_{idx}"):
                if choice == qobj["answer"]:
                    st.success("Correct!")
                    st.session_state.quiz_score += 1
                else:
                    st.error(f"Wrong. Correct: {qobj['answer']}")
                    st.write("Explain:", qobj.get("explain"))
                st.session_state.quiz_index += 1
                if st.session_state.quiz_index >= len(quiz):
                    st.success(f"Quiz finished: {st.session_state.quiz_score}/{len(quiz)}")
                    st.session_state.progress.setdefault("quizzes", []).append({
                        "topic": st.session_state.current_quiz_meta,
                        "score": st.session_state.quiz_score,
                        "total": len(quiz)
                    })
                    st.session_state.current_quiz = None
                    st.session_state.quiz_index = 0
                    st.session_state.quiz_score = 0
        else:
            st.write("No active quizzes. Generate or start a quiz from the lessons.")

        st.markdown("---")
        st.subheader("Progress snapshot")
        st.write(st.session_state.progress)

# -------------------
# Teacher Dashboard
# -------------------
with tabs[3]:
    st.header("Teacher Dashboard")
    st.markdown("Monitor class progress, view quizzes, and export CSV reports.")
    # For demo, progress is stored in session_state. In production, teacher view should aggregate across real users.
    # We will create a simple table view and CSV export.
    data_rows = []
    quizzes = st.session_state.progress.get("quizzes", [])
    for idx, q in enumerate(quizzes):
        # normalize record for CSV
        topic = q.get("topic")
        if isinstance(topic, dict):
            topic_str = json.dumps(topic)
        else:
            topic_str = str(topic)
        data_rows.append({
            "id": idx + 1,
            "user": st.session_state.user_id,
            "topic": topic_str,
            "score": q.get("score"),
            "total": q.get("total")
        })
    if data_rows:
        st.table(data_rows)
        # CSV export
        import pandas as pd
        df = pd.DataFrame(data_rows)
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV report", csv_bytes, file_name="edu_genie_progress.csv", mime="text/csv")
    else:
        st.info("No student quiz data yet. Run a quiz as a student to generate sample data.")

# -------------------
# Footer
# -------------------
st.markdown("---")
st.markdown("Built with ❤️ — EduGenie. For hackathon, set LLM_PROVIDER=openai for local testing or bedrock for AWS.")
