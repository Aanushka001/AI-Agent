# AI-Agent: Conversational Google Calendar Assistant

## Overview
Conversational AI agent to book appointments on Google Calendar using FastAPI (backend), LangGraph (agent), Streamlit (frontend), and OpenRouter (LLM).

## Features
- Conversational chat interface for booking and checking Google Calendar events
- Real-time Google Calendar integration using a service account
- Modern Streamlit frontend with status indicators and error feedback
- Deployable to Render (or similar platforms)

## Local Development

1. **Set up environment variables**
   - Create a `.env` file in `ai_agent/`:
     ```
     OPENROUTER_API_KEY=your_openrouter_key
     GOOGLE_CALENDAR_ID=your_calendar_id
     GOOGLE_CREDENTIALS_FILE=storied-program-427904-q8-e893e42250f5.json
     ```
2. **Install dependencies**
   ```sh
   pip install -r requirements.txt
   ```
3. **Run backend**
   ```sh
   uvicorn backend.main:app --reload --port 8000
   ```
4. **Run frontend**
   ```sh
   streamlit run frontend/app.py
   ```

## Deployment (Render)

1. **Push your code to GitHub**
2. **Create two Render web services:**
   - **Backend:**
     - Build Command: `pip install -r ai_agent/backend/requirements.txt`
     - Start Command: `uvicorn ai_agent.backend.main:app --host 0.0.0.0 --port 10000`
     - Set environment variables in the Render dashboard
   - **Frontend:**
     - Build Command: `pip install -r ai_agent/frontend/requirements.txt`
     - Start Command: `streamlit run ai_agent/frontend/app.py --server.port 10001 --server.address 0.0.0.0`
     - Update backend URL in frontend code to point to the Render backend URL
3. **Set all required environment variables in Render**
4. **Upload your Google service account JSON as a secret file if needed**

## Notes
- Ensure the Google service account has access to your calendar.
- Update CORS settings if restricting frontend origins.
- For production, secure all secrets and API keys. 