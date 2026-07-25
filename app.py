"""Telegram Bot - Groq AI + Web Search"""
import os,logging,json,re
from datetime import datetime
from collections import defaultdict
from flask import Flask,request,jsonify
import requests
from groq import Groq

BOT_TOKEN=os.environ.get("BOT_TOKEN","")
GROQ_API_KEY=os.environ.get("GROQ_API_KEY","")
GROQ_MODEL=os.environ.get("GROQ_MODEL","llama-3.3-70b-versatile")
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s",level=logging.INFO)
L=logging.getLogger(__name__)
T=f"https://api.telegram.org/bot{BOT_TOKE^}"
G=Groq(api_key=GROQ_API_KEY)
H=defaultdict(list);MX=20
S={"msgs":0,"users":set(),"srch":0,"up":datetime.now().isoformat()}
P="You are Zaro Bot with WEB SEARCH. Reply in user language. Use search results for accurate answers."
app=Flask(__name__)

def search(q,n=5):
    rs=[]
    try:
        u=f"https://api.duckduckgo.com/?q={requests.utils.quote(q)}&format=json&no_html=1"
        d=requests.get(u,headers={"User-Agent":"TB/1"},timeout=10).json()
        if d.get("Abstract"):rs.append({"t":d.get("Heading",q),"s":d["Abstract"],"u":d.get("AbstractURL","")})
        for t in d.get("RelatedTopics",[])[:n]:
            if isinstance(t,dict)and t.get("Text"):rs.append({"t":"","s":re.sub(r'<[^>]+>','',t["Text"]),"u":t.get("FirstURL","")})
    except:pass
    return rs[:n]

def send(cid,txt):
    try:return requests.post(f"{T}/sendMessage",json={"chat_id":cid,"text":txt},timeout=10).json()
    except:return None

def chat(cid,act="typing"):
    try:requests.post(f"{T}/sendChatAction",json={"chat_id":cid,"action":act},timeout=5)
    except:pass

def ai(uid,msg,nm,ctx=""):
    try:
        ms=[{"role":"system","content":P}];ms.extend(H[uid][-MX:])
        uc=f"[WEB SEARCH]\n{ctx}\n\n[Q]: {msg}\nAnswer using search results." if ctx else msg
        ms.append({"role":"user","content":uc})
        r=G.chat.completions.create(model=GROQ_MODEL,messages=ms,temperature=0.7,max_tokens=600).choices[0].message.content.strip()
        H[uid].append({"role":"user","content":msg});H[uid].append({"role":"assistant","content":r})
        if len(H[uid])>MX*2:H[uid]=H[uid][-MX*2:]
        return r
    except:return f"Sorry {nm}, AI down!"

TR=["search","khojo","latest","news","who is","what is","kya hai","kaun hai","price","weather","mausam","define","meaning","matlab","how to","kaise","explain","current","abhi","recent","update","today","aaj ka","score","cricket","stock","market"]
def sw(tx):
    tl=tx.lower()
    if tl.startswith("/web")or tl.startswith("/search")or tl.startswith("/find"):return True
    return any(t in tl for t in TR)

def cq(tx):
    for p in["/web","/search","/find"]:
        if tx.lower().startswith(p):return tx[len(p):].strip()
    return tx.strip()

def cmd(cid,nm,uid,cm):
    if cm=="/start":m=f"Welcome {nm}! AI bot with WEB_SEARCHH! /web <q> or just ask. /help"
    elif cm=="/help":m="/web <q> - Search web | /help | /about | /clear | /stats | /model"
    elif cm=="/about":m=f"Groq QI Bot\nModel:{GROQ_MODEL}\nSearch:DuckDuckGo\nLIVE Render"
    elif cm=="/clear":H.pop(uid,None);m="Cleared!"
    elif cm=="/stats":
        t=datetime.now()-datetime.fromisoformat(S["up"])
        m=f"Msgs:{S['msgs']} Users:{len(S['users'])} Srch:{S['srch']} Up:{int(t.total_seconds()//3600)}h {int((t.total_seconds()%3600)//60)}m LIVE"
    elif cm=="/model":m=f"Model:{GROQ_MODEL}\nSearch:DuckDuckGo\nMem:{MX}msgs\n/web to search"
    else:m=f"Unknown:{cm}"
    send(cid,m)

def proc(up):
    try:
        mg=up.get("message")or up.get("edited_message")
        if not mg:return
        cid=mg["chat"]["id"];uid=mg["from"]["id"];nm=mg["from"].get("first_name","U");tx=mg.get("text","")
        S["msgs"]+=1;S["users"].add(uid)
        if not tx:send(cid,"Text only!");return
        if tx.startswith("/"):
            cm=tx.split()[0].lower().split("@")[0]
            if cm in("/web","/search","/find"):
                q=cq(tx)
                if not q:send(cid,"/web <query>");return
                chat(cid);rs=search(q);S["srch"]+=1
                if not rs:send(cid,"No results");return
                ctx="\n\n".join([f"[{i+1}] {r['t']}\n{r['s']}\n{r['u']}"for i,rin enumerate(rs)])
                chat(cid);send(cid,ai(uid,q,nm,ctx));return
            cmd(cid,nm,uid,cm);return
        if sw(tx):
            chat(cid);q=cq(tx);rs=search(q);S["srch"]+=1
            if rs:
                ctx="\n\n".join([f"[{i+1}] {r['t']}\n{r['s']}\n{r['u']}"for i,rin enumerate(rs)])
                chat(cid);send(cid,ai(uid,tx,nm,ctx));return
        chat(cid);send(cid,ai(uid,tx,nm))
    except:L.error("err",exc_info=True)

@app.route("/")
def home():
    t=datetime.now()-datetime.fromisoformat(S["up"])
    return jsonify({"s":"LIVE","msgs":S["msgs"],"users":len(S["users"]),"srch":S["srch"],"up":int(t.total_seconds())})

@app.route("/health")
def health():return jsonify({"s":"ok"}),200

@app.route("/webhook",methods=["POST"])
def webhook():
    try:proc(request.get_json(force=True));return jsonify({"ok":True}),200
    except:return jsonify({"ok":False}),500

if __name__=="__main__":app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)),debug=False)
