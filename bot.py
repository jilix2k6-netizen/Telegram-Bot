import os
import urllib.request
import json
import time
import requests
from flask import Flask
from threading import Thread

# Render က Port ရှာတွေ့အောင် Flask လေးနဲ့ တည်ဆောက်ခြင်း
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# သင့် Token နဲ့ Gemini Key (Render ရဲ့ Environment Variable ကနေ ယူပါမယ်)
TG_API = os.environ.get("TG_API")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def send(chat_id, text):
    url = TG_API + "sendMessage"
    data = json.dumps({"chat_id": chat_id, "text": text}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print("Send Error:", e)

def ask_ai(prompt):
    model_name = "gemini-3.6-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    instruction = "မင်းနာမည်က Lix ပါ။ မင်းက ကူညီပေးတတ်တဲ့ AI သူငယ်ချင်းတစ်ယောက်ပါ။ အသုံးပြုသူက စာပို့လာတိုင်း မင်းရဲ့ အဖြေရဲ့ အစမှာ 'Lix ဘက်ကနေ ဘာများကူညီပေးရမလဲ' ဆိုတဲ့ စကားလေးကို အမြဲထည့်ပြီး ပြန်ဖြေပေးပါ။ ပြီးမှ သူမေးတာကို ဖြေပေးပါ။"
    full_prompt = f"{instruction}\n\nUser: {prompt}"

    data = {"contents": [{"parts": [{"text": full_prompt}]}]}
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=60)
        result = response.json()
        
        if 'candidates' in result:
            return result['candidates'][0]['content']['parts'][0]['text']
        else:
            return f"API Error: {result}"
    except Exception as e:
        return f"AI Error: {str(e)}"

# Web Server ကို စတင်ခြင်း (ဒါက အရေးကြီးဆုံးပါ)
keep_alive()

offset = 0
print("GEMINI AI BOT RUNNING!")

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
                send(chat_id, "မင်္ဂလာပါ ❤️ Lixll Ai Bot မှ ကြိုဆိုပါတယ်။")
            else:
                try:
                    answer = ask_ai(text)
                    send(chat_id, answer[:4000])
                except Exception as e:
                    send(chat_id, "AI Error: " + str(e)[:300])

    except Exception as e:
        print("Error:", str(e))
        time.sleep(5)
