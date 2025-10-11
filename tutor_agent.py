import streamlit as st
import json
import random
from aws_utils import translate_text, synthesize_speech, save_progress_dynamodb, load_progress_dynamodb, USE_AWS
from agent import EduGenieAgent

# ----------------------------------------------------
# 🎓 Tutor UI Component
# ----------------------------------------------------
def tutor_ui():
    st.markdown("## 👋 Welcome to EduGenie – Your AI Tutor")
    st.write("Learn interactively with AI-powered lessons, quizzes, and feedback.")

    # Session state setup
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "student_id" not in st.session_state:
        st.session_state.student_id = f"user_{random.randint(1000,9999)}"

    st.sidebar.header("⚙️ Settings")
    lang = st.sidebar.selectbox("Preferred Language", ["English", "Hindi", "Telugu"])
    voice_on = st.sidebar.checkbox("🎧 Enable Voice Narration", False)

    # Input area
    user_query = st.text_input("Ask EduGenie a question or start a topic:")
    if st.button("Ask"):
        if not user_query.strip():
            st.warning("Please enter a question or topic.")
            return

        # Generate AI answer
        response = call_bedrock_agent(user_query)
        if not response:
            response = fallback_llm_response(user_query)

        # Translate (if needed)
        if lang != "English":
            lang_code = {"Hindi": "hi", "Telugu": "te"}.get(lang, "en")
            response = translate_text(response, lang_code)

        # Save to history
        st.session_state.chat_history.append(("You", user_query))
        st.session_state.chat_history.append(("EduGenie", response))
        save_progress_dynamodb(st.session_state.student_id, {"last_query": user_query, "last_response": response})

        # Display
        st.markdown(f"**EduGenie:** {response}")

        # Voice narration
        if voice_on:
            audio_data = synthesize_speech(response)
            if audio_data:
                st.audio(audio_data, format="audio/mp3")

    # Chat history
    if st.session_state.chat_history:
        with st.expander("🗒️ Chat History"):
            for sender, msg in st.session_state.chat_history[-10:]:
                st.markdown(f"**{sender}:** {msg}")

    # Launch quiz
    if st.button("🧠 Take a Quiz"):
        show_quiz_ui(lang)

# ----------------------------------------------------
# 🧩 Quiz Generator and Evaluator
# ----------------------------------------------------
def show_quiz_ui(lang="English"):
    st.markdown("### 🧠 AI-Generated Quiz")
    topic = st.text_input("Enter a topic for quiz generation:")

    if st.button("Generate Quiz"):
        with st.spinner("Generating quiz with AI..."):
            quiz_data = call_bedrock_agent(f"Create 3 short quiz questions on {topic} in JSON with options and correct answers.")
            if not quiz_data:
                quiz_data = fallback_llm_response(topic)
            
            # Parse JSON safely
            try:
                quiz = json.loads(quiz_data)
                st.session_state.quiz = quiz
            except:
                st.warning("Invalid AI response, using sample quiz.")
                st.session_state.quiz = sample_quiz()

    if "quiz" in st.session_state:
        score = 0
        for q in st.session_state.quiz:
            st.markdown(f"**Q:** {q['question']}")
            user_ans = st.radio("Select an answer:", q["options"], key=q["question"])
            if st.button(f"Check {q['question']}"):
                if user_ans == q["answer"]:
                    st.success("✅ Correct!")
                    score += 1
                else:
                    st.error(f"❌ Wrong. Correct answer: {q['answer']}")
        st.info(f"Your Score: {score}/{len(st.session_state.quiz)}")

def sample_quiz():
    return [
        {"question": "What does AI stand for?", "options": ["Artificial Intelligence", "Analog Input", "Automated Interface"], "answer": "Artificial Intelligence"},
        {"question": "Which company provides AWS Bedrock?", "options": ["Microsoft", "Google", "Amazon"], "answer": "Amazon"},
        {"question": "What is DynamoDB used for?", "options": ["Storage", "Computation", "Networking"], "answer": "Storage"},
    ]
