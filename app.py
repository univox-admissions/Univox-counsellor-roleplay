import streamlit as st
from streamlit_mic_recorder import speech_to_text
import requests

st.set_page_config(page_title="UNIVOX Counsellor Simulator", layout="centered")
st.title("🎓 UNIVOX Counsellor Simulator")

SHEET_WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbxxw6STfiO923NiJCTLE-Yujr5ybctx9XnGzs7_rlxxX_JQsz64-DZQpk16tBxpJsGQwA/exec"

st.sidebar.header("👤 Counsellor Profile")
counsellor_name = st.sidebar.text_input("Enter Your Name / ID:", placeholder="e.g. Vikas Chawla")

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

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

st.write("🎙️ **Tap to speak (English / Hinglish):**")
voice_text = speech_to_text(language='en-IN', start_prompt="🎙️ Start Speaking", stop_prompt="⏹️ Stop Speaking", key='speech_input')

user_input = None
if voice_text:
    user_input = voice_text

text_prompt = st.chat_input("Or type your response here...")
if text_prompt:
    user_input = text_prompt

def call_ai(api_key, system_instruction, history_text):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={api_key}"
    payload = {
        "contents": [{
            "parts": [{"text": f"{system_instruction}\n\nChat History:\n{history_text}"}]
        }]
    }
    r = requests.post(url, json=payload, timeout=20)
    data = r.json()
    if "candidates" in data and len(data["candidates"]) > 0:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    elif "error" in data:
        raise Exception(data["error"].get("message", "API error"))
    return "I couldn't process that, please say it again."

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    api_key = st.secrets.get("GEMINI_API_KEY", "")
    if not api_key:
        st.error("API Key missing in secrets.")
    else:
        sys_inst = f"Roleplay as a prospective student: {persona}. Reply to the counsellor in 1-2 realistic sentences in conversational English or Hinglish."
        chat_context = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
        
        try:
            with st.spinner("Student replying..."):
                reply = call_ai(api_key, sys_inst, chat_context)
            st.session_state.messages.append({"role": "assistant", "content": reply})
            with st.chat_message("assistant"):
                st.write(reply)
        except Exception as e:
            st.error(f"Error: {e}")

if st.sidebar.button("📊 End Call & Score Session"):
    if not counsellor_name:
        st.sidebar.error("⚠️ Please enter your Name in the sidebar.")
    else:
        api_key = st.secrets.get("GEMINI_API_KEY", "")
        if api_key and st.session_state.messages:
            transcript = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
            eval_inst = f"Audit this counsellor call for {counsellor_name}. Scenario: {persona}\nScore out of 10 on Rapport, Pitching, and Objection Handling. Give 3 closing tips."
            
            try:
                with st.spinner("Scoring..."):
                    score_res = call_ai(api_key, eval_inst, transcript)
                st.sidebar.markdown("### 🏆 Scorecard")
                st.sidebar.write(score_res)
                
                if SHEET_WEBHOOK_URL:
                    requests.post(SHEET_WEBHOOK_URL, json={
                        "counsellor_name": counsellor_name,
                        "scenario": persona,
                        "evaluation": score_res,
                        "transcript": transcript
                    }, timeout=10)
                    st.sidebar.success("✅ Logged to Sheet!")
            except Exception as e:
                st.sidebar.error(f"Error: {e}")
