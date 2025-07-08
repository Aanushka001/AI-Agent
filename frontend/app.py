import streamlit as st
import requests
import dateparser
from datetime import datetime, timedelta
import os

st.set_page_config(page_title="AI-Agent: Google Calendar Assistant", page_icon="📅")
st.title("🤖 AI-Agent: Google Calendar Assistant")

# Backend status check
BACKEND_URL = os.environ.get("BACKEND_URL", "https://ai-agent-backend.onrender.com")
backend_status = "Unknown"
backend_color = "gray"
try:
    health_check = requests.post(
        f"{BACKEND_URL}/chat",
        json={"message": "ping"},
        timeout=5
    )
    if health_check.status_code == 200:
        backend_status = "Backend: Connected"
        backend_color = "green"
    else:
        backend_status = f"Backend: Error ({health_check.status_code})"
        backend_color = "red"
except Exception:
    backend_status = "Backend: Unreachable. Please check that the backend server is running and accessible."
    backend_color = "red"

st.markdown(f'<div style="color:{backend_color};font-weight:bold;">{backend_status}</div>', unsafe_allow_html=True)

# Sidebar configuration/settings
st.sidebar.header("Settings")
st.sidebar.info("Backend configuration is managed securely. No secrets are shown here.")

if "messages" not in st.session_state:
    st.session_state["messages"] = []

st.write("Chat with the AI agent to book appointments on your Google Calendar.")

# --- Custom CSS for modern chat UI ---
st.markdown('''
    <style>
    body {
        background: #18181b !important;
    }
    .main {
        background: #18181b !important;
    }
    .stApp {
        background: linear-gradient(135deg, #18181b 60%, #23272e 100%) !important;
    }
    .chat-container {
        max-width: 600px;
        margin: 0 auto;
        padding: 24px 0 0 0;
    }
    .chat-bubble {
        border-radius: 18px;
        margin-bottom: 12px;
        padding: 16px 20px;
        font-size: 1.15rem;
        box-shadow: 0 2px 16px 0 rgba(57,255,20,0.08);
        transition: box-shadow 0.2s;
    }
    .chat-bubble.user {
        background: linear-gradient(90deg, #39ff14 0%, #00e0ff 100%);
        color: #18181b;
        align-self: flex-end;
        box-shadow: 0 2px 16px 0 rgba(57,255,20,0.18);
        border-bottom-right-radius: 4px;
        display: flex;
        align-items: center;
    }
    .chat-bubble.agent {
        background: linear-gradient(90deg, #23272e 0%, #23272e 100%);
        color: #fff;
        align-self: flex-start;
        border-bottom-left-radius: 4px;
        display: flex;
        align-items: center;
    }
    .chat-bubble.agent.success {
        border-left: 5px solid #39ff14;
        box-shadow: 0 2px 16px 0 #39ff1444;
    }
    .chat-bubble.agent.error {
        border-left: 5px solid #ff073a;
        box-shadow: 0 2px 16px 0 #ff073a44;
    }
    .chat-bubble.agent.info {
        border-left: 5px solid #ffe600;
        box-shadow: 0 2px 16px 0 #ffe60044;
        color: #18181b;
        background: linear-gradient(90deg, #ffe600 0%, #fffbe6 100%);
    }
    .avatar {
        width: 36px;
        height: 36px;
        border-radius: 50%;
        margin-right: 12px;
        background: #23272e;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.3rem;
        font-weight: bold;
        color: #39ff14;
        box-shadow: 0 2px 8px 0 #23272e44;
    }
    .avatar.user {
        background: #39ff14;
        color: #18181b;
    }
    .avatar.agent {
        background: #23272e;
        color: #39ff14;
    }
    .stTextInput>div>div>input {
        background: #23272e !important;
        color: #fff !important;
        border-radius: 8px !important;
        font-size: 1.1rem !important;
        border: 1.5px solid #39ff14 !important;
        box-shadow: 0 2px 8px 0 #39ff1444 !important;
    }
    .stButton>button {
        background: linear-gradient(90deg, #39ff14 0%, #00e0ff 100%) !important;
        color: #18181b !important;
        font-weight: bold !important;
        border-radius: 8px !important;
        font-size: 1.1rem !important;
        box-shadow: 0 2px 8px 0 #39ff1444 !important;
        border: none !important;
        transition: box-shadow 0.2s;
    }
    .stButton>button:hover {
        box-shadow: 0 4px 16px 0 #39ff14cc !important;
    }
    </style>
''', unsafe_allow_html=True)

# --- Chat UI ---
st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
chat_container = st.container()
with chat_container:
    chat_html = ""
    for msg in st.session_state["messages"]:
        if msg["role"] == "user":
            chat_html += f"<div class='chat-bubble user'><span class='avatar user'>🧑</span><span>{msg['content']}</span></div>"
        else:
            # Neon highlights for Google Calendar responses
            if "Booked:" in msg["content"]:
                chat_html += f"<div class='chat-bubble agent success'><span class='avatar agent'>🤖</span><span>{msg['content']}</span></div>"
            elif "Error" in msg["content"]:
                chat_html += f"<div class='chat-bubble agent error'><span class='avatar agent'>🤖</span><span>{msg['content']}</span></div>"
            elif "Available from" in msg["content"] or "Busy during" in msg["content"]:
                chat_html += f"<div class='chat-bubble agent info'><span class='avatar agent'>🤖</span><span>{msg['content']}</span></div>"
            else:
                chat_html += f"<div class='chat-bubble agent'><span class='avatar agent'>🤖</span><span>{msg['content']}</span></div>"
    st.markdown(chat_html, unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# Input box at the bottom
with st.form(key="chat_form", clear_on_submit=True):
    user_input = st.text_input("Type your message:", key="user_input", placeholder="Type here and press Enter...")
    submitted = st.form_submit_button("Send")
    if submitted and user_input:
        st.session_state["messages"].append({"role": "user", "content": user_input})
        try:
            # Prepare chat history for context
            history = [msg for msg in st.session_state["messages"]]
            response = requests.post(
                f"{BACKEND_URL}/chat",
                json={"message": user_input, "history": history},
                timeout=30
            )
            if response.status_code == 401:
                agent_reply = "Authentication failed. Please check your API key."
            elif response.status_code != 200:
                agent_reply = f"Error: Backend returned status code {response.status_code}"
            else:
                agent_reply = response.json().get("response", "(No response)")
        except Exception as e:
            agent_reply = f"Error: Could not reach backend. {e}"
        st.session_state["messages"].append({"role": "agent", "content": agent_reply})
        st.rerun()

def route_to_tools(state: dict):
    output = state["output"].lower()
    # Try to extract all fields
    summary = extract_summary(output)
    time_info = dateparser.parse(output)
    duration = extract_duration(output)
    platform = extract_platform(output)
    timezone = extract_timezone(output)
    reminders = extract_reminders(output)

    # Only route if all required fields are present
    if summary and time_info and duration:
        start_time = time_info.isoformat()
        end_time = (time_info + timedelta(minutes=duration)).isoformat()
        return {
            "tool_name": "book_meeting",
            "tool_args": {
                "start_time": start_time,
                "end_time": end_time,
                "summary": summary,
                "platform": platform,
                "timezone": timezone,
                "reminders": reminders
            }
        }
    else:
        return {"output": state["output"]}

# --- Extraction helper functions ---
def extract_summary(text: str):
    # Simple extraction: look for 'with NAME' or fallback
    import re
    match = re.search(r"with ([\w\s]+)", text)
    return match.group(1).strip() if match else "Meeting"

def extract_duration(text: str):
    import re
    match = re.search(r"(\d+) ?(minutes|min|hours|hour)", text)
    if match:
        value = int(match.group(1))
        if 'hour' in match.group(2):
            return value * 60
        return value
    return 30  # default 30 minutes

def extract_platform(text: str):
    for platform in ["zoom", "teams", "google meet", "meet", "skype"]:
        if platform in text:
            return platform.title()
    return None

def extract_timezone(text: str):
    import re
    match = re.search(r"([A-Z]{2,4}) time", text)
    return match.group(1) if match else None

def extract_reminders(text: str):
    import re
    match = re.search(r"reminder[s]? (\d+) (minute|hour|day)s? before", text)
    if match:
        value = int(match.group(1))
        unit = match.group(2)
        return f"{value} {unit}(s) before"
    return None 