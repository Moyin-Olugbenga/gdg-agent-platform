import os
import httpx
import asyncio
import uvicorn
from fastapi import FastAPI, Request, BackgroundTasks
from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

load_dotenv()

from legal_agent.agent import root_agent as legal_agent
from sdr_agent.agent import root_agent as sdr_agent

app = FastAPI(title="AI Agent Platform", version="1.0.0")

legal_session_service = InMemorySessionService()
sdr_session_service = InMemorySessionService()


legal_runner = Runner(
    agent=legal_agent,
    app_name="legal_aid_agent",
    session_service=legal_session_service,
)

sdr_runner = Runner(
    agent=sdr_agent,
    app_name="sdr_agent",
    session_service=sdr_session_service,
)

async def run_agent(runner, session_service, user_id: str, session_id: str, message: str) -> str:
    """Run an agent and return the final response as a string."""
    existing = await session_service.get_session(
        app_name=runner.app_name,
        user_id=user_id,
        session_id=session_id
    )
    if not existing:
        await session_service.create_session(
            app_name=runner.app_name,
            user_id=user_id,
            session_id=session_id
        )

    content = types.Content(
        role="user",
        parts=[types.Part(text=message)]
    )

    final_response = ""
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=content
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_response = event.content.parts[0].text

    return final_response or "I'm sorry, I couldn't generate a response."

# ── Telegram Background Processing ──────────────────────────────────────────
async def process_telegram_update(text: str, chat_id: str, user_id: str):
    """Processes the AI logic and sends the message back to Telegram."""
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not telegram_token:
        print("Error: TELEGRAM_BOT_TOKEN not found in environment.")
        return

    try:
        # Route logic
        if text.startswith("/legal") or "contract" in text.lower() or "sign" in text.lower():
            clean_message = text.replace("/legal", "").strip()
            response = await run_agent(
                legal_runner, legal_session_service, user_id, chat_id, 
                clean_message or "Hello, I need legal help."
            )
            agent_name = "⚖️ Legal Aid Agent"
        elif text.startswith("/sdr") or "leads" in text.lower() or "sales" in text.lower():
            clean_message = text.replace("/sdr", "").strip()
            response = await run_agent(
                sdr_runner, sdr_session_service, user_id, chat_id, 
                clean_message or "Hello, I need sales help."
            )
            agent_name = "💼 SDR Agent"
        elif text == "/start":
            response = (
                "👋 Welcome to the AI Agent Platform!\n\n"
                "⚖️ *Legal Aid Agent* — Use /legal\n"
                "💼 *SDR Agent* — Use /sdr"
            )
            agent_name = "Platform"
        else:
            response = "Please use /legal or /sdr to start."
            agent_name = "Platform"

        # Send response to Telegram
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://api.telegram.org/bot{telegram_token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": f"*{agent_name}*\n\n{response}",
                    "parse_mode": "Markdown"
                },
                timeout=30.0
            )
    except Exception as e:
        print(f"Error processing Telegram update: {e}")

# ── Endpoints ────────────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {"status": "running", "agents": ["legal_aid_agent", "sdr_agent"]}

@app.post("/telegram")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    """Entry point for Telegram. Responds immediately to avoid 500 errors."""
    try:
        body = await request.json()
        message = body.get("message", {})
        text = message.get("text", "")
        chat_id = message.get("chat", {}).get("id")
        user_id = str(message.get("from", {}).get("id", "default"))

        if text and chat_id:
            # Move the heavy lifting to the background
            background_tasks.add_task(process_telegram_update, text, str(chat_id), user_id)
            
        return {"ok": True}
    except Exception as e:
        print(f"Webhook Error: {e}")
        return {"ok": True} # Always return 200 to Telegram

# ── Runner ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Render provides the port via the PORT environment variable
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)