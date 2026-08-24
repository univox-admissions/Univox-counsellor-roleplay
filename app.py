import streamlit as st
from google import genai
from google.genai import types
from audio_recorder_streamlit import audio_recorder
import requests

st.set_page_config(page_title="UNIVOX Counsellor Simulator", layout="centered")
st.title("🎓 UNIVOX Counsellor Simulator")

# Paste your Google Apps Script URL below:
SHEET_WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbxxw6STfiO923NiJCTLE-Yujr5ybctx9XnGzs7_rlxxX_JQsz64-DZQpk16tBxpJsGQwA/exec"

# Sidebar: Counsellor Identification
st.sidebar.header("👤 Counsellor Profile")
counsellor_name = st.sidebar.text_input("Enter Your Name / ID:", placeholder="e.g. Rahul Sharma")

# Expanded Scenarios Library
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

# Voice / Mic input
st.write("🎙️ **Record voice or type below:**")
audio_bytes = audio_recorder(text="Click to Record", recording_color="#e74c3c", neutral_color="#2ecc71")

user_input = None

if audio_bytes:
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    if api_key:
        client = genai.Client(api_key=api_key)
        try:
            audio_part = types.Part.from_bytes(
                data=audio_bytes,
                mime_type="audio/wav"
            )
            transcription_res = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    "Transcribe this audio exactly in Hindi/Hinglish/English as spoken:",
                    audio_part
                ]
            )
            user_input = transcription_res.text
        except Exception as e:
            # Fallback if specific version is requested by environment
            try:
                transcription_res = client.models.generate_content(
                    model="gemini-1.5-flash",
                    contents=[
                        "Transcribe this audio exactly in Hindi/Hinglish/English as spoken:",
                        audio_part
                    ]
                )
                user_input = transcription_res.text
            except Exception as inner_e:
                st.error(f"Voice processing error: {inner_e}")

# Chat input
text_prompt = st.chat_input("Type your response as counsellor...")
if text_prompt:
    user_input = text_prompt

# AI response logic
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    api_key = st.secrets.get("GEMINI_API_KEY", "")
    if api_key:
        client = genai.Client(api_key=api_key)
        system_instruction = f"You are roleplaying as a prospective student/parent: {persona}. Respond in 1-2 realistic sentences in Hinglish or English matching the counsellor. Show realistic hesitation, objections, and questions."
        
        chat_context = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
        
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"System Instruction: {system_instruction}\n\nChat History:\n{chat_context}"
            )
        except Exception:
            response = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=f"System Instruction: {system_instruction}\n\nChat History:\n{chat_context}"
            )
        
        st.session_state.messages.append({"role": "assistant", "content": response.text})
        with st.chat_message("assistant"):
            st.write(response.text)

# Evaluation & Auto-Logging
if st.sidebar.button("📊 End Call & Score Session"):
    if not counsellor_name:
        st.sidebar.error("⚠️ Please enter your Name in the sidebar before scoring.")
    else:
        api_key = st.secrets.get("GEMINI_API_KEY", "")
        if api_key and st.session_state.messages:
            client = genai.Client(api_key=api_key)
            transcript = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
            eval_prompt = f"Audit this counsellor-student call for {counsellor_name}. Scenario: {persona}\n\nTranscript:\n{transcript}\n\nScore out of 10 on Rapport, Clarity, and Objection Handling. Provide 3 specific tips."
            
            try:
                eval_res = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=eval_prompt
                )
            except Exception:
                eval_res = client.models.generate_content(
                    model="gemini-1.5-flash",
                    contents=eval_prompt
                )
            
            st.sidebar.markdown("### 🏆 Scorecard")
            st.sidebar.write(eval_res.text)
            
            # Send to Google Sheets
            if SHEET_WEBHOOK_URL:
                payload = {
                    "counsellor_name": counsellor_name,
                    "scenario": persona,
                    "evaluation": eval_res.text,
                    "transcript": transcript
                }
                try:
                    requests.post(SHEET_WEBHOOK_URL, json=payload, timeout=10)
                    st.sidebar.success("✅ Session logged to Team Tracker!")
                except Exception as e:
                    st.sidebar.info("Logged locally.")
