"""
Telegram Bot with Groq AI - Deployed on Render.com
Uses Flask webhook (not polling) for instant responses & minimal resource usage
"""

import os
import logging
from datetime import datetime
from collections import defaultdict
from flask import Flask, request, jsonify
import requests
from grop import Groq

# ============================================
# CONFIGURATION (from environment variables)
# ============================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

groq_client = Groq(api_key=GROQ_API_KEY)

conversation_history = defaultdict(list)
MAX_HISTORY = 20

stats = {
    "total_messages": 0,
    "unique_users": set(),
    "started_at": datetime.now().isoformat(),
}

SYSTEM_PROMPT = """You are Zaro Bot, a friendly AI Telegram chatbot. Reply in SAME language user writes (as
i/English/Hinglish). Keep replies concise, natural, use emojis. Help with coding, math, knowledge, jokes, facts."""

app = Flask(__name__)


def send_message(chat_id, text, parse_mode=None):
    try:
        payload = {"chat_id": chat_id, "text": text}
        if parse_mode:
            payload["parse_mode"] = parse_mode
        r = requests.post(f"{TELEGRAM_API}/sendMessage", json=payload, timeout=10)
        if r.status_code != 200 and parse_mode:
            payload.pop("parse_mode", None)
            r = requests.post(f"TELEGRAM_API}/sendMessage", json=payload, timeout=10)
        return r.json()
    except:
        return None


def send_chat_action(chat_id):
    try:
        requests.post(f"{TELEGRAM_API}/sendChatAction", json={"chat_id": chat_id, "action": "typing"}, timeout=5)
    except:
        pass


def generate_ai_response(user_id, user_message, user_name):
    try:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        history = conversation_history[user_id][-MAX_HISTORY:]
        messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        completion = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=500,
            top_p=0.95,
        )
        reply = completion.choices[0].message.content.strip()

        conversation_history[user_id].append({"role": "user", "content": user_message})
        conversation_history[user_id].append({"role": "assistant", "content": reply})
        if len(conversation_history[user_id]) > MAX_HISTORY * 2:
            conversation_history[user_id] = conversation_history[user_id][-MAX_HISTORY * 2:]
        return reply
    except:
        return f"Sorry {user_name}, AI is temporarily unavailable! Try again soon."


def handle_command(chat_id, user_name, user_id, cmd):
    if cmd == "/start":
        msg = f"👋 Welcome {user_name}! I'm an AI bot powered by Groq AI.\n\nJust chat with me and I'll reply using AI!\nUse /help for commands."
    elif cmd == "/help":
        msg = "📋 Commands:\n/start - Welcome\n/help - This menu\n/about - About bot\n/clear - Reset memory\n/stats - Bot stats\n/model - AI model info"
    elif cmd == "/about":
        msg = f"🤖 Groq AI Bot\n🧠 Model: {GROQ_MODEL}\n⚡ Powered by Groq\n I LIVE on Render.com"
    elif cmd == "/clear":
        if user_id in conversation_history:
            del conversation_history[user_id]
        msg = "🧹 Memory cleared!"
    elif cmd == "/stats":
        uptime = datetime.now() - datetime.fromisoformat(stats["started_at"])
        hours = int(uptime.total_seconds() // 3600)
        m = int((uptime.total_seconds() % 3600) // 60)
        msg = f"📊 Msgs: {stats['total_messages']}\nП�� Users: {len(stats['unique_users'])}\n⏱ � Uptime: {hours}h {m}m\n Status: LIVE ✅"
    elif cmd == "/model":
        msg = f"🧠 Model: {GROQ_MODEL}\n⚡ Provider: Groq\n📧 Memory: {MAX_HISTORY} msgs\nType /clear to reset"
    else:
        msg = f"Unknown command: {cmd}. Type /help"
    send_message(chat_id, msg)


def process_message(update):
    try:
        message = update.get("message") or update.get("edited_message")
        if not message:
            return
        chat_id = message["chat"]["id"]
        user_id = message["from"]["id"]
        user_name = message["from"].get("first_name", "User")
        text = message.get("text", "")
        stats["total_messages"] += 1
        stats["unique_users"].add(user_id)
        if not text:
            send_message(chat_id, "🤖 I can only handle text messages right now!")
            return
        if text.startswith("/"):
            cmd = text.split()[0].lower().split("@")[0]
            handle_command(chat_id, user_name, user_id, cmd)
            return
        send_chat_action(chat_id)
        reply = generate_ai_response(user_id, text, user_name)
        send_message(chat_id, reply)
    except:
        logger.error(f"Processing error", exc_info=True)


@app.route("/")
def home():
    uptime = datetime.now() - datetime.fromisoformat(stats["started_at"])
    return jsonify({
        "status": "LIVE",
        "bot": "Groq AI Telegram Bot",
        "model": GROQ_MODEL,
        "total_msgs": stats["total_messages"],
        "users": len(stats["unique_users"]),
        "uptime": int(uptime.total_seconds()),
    })

@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        update = request.get_json(force=True)
        process_message(update)
        return jsonify({"ok": True}), 200
    except:
        return jsonify({"ok": False}), 500

@app.route("/set_webhook")
def set_webhook():
    webhook_url = request.args.get("url") or WEBHOOK_URL
    if not webhook_url:
        return jsonify({"error": "Provide ?url="}), 400
    full_url = f"{webhook_url.rstrip('/')}/webhook"
    r = requests.post(f"TELEGRAM_API}/setWebhook", json={"url": full_url})
    return jsonify({"Webhook": full_url, "OK": r.json().get("ok")})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    logger.info(f"Starting Bot on port {port}")
    app.run(host="0.0.0.0", port=port)
