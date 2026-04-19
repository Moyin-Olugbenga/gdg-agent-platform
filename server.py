import os
import asyncio
from fastapi import FastAPI, Request
from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
import uvicorn

load_dotenv()

# ── Import both agents ────────────────────────────────────────────────────────
from legal_agent.agent import root_agent as legal_agent
from sdr_agent.agent import root_agent as sdr_agent

app = FastAPI(title="AI Agent Platform", version="1.0.0")

# ── Session services (one per agent) ─────────────────────────────────────────
legal_session_service = InMemorySessionService()
sdr_session_service = InMemorySessionService()

# ── Runners ───────────────────────────────────────────────────────────────────
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
    # Create session if it doesn't exist
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

    return final_response


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {"status": "running", "agents": ["legal_aid_agent", "sdr_agent"]}


# ── Legal Agent endpoint ──────────────────────────────────────────────────────
@app.post("/legal")
async def legal_endpoint(request: Request):
    body = await request.json()
    user_id = body.get("user_id", "default_user")
    session_id = body.get("session_id", "default_session")
    message = body.get("message", "")

    if not message:
        return {"error": "message is required"}

    response = await run_agent(
        legal_runner,
        legal_session_service,
        user_id,
        session_id,
        message
    )
    return {"agent": "legal_aid_agent", "response": response}


# ── SDR Agent endpoint ────────────────────────────────────────────────────────
@app.post("/sdr")
async def sdr_endpoint(request: Request):
    body = await request.json()
    user_id = body.get("user_id", "default_user")
    session_id = body.get("session_id", "default_session")
    message = body.get("message", "")

    if not message:
        return {"error": "message is required"}

    response = await run_agent(
        sdr_runner,
        sdr_session_service,
        user_id,
        session_id,
        message
    )
    return {"agent": "sdr_agent", "response": response}


# ── Telegram Webhook ──────────────────────────────────────────────────────────
@app.post("/telegram")
async def telegram_webhook(request: Request):
    body = await request.json()

    message = body.get("message", {})
    text = message.get("text", "")
    chat_id = str(message.get("chat", {}).get("id", ""))
    user_id = str(message.get("from", {}).get("id", "default"))

    if not text or not chat_id:
        return {"ok": True}

    # Route based on command or keyword
    if text.startswith("/legal") or "contract" in text.lower() or "sign" in text.lower():
        clean_message = text.replace("/legal", "").strip()
        response = await run_agent(
            legal_runner,
            legal_session_service,
            user_id,
            chat_id,
            clean_message or "Hello, I need legal help."
        )
        agent_name = "⚖️ Legal Aid Agent"
    elif text.startswith("/sdr") or "leads" in text.lower() or "sales" in text.lower():
        clean_message = text.replace("/sdr", "").strip()
        response = await run_agent(
            sdr_runner,
            sdr_session_service,
            user_id,
            chat_id,
            clean_message or "Hello, I need sales help."
        )
        agent_name = "💼 SDR Agent"
    elif text == "/start":
        response = (
            "👋 Welcome to the AI Agent Platform!\n\n"
            "I have two agents ready to help you:\n\n"
            "⚖️ *Legal Aid Agent* — Analyse contracts and legal documents\n"
            "Use /legal followed by your question\n\n"
            "💼 *SDR Agent* — Research leads and write sales emails\n"
            "Use /sdr followed by your product and leads info\n\n"
            "What do you need help with today?"
        )
        agent_name = "Platform"
    else:
        response = (
            "Please use:\n"
            "/legal — for contract analysis\n"
            "/sdr — for sales outreach help"
        )
        agent_name = "Platform"

    # Send reply to Telegram
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if telegram_token:
        import httpx
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://api.telegram.org/bot{telegram_token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": f"{agent_name}\n\n{response}",
                    "parse_mode": "Markdown"
                }
            )

    return {"ok": True}


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8080, reload=False)