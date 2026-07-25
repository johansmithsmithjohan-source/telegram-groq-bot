"""
Telegram Bot with Groq AI - Deployed on Render.com
Uses Flask webhook (not polling) for instant responses & minimal resource usage
"""

import os
import json
import logging
from datetime import datetime
from collections import defaultdict
from flask import Flask, request, jsonify
import requests
from groq import Groq

# ============================================
# CONFIGURATION (from environment variables)
# ============================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")  # e.g. https://your-app.onrender.com

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Logging
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Grop client
groq_client = Groq(api_key=GROQ_API_KEY)

# In-memory conversation store (per user)
conversation_history = defaultdict(list)
MAX_HISTORY = 20

# Stats counters
stats = {
    "total_messages": 0,
    "unique_users": set(),
    "started_at": datetime.now().isoformat(),
}

# System prompt
SYSTEM_PROMPT = """You are Zaro Bot, a friendly and witty AI Telegram chatbot.

Guidelines:
- Reply in the SAME language the user writes (Hindi/English/Hinglish auto-detect)
- Keep responses concise and natural — like a friendly chat, not an essay
- Use emojis occasionally to feel warm 😊
- Help with: coding, math, general knowledge, jokes, facts, motivation, advice
- If asked who made you: "I was built by Smithjohan using Groq AI, deployed on Render!"

IMPORTANT: Keep replies under 800 characters unless user asks for something detailed."""


# ============================================
# FLASK APP
# ============================================
app = Flask(__name__)


# ============================================
# TELEGRAM API HELPERS
# ============================================
def send_message(chat_id, text, parse_mode=None):
    """Send message to Telegram chat"""
    try:
        payload = {"chat_id": chat_id, "text": text}
        if parse_mode:
            payload["parse_mode"] = parse_mode
        r = requests.post(f"{TELEGRAM_API}/sendMessage", json=payload, timeout=10)
        if r.status_code != 200 and parse_mode:
            # Retry without parse_mode if Markdown fails
            payload.pop("parse_mode", None)
            r = requests.post(f"{TELEGRAM_API}/sendMessage", json=payload, timeout=10)
        return r.json()
    except Exception as e:
        logger.error(f"send_message error: {e}")
        return None


def send_chat_action(chat_id, action="typing"):
    """Show 'typing...' indicator"""
    try:
        requests.post(f"{TELEGRAM_API}/sendChatAction",
                     json={"chat_id": chat_id, "action": action}, timeout=5)
    except:
        pass


# ============================================
# GROQ AI RESPONSE
# ============================================
def generate_ai_response(user_id, user_message, user_name):
    """Generate AI response with conversation memory"""
    try:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Add history
        history = conversation_history[user_id][-MAX_HISTORY:]
        messages.extend(history)

        # Add current message
        messages.append({"role": "user", "content": user_message})

        # Call Groq
        completion = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=500,
            top_p=0.95,
        )

        reply = completion.choices[0].message.content.strip()

        # Save to history
        conversation_history[user_id].append({"role": "user", "content": user_message})
        conversation_history[user_id].append({"role": "assistant", "content": reply})

        # Trim
        if len(conversation_history[user_id]) > MAX_HISTORY * 2:
            conversation_history[user_id] = conversation_history[user_id][-MAX_HISTORY * 2:]

        return reply
    except Exception as e:
        logger.error(f"Groq error: {e}")
        return f"🤔 Sorry {user_name}, my AI brain is a bit slow right now. Try again in a moment!"


# ============================================
# COMMAND HANDLERS
# ============================================
def handle_start(chat_id, user_name):
    text = (
        f"👋 *Welcome {user_name}!*\n\n"
        f"I'm your AI-powered Telegram bot 🤖\n"
        f"Powered by *Groq AI* (llama-3.3-70b) ⚡\n\n"
        f"✨ I can:\n"
        f"• Have real conversations with memory 🧠\n"
        f"• Answer any question\n"
        f"• Help with coding & math\n"
        f"• Tell jokes, facts, motivational quotes\n"
        f"• Chat in Hindi, English, Hinglish\n\n"
        f"Just send me any message! 😊\n\n"
        f"*Commands:*\n"
        f"/help - See all commands\n"
        f"/clear - Reset chat memory\n"
        f"/about - About this bot"
    )
    send_message(chat_id, text, parse_mode="Markdown")


def handle_help(chat_id):
    text = (
        "📋 *Available Commands:*\n\n"
        "/start - Welcome message\n"
        "/help - This menu\n"
        "/about - About the bot\n"
        "/clear - Reset conversation memory 🧹\n"
        "/stats - Bot statistics 📊\n"
        "/model - Current AI model\n\n"
        "🤖 *Just chat naturally!*\n"
        "I understand Hindi, English & Hinglish.\n"
        "I remember our last 20 messages 🧠"
    )
    send_message(chat_id, text, parse_mode="Markdown")