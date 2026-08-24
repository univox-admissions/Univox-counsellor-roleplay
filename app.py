import streamlit as st
from google import genai
from audio_recorder_streamlit import audio_recorder
import io

st.set_page_config(page_title="UNIVOX Counsellor Simulator", layout="centered")
st.title("🎓 UNIVOX Counsellor Simulator")

# Expanded Situations Library
scenarios = [
    "1. Working Professional - Online MBA: Asking about UGC-DEB validity, exam modes, and EMI plans.",
    "2. Anxious Parent - B.Tech: Demanding average placement packages, top recruiters, and campus safety.",
    "3. Budget-Conscious Student - BCA/MCA: Pushing hard for upfront scholarship discounts and semester installment fees.",
    "4. Career Switcher - Data Science/AI: Non-tech background asking if math/coding bridge classes are provided.",
    "5. Skeptical Student - Online vs Regular Degree: Asking if online degrees hold equal weight in government exams & MNCs.",
    "6. Distance Learning Seeker - BA/B.Com: Working full-time, asking about weekend classes and recorded lectures.",
    "7. Urgent Admission Lead - Late Enquirer: Asking if late admission is allowed and if registration fee can be waived.",
    "8. Study Abroad Aspirant - UK/Canada: Inquiring about IELTS waiver, stay-back work visa, and living cost loans.",
    "9. Aggressive Competitor Comparison: Comparing UNIVOX partner universities with Amity/Manipal and asking why choose here.",
    "10. High-Intent Closer: Ready to pay today if given a 10% spot admission fee concession."
]

persona = st.selectbox("🎯 Choose Student Scenario:", scenarios)

if "messages" not in st.session_state:
    st.session_state.messages = []

# Reset conversation when switching scenarios
if "current_scenario" not in st.session_state or st.session_state.current_scenario != persona:
    st.session_state.current_scenario = persona
    st.session_state.messages = []

# Display conversation history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Audio input recording
st.write("🎙️ **Record your voice or type below:**")
audio_bytes = audio_recorder(text="Click to Record Audio", recording_color="#e74c3c", neutral_color="#2ecc71")

user_input = None

if audio_bytes:
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    if api_key:
        client = genai.Client(api_key=api_key)
        audio_file = io.BytesIO(audio_bytes)
        audio_part = client.files.upload(file=audio_file, mime_type="audio/wav")
        transcription_res = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=["Transcribe this audio exactly in Hindi/Hinglish/English as spoken:", audio_part]
        )
        user_input = transcription_res.text

# Text input box
text_prompt = st.chat_input("Type your response as counsellor...")
if text_prompt:
    user_input = text_prompt

# Process the response
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    api_key = st.secrets.get("GEMINI_API_KEY", "")
    if api_key:
        client = genai.Client(api_key=api_key)
        system_instruction = f"You are roleplaying as a prospective student/parent in this scenario: {persona}. Respond in 1-2 realistic, conversational sentences in Hinglish or English matching the user. Show realistic hesitation, objections, and questions."
        
        chat_context = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"System Instruction: {system_instruction}\n\nChat History:\n{chat_context}"
        )
        
        st.session_state.messages.append({"role": "assistant", "content": response.text})
        with st.chat_message("assistant"):
            st.write(response.text)

# Sidebar for scoring
if st.sidebar.button("📊 End Call & Score Session"):
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    if api_key and st.session_state.messages:
        client = genai.Client(api_key=api_key)
        transcript = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
        eval_prompt = f"Audit this counsellor-student roleplay call. Scenario: {persona}\n\nTranscript:\n{transcript}\n\nScore out of 10 on Rapport, Clarity, and Objection Handling. Provide 3 specific tips to close this student next time."
        
        eval_res = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=eval_prompt
        )
        st.sidebar.markdown("### 🏆 Performance Scorecard")
        st.sidebar.write(eval_res.text)
