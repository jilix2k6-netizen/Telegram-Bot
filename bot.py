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

TG_API = os.environ.get("TG_API")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

user_last_msg_time = {}

# စာပို့ပြီး Message ID ကို ပြန်ယူတဲ့ Function (ဖျက်ဖို့အတွက်)
def send_and_get_id(chat_id, text):
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

# စာဖျက်တဲ့ Function
def delete_message(chat_id, message_id):
    url = TG_API + "deleteMessage"
    data = json.dumps({"chat_id": chat_id, "message_id": message_id}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print("Delete Error:", e)

# "Typing..." ပြတဲ့ Function (ပိုပြီး သဘာဝကျပါတယ်)
def send_typing(chat_id):
    url = TG_API + "sendChatAction"
    data = json.dumps({"chat_id": chat_id, "action": "typing"}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        pass # Error တက်ရင် ဘာမှမလုပ်ဘဲ ဆက်သွားမယ်

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
        elif 'error' in result:
            return "⚠️ AI နဲ့ ချိတ်ဆက်ရာမှာ အမှားအယွင်း ဖြစ်သွားပါတယ်။ ခဏနေမှ ပြန်ကြိုးစားပေးပါဦး။"
        else:
            return "⚠️ AI ဆီကနေ မမျှော်လင့်ထားတဲ့ အဖြေ ပြန်လာပါတယ်။"
            
    except Exception as e:
        print("Ask AI Error:", str(e))
        return "⚠️ AI နဲ့ ချိတ်ဆက်လို့ မရဖြစ်နေပါတယ်။ ခဏနေမှ ပြန်မေးပေးပါဦး။"

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
                send_and_get_id(chat_id, "မင်္ဂလာပါ ❤️ Lixll Ai Bot မှ ကြိုဆိုပါတယ်။")
            else:
                # Rate Limit စစ်ဆေးခြင်း
                current_time = time.time()
                if chat_id in user_last_msg_time:
                    time_diff = current_time - user_last_msg_time[chat_id]
                    if time_diff < 3:
                        send_and_get_id(chat_id, "⏳ ခဏစောင့်ပြီးမှ ပြန်မေးပေးပါဦး။ စာပို့တာ မြန်လွန်းနေပါတယ်။")
                        continue
                
                user_last_msg_time[chat_id] = current_time

                try:
                    # ၁။ "Typing..." လေး အရင်ပြမယ်
                    send_typing(chat_id)
                    
                    # ၂။ သင်တောင်းဆိုတဲ့အတိုင်း ⏳ စာလေး အရင်ပို့ပြီး ID ကို မှတ်ထားမယ်
                    wait_msg_id = send_and_get_id(chat_id, "⏳ ခဏစောင့်ပေးပါဦး၊ Lix စဉ်းစားနေပါတယ်...")
                    
                    # ၃။ AI ကို ခေါ်မယ်
                    answer = ask_ai(text)
                    
                    # ၄။ ⏳ စာလေးကို ဖျက်မယ်
                    if wait_msg_id:
                        delete_message(chat_id, wait_msg_id)
                        
                    # ၅။ အဖြေတကယ်ကို ပို့မယ်
                    send_and_get_id(chat_id, answer[:4000])
                    
                except Exception as e:
                    send_and_get_id(chat_id, "AI Error: " + str(e)[:300])

    except Exception as e:
        print("Error:", str(e))
        time.sleep(5)
