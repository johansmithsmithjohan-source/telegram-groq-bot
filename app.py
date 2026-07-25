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
from groq import Groq

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
groq_client = Groq(api_key=GROQ_API_KEY)
conversation_history = defaultdict(list)
MAX_HISTORY = 20
stats = {"total_messages":0,"unique_users":set(),"started_at":datetime.now().isoformat()}
SYSTEM_PROMPT = "You are Zaro Bot, a friendly AI Telegram chatbot. Reply in SAME language user writes (Hindi/English/Hinglish). Keep replies concise, natural, use emojis. Help with coding, math, knowledge, jokes, facts."
app = Flask(__name__)

def send_message(chat_id, text):
    try:
        return requests.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id":chat_id,"text":text}, timeout=10).json()
    except: return None

def send_chat_action(chat_id):
    try:
        requests.post(f"{TELEGRAM_API}/sendChatAction", json={"chat_id":chat_id,"action":"typing"}, timeout=5)
    except: pass

def groq_reply(user_id, user_msg, user_name):
    try:
        msgs = [{"role":"system","content":SYSTEM_PROMPT}]
        msgs.extend(conversation_history[user_id][-MAX_HISTORY:])
        msgs.append({"role":"user","content":user_msg})
        comp = groq_client.chat.completions.create(model=GROQ_MODEL, messages=msgs, temperature=0.7, max_tokens=500)
        reply = comp.choices[0].message.content.strip()
        conversation_history[user_id].append({"role":"user","content":user_msg})
        conversation_history[user_id].append({"role":"assistant","content":reply})
        if len(conversation_history[user_id]) > MAX_HISTORY*2:
            conversation_history[user_id]=conversation_history[user_id][-MAX_HISTORY:2]
        return reply
    except:
        return f"Sorry {user_name}, AI unavailable right now!"

def handle_cmd(chat_id,user_name,user_id,cmd):
    if cmd=="/start":
        msg=f"Welcome {user_name}! \n\nIm an AI bot powered by Groq (! Real AI chat with memory! \n/help for commands."
    elif cmd=="/help":
        msg="/start - Welcome~n/help - This menu\n/about - About\n/clear - Reset memory\n/stats - Bot stats\n/model - AI model"
    elif cmd=="/about":
        msg=f"Groq QI Bot\nModel: {GROQ_MODEL}\nPowered by Groq\nHosted on Render.com 24/7"
    elif cmd=="/clear":
        conversation_history.pop(user_id,None); msg="Memory cleared!"
    elif cmd=="/stats":
        t=datetime.now()-datetime.fromisoformat(stats["started_at"])
        msg=f"Msgs: {stats['total_messages']} | Users: {len(stats['unique_users'])} | Uptime: {int(t.total_seconds()//3600)}h {int((t.total_seconds()%3600)//60)}m | LIVE"
    elif cmd=="/model":
        msg=f"Model: {GROQ_MODEL}\nGroq w {1}.version(groq) | Memory: {MAX_HISTORY} msgs\n/clear to reset"
    else: msg=f"Unknown: {cmd}. /help"
    send_message(chat_id,msg)

def process_update(update):
    try:
        msg=update.get("message") or update.get("edited_message")
        if not msg: return
        chat_id=msg["chat"]["id"]; user_id=msg["from"]["id"]; user_name=msg["from"].get("first_name","User"); text=msg.get("text","")
        stats["total_messages"]+=1; stats["unique_users"].add(user_id)
        if not text: send_message(chat_id,"Sorry, I only handle text messages"); return
        if text.startswith("/"): handle_cmd(chat_id,user_name,user_id,text.split()[0].lower().split("@")[0]); return
        send_chat_action(chat_id)
        send_message(chat_id,groq_reply(user_id,text,user_name))
    except: logger.error("err",exc_info=True)

@app.route("/")
def home(): t = datetime.now()-datetime.fromisoformat(stats["started_at"]); return jsonify({"status":"LIVE","msgs":stats["total_messages"],"users":len(stats["unique_users"]),"uptime":int(t.total_seconds())})

@app.route("/health")
def health(): return jsonify({"status":"ok"}),200

@app.route("/webhook",methods=["POST"])
def webhook():
    try: process_update(request.get_json(force=True)); return jsonify({"ok":True}),200
    except: return jsonify({"ok": False}),500

if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)),debug=False)
