# app.py
import streamlit as st
import json
import os
from pathlib import Path
from typing import Dict, Any
from agent import EduGenieAgent
from aws_utils import USE_AWS, init_progress_table, save_progress_dynamodb, load_progress_dynamodb, text_to_speech_polly

# ---- Config ----
st.set_page_config(page_title="EduGenie", layout="wide", page_icon="🧞‍♂️")

BASE_DIR = Path(__file__).parent
DATA_FILE = BASE_DIR / "data" / "lessons.json"

# Load lessons
with open(DATA_FILE, "r", encoding="utf-8") as f:
    LESSONS = json.load(f)

# Initialize agent
if "agent" not in st.session_state:
    st.session_state.agent = EduGenieAgent()

if "user_id" not in st.session_state:
    st.session_state.user_id = st.text_input("Enter a username (for progress tracking)", value="guest_user") or "guest_user"

if "progress" not in st.session_state:
    # Attempt to load DynamoDB if enabled
    if USE_AWS:
        table_name = os.getenv("PROGRESS_TABLE", "EduGenieProgress")
        try:
            init_progress_table(table_name)
            p = load_progress_dynamodb(table_name, st.session_state.user_id)
            st.session_state.progress = p or {}
        except Exception as e:
            st.session_state.progress = {}
    else:
        st.session_state.progress = {}

# Layout
st.sidebar.image(str(BASE_DIR / "assets" / "logo.png"), width=140) if (BASE_DIR / "assets" / "logo.png").exists() else st.sidebar.title("EduGenie")
st.sidebar.header("Settings")
model_provider = st.sidebar.selectbox("LLM Provider", options=["openai", "bedrock"], index=0)
voice_enabled = st.sidebar.checkbox("Enable voice (gTTS / Polly)", value=False)
language = st.sidebar.selectbox("Language", ["English"], index=0)
st.sidebar.markdown("---")
st.sidebar.markdown("**Quick actions**")
if st.sidebar.button("Reset session chat"):
    st.session_state.agent = EduGenieAgent()
    st.success("Chat reset.")

# Main columns
col_left, col_mid, col_right = st.columns([1.5,2,1])

with col_left:
    st.header("Lessons")
    for domain, topics in LESSONS.items():
        with st.expander(domain.title()):
            for topic_key, topic in topics.items():
                st.write(f"**{topic['title']}** — {topic.get('level','')}")
                st.write(topic['content'])
                if st.button(f"Start quiz: {topic_key}", key=f"quiz_{domain}_{topic_key}"):
                    st.session_state.current_quiz = topic.get("quizzes", [])
                    st.session_state.current_quiz_meta = {"domain":domain, "topic":topic_key}
                    st.session_state.quiz_index = 0
                    st.session_state.quiz_score = 0
                    st.experimental_rerun()
                if st.button(f"Ask EduGenie about {topic_key}", key=f"ask_{domain}_{topic_key}"):
                    q = f"Explain the topic: {topic['title']} in a simple way and provide 2 example problems with solutions."
                    ans = st.session_state.agent.explain_step_by_step(topic['title'], style="simple")
                    st.session_state.last_answer = ans
                    st.experimental_rerun()

with col_mid:
    st.header("EduGenie — Chat & Tutor")
    # Chat area
    chat_container = st.container()
    with chat_container:
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []  # list of (role, text)

        for role, text in st.session_state.chat_history:
            if role == "user":
                st.markdown(f"**You:** {text}")
            else:
                st.markdown(f"**EduGenie:** {text}")

        user_input = st.text_input("Ask EduGenie anything (math, concepts, practice questions)...", key="user_input")
        col_prompt1, col_prompt2 = st.columns([1,1])
        with col_prompt1:
            if st.button("Send"):
                if user_input.strip():
                    st.session_state.chat_history.append(("user", user_input))
                    answer = st.session_state.agent.ask(user_input)
                    st.session_state.chat_history.append(("agent", answer))
                    st.session_state.last_answer = answer
                    # Optionally play voice
                    if voice_enabled:
                        try:
                            if USE_AWS:
                                audio_bytes = text_to_speech_polly(answer)
                                st.audio(audio_bytes, format="audio/mp3")
                            else:
                                # use gTTS fallback
                                from gtts import gTTS
                                from io import BytesIO
                                tts = gTTS(answer)
                                fp = BytesIO()
                                tts.write_to_fp(fp)
                                fp.seek(0)
                                st.audio(fp.read(), format="audio/mp3")
                        except Exception as e:
                            st.warning(f"Voice playback failed: {e}")

        with col_prompt2:
            if st.button("Explain like I'm 5"):
                q = f"Explain this like I'm 5: {user_input}"
                st.session_state.chat_history.append(("user", q))
                ans = st.session_state.agent.ask(q)
                st.session_state.chat_history.append(("agent", ans))
                st.session_state.last_answer = ans

    # Show last answer prominently
    if "last_answer" in st.session_state:
        st.markdown("---")
        st.subheader("Latest explanation")
        st.write(st.session_state.last_answer)

with col_right:
    st.header("Quiz & Progress")
    # Quiz flow
    if st.session_state.get("current_quiz"):
        quiz = st.session_state.current_quiz
        idx = st.session_state.quiz_index
        qobj = quiz[idx]
        st.markdown(f"**Question {idx+1}/{len(quiz)}**")
        st.write(qobj["question"])
        choice = st.radio("Choose an option", qobj["options"], key=f"qchoice_{idx}")
        if st.button("Submit Answer", key=f"submit_{idx}"):
            if choice == qobj["answer"]:
                st.success("Correct!")
                st.session_state.quiz_score += 1
            else:
                st.error(f"Wrong. Correct answer: {qobj['answer']}")
                st.write("Explanation:", qobj.get("explain", ""))
            st.session_state.quiz_index += 1
            if st.session_state.quiz_index >= len(quiz):
                st.success(f"Quiz finished! Score: {st.session_state.quiz_score}/{len(quiz)}")
                # Save progress locally or to DynamoDB
                st.session_state.progress.setdefault("quizzes", []).append({
                    "topic": st.session_state.current_quiz_meta,
                    "score": st.session_state.quiz_score,
                    "total": len(quiz)
                })
                # If AWS enabled, save
                if USE_AWS:
                    try:
                        table_name = os.getenv("PROGRESS_TABLE", "EduGenieProgress")
                        save_progress_dynamodb(table_name, st.session_state.user_id, st.session_state.progress)
                    except Exception as e:
                        st.warning(f"Failed to save progress to DynamoDB: {e}")
                # clear quiz
                st.session_state.current_quiz = None
                st.session_state.quiz_index = 0
                st.session_state.quiz_score = 0
            st.experimental_rerun()
    else:
        st.write("No active quiz. Start a quiz from Lessons on the left.")

    st.markdown("---")
    st.subheader("Progress summary")
    st.write(st.session_state.progress)

# Footer / help
st.markdown("---")
st.markdown("Developed by **EduGenie** — AI tutor that grants your learning wishes. Built with Streamlit.")

