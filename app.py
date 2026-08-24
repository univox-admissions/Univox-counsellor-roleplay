import streamlit as st
from google import genai

st.set_page_config(page_title="Admission Counsellor Simulator", layout="centered")
st.title("🎓 Counsellor Roleplay Simulator")

persona = st.selectbox(
    "Choose Student Scenario:",
    [
        "Working Professional - Asking about Online MBA fees, EMI, and UGC approval",
        "Anxious Parent - Inquiring about B.Tech placement guarantee and faculty",
        "Budget-Conscious Student - Asking about BBA/BCA discounts and installment plans"
    ]
)

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

if prompt := st.chat_input("Speak/Type your response as counsellor..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    api_key = st.secrets.get("GEMINI_API_KEY", "")
    if api_key:
        client = genai.Client(api_key=api_key)
        system_instruction = f"You are roleplaying as a prospective student/parent: {persona}. Respond in 1-2 realistic, conversational sentences. Raise realistic doubts and objections."
        
        contents = []
        for m in st.session_state.messages:
            role = "user" if m["role"] == "user" else "model"
            contents.append(f"{role}: {m['content']}")
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"Instructions: {system_instruction}\n\nChat History:\n" + "\n".join(contents)
        )
        
        st.session_state.messages.append({"role": "assistant", "content": response.text})
        with st.chat_message("assistant"):
            st.write(response.text)

if st.sidebar.button("📊 End Call & Score Session"):
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    if api_key and st.session_state.messages:
        client = genai.Client(api_key=api_key)
        transcript = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
        eval_prompt = f"Audit this counsellor-student call. Score out of 10 on Rapport, Objection Handling, and Program Pitching. Give 3 actionable tips:\n\n{transcript}"
        
        eval_res = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=eval_prompt
        )
        st.sidebar.markdown("### 🏆 Performance Scorecard")
        st.sidebar.write(eval_res.text)
