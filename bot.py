import os
import urllib.request
import json
import time
import requests
from flask import Flask
from threading import Thread

# ==========================================
# ၁။ Render အတွက် Web Server အပိုင်း
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "Lix Bot is running!"

def run():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ==========================================
# ၂။ Environment Variables ယူခြင်း
# ==========================================
TG_API = os.environ.get("TG_API")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

user_last_msg_time = {}

# ==========================================
# ၃။ Telegram ဆိုင်ရာ Function များ
# ==========================================
def send_message(chat_id, text):
    url = TG_API + "sendMessage"
    data = json.dumps({"chat_id": chat_id, "text": text}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        response = urllib.request.urlopen(req, timeout=10)
        result = json.loads(response.read())
        return result['result']['message_id']
    except Exception as e:
        print("Send Error:", e)
        return None

def delete_message(chat_id, message_id):
    url = TG_API + "deleteMessage"
    data = json.dumps({"chat_id": chat_id, "message_id": message_id}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        pass

def send_typing(chat_id):
    url = TG_API + "sendChatAction"
    data = json.dumps({"chat_id": chat_id, "action": "typing"}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass

# ==========================================
# ၄။ AI ကို မေးခြင်း (Gemini API)
# ==========================================
def ask_ai(prompt):
    # သင့် API Key နဲ့ ကိုက်ညီမယ့် Model ကို သုံးထားပါတယ်
    model_name = "gemini-1.5-flash" 
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    # AI ရဲ့ ကိုယ်ပိုင် စရိုက် (Persona)
    instruction = (
        "မင်းနာမည်က Lix ပါ။ မင်းက ကူညီပေးတတ်တဲ့ AI သူငယ်ချင်းတစ်ယောက်ပါ။ "
        "အသုံးပြုသူက စာပို့လာတိုင်း မင်းရဲ့ အဖြေရဲ့ အစမှာ 'Lix ဘက်ကနေ ဘာများကူညီပေးရမလဲ' ဆိုတဲ့ စကားလေးကို "
        "အမြဲထည့်ပြီး ပြန်ဖြေပေးပါ။ ပြီးမှ သူမေးတာကို ဖြေပေးပါ။"
    )
    full_prompt = f"{instruction}\n\nUser: {prompt}"
    data = {"contents": [{"parts": [{"text": full_prompt}]}]}
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=60)
        result = response.json()
        
        # အောင်မြင်ရင် အဖြေကို ယူမယ်
        if 'candidates' in result:
            return result['candidates'][0]['content']['parts'][0]['text']
        else:
            # Error တက်ရင် အစစ်အမှန် Error ကို ပြမယ် (Debug လုပ်ဖို့)
            return f"DEBUG ERROR: {result}"
            
    except Exception as e:
        return f"DEBUG EXCEPTION: {str(e)}"

# ==========================================
# ၅။ Main Loop (Bot အလုပ်လုပ်တဲ့ နေရာ)
# ==========================================
keep_alive()
offset = 0
print("LIX GEMINI BOT RUNNING!")

while True:
    try:
        url = TG_API + "getUpdates?offset=" + str(offset) + "&timeout=10"
        response = urllib.request.urlopen(url, timeout=30)
        updates = json.loads(response.read())["result"]

        for update in updates:
            offset = update["update_id"] + 1
            msg = update.get("message", {})
            chat_id = msg.get("chat", {}).get("id")
            text = msg.get("text", "")

            if not chat_id or not text:
                continue

            if text == "/start":
                send_message(chat_id, "မင်္ဂလာပါ ❤️ Lixll Ai Bot မှ ကြိုဆိုပါတယ်။")
            else:
                # Rate Limit (၃ စက္ကန့်အတွင်း ၂ ခါ မပို့ရအောင်)
                current_time = time.time()
                if chat_id in user_last_msg_time:
                    if current_time - user_last_msg_time[chat_id] < 3:
                        send_message(chat_id, "⏳ ခဏစောင့်ပြီးမှ ပြန်မေးပေးပါဦး။")
                        continue
                
                user_last_msg_time[chat_id] = current_time

                try:
                    # "Typing..." ပြမယ်
                    send_typing(chat_id)
                    
                    # AI ကို မေးမယ်
                    answer = ask_ai(text)
                    
                    # အဖြေကို ပို့မယ်
                    send_message(chat_id, answer[:4000])
                    
                except Exception as e:
                    send_message(chat_id, "System Error: " + str(e)[:300])

    except Exception as e:
        print("Loop Error:", str(e))
        time.sleep(5)
