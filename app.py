import streamlit as st
from google import genai
from streamlit_mic_recorder import speech_to_text
import requests

st.set_page_config(page_title="UNIVOX Counsellor Simulator", layout="centered")
st.title("🎓 UNIVOX Counsellor Simulator")

# Webhook to Google Sheets
SHEET_WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbxxw6STfiO923NiJCTLE-Yujr5ybctx9XnGzs7_rlxxX_JQsz64-DZQpk16tBxpJsGQwA/exec"

# Sidebar: Counsellor Identification
st.sidebar.header("👤 Counsellor Profile")
counsellor_name = st.sidebar.text_input("Enter Your Name / ID:", placeholder="e.g. Vikas Chawla")

# Scenarios Library
scenarios = [
    "1. Working Professional - Online MBA: Asking about UGC-DEB validity, exam modes, and EMI plans.",
    "2. Anxious Parent - B.Tech: Demanding average placement packages, top recruiters, and campus safety.",
    "3. Budget-Conscious Student - BCA/MCA: Pushing hard for upfront scholarship discounts and installment fees.",
    "4. Career Switcher - Data Science/AI: Non-tech background asking if bridge classes are provided.",
    "5. Skeptical Student - Online vs Regular Degree: Asking if online degrees hold equal weight in MNCs.",
    "6. Distance Learning Seeker - BA/B.Com: Working full-time, asking about weekend classes.",
    "7. Urgent Admission Lead - Late Enquirer: Asking if late admission is allowed and registration waived.",
    "8. Study Abroad Aspirant - UK/Canada: Inquiring about IELTS waiver and stay-back visa.",
    "9. Aggressive Competitor Comparison: Comparing partner universities with Amity/Manipal.",
    "10. High-Intent Closer: Ready to pay today if given a 10% spot fee concession."
]

persona = st.selectbox("🎯 Choose Student Scenario:", scenarios)

if "messages" not in st.session_state:
    st.session_state.messages = []

if "current_scenario" not in st.session_state or st.session_state.current_scenario != persona:
    st.session_state.current_scenario = persona
    st.session_state.messages = []

# Display conversation
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Free Browser Voice Input
st.write("🎙️ **Tap to speak (English / Hinglish):**")
voice_text = speech_to_text(language='en-IN', start_prompt="🎙️ Start Speaking", stop_prompt="⏹️ Stop Speaking", key='speech_input')

user_input = None

if voice_text:
    user_input = voice_text

text_prompt = st.chat_input("Or type your response here...")
if text_prompt:
    user_input = text_prompt

# Helper function to generate content across available models
def call_gemini(api_key, prompt):
    client = genai.Client(api_key=api_key)
    # List of models ordered by preference
    candidate_models = ["gemini-3.6-flash", "gemini-2.5-flash", "gemini-2.5-pro"]
    last_error = None
    for model_name in candidate_models:
        try:
            res = client.models.generate_content(model=model_name, contents=prompt)
            if res and res.text:
                return res.text
        except Exception as e:
            last_error = e
            continue
    raise last_error

# Process User Message
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    api_key = st.secrets.get("GEMINI_API_KEY", "")
    if not api_key:
        st.error("API Key missing from Streamlit secrets.")
    else:
        system_instruction = f"Roleplay as a student/parent: {persona}. Respond in 1-2 realistic sentences in conversational English or Hinglish."
        chat_context = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
        full_prompt = f"{system_instruction}\n\nChat History:\n{chat_context}"
        
        try:
            with st.spinner("Student is typing..."):
                reply_text = call_gemini(api_key, full_prompt)
            st.session_state.messages.append({"role": "assistant", "content": reply_text})
            with st.chat_message("assistant"):
                st.write(reply_text)
        except Exception as err:
            st.error(f"Generation error: {err}")

# Evaluation & Sheet Logging
if st.sidebar.button("📊 End Call & Score Session"):
    if not counsellor_name:
        st.sidebar.error("⚠️ Please enter your Name in the sidebar before scoring.")
    else:
        api_key = st.secrets.get("GEMINI_API_KEY", "")
        if api_key and st.session_state.messages:
            transcript = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
            eval_prompt = f"Audit this counsellor-student call for {counsellor_name}. Scenario: {persona}\n\nTranscript:\n{transcript}\n\nScore out of 10 on Rapport, Clarity, and Objection Handling. Provide 3 specific tips."
            
            try:
                with st.spinner("Auditing call performance..."):
                    score_text = call_gemini(api_key, eval_prompt)
                st.sidebar.markdown("### 🏆 Scorecard")
                st.sidebar.write(score_text)
                
                if SHEET_WEBHOOK_URL:
                    payload = {
                        "counsellor_name": counsellor_name,
                        "scenario": persona,
                        "evaluation": score_text,
                        "transcript": transcript
                    }
                    try:
                        requests.post(SHEET_WEBHOOK_URL, json=payload, timeout=10)
                        st.sidebar.success("✅ Session logged to Google Sheet!")
                    except Exception:
                        st.sidebar.info("Logged locally.")
            except Exception as err:
                st.sidebar.error(f"Audit error: {err}")
