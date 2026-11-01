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

# Environment Variables ကနေ ယူခြင်း
TG_API = os.environ.get("TG_API")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Rate Limit အတွက် အသုံးပြုသူရဲ့ နောက်ဆုံးစာပို့ချိန်ကို မှတ်ထားမယ့် နေရာ
user_last_msg_time = {}

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
        
        # API Error တွေကို စနစ်တကျ ဖမ်းယူခြင်း
        if 'candidates' in result:
            return result['candidates'][0]['content']['parts'][0]['text']
        elif 'error' in result:
            error_msg = result['error'].get('message', '')
            if 'quota' in error_msg.lower() or '429' in str(result):
                return "⚠️ တစ်နေ့တာ အသုံးပြုခွင့် ပမာဏ ပြည့်သွားပါပြီ။ ခဏနေမှ ပြန်မေးပေးပါဦး။"
            elif 'safety' in error_msg.lower():
                return "⚠️ ဒီစာသားလေးကို AI က ဖြေဖို့ မသင့်လျော်ဘူးလို့ သတ်မှတ်ထားလို့ မဖြေပေးနိုင်ပါဘူး။ တခြားစာသားနဲ့ မေးကြည့်ပါဦး။"
            else:
                return "⚠️ AI နဲ့ ချိတ်ဆက်ရာမှာ အမှားအယွင်း ဖြစ်သွားပါတယ်။ ခဏနေမှ ပြန်ကြိုးစားပေးပါဦး။"
        else:
            return "⚠️ AI ဆီကနေ မမျှော်လင့်ထားတဲ့ အဖြေ ပြန်လာပါတယ်။ ခဏနေမှ ပြန်မေးပေးပါဦး။"
            
    except Exception as e:
        print("Ask AI Error:", str(e))
        return "⚠️ AI နဲ့ ချိတ်ဆက်လို့ မရဖြစ်နေပါတယ်။ ခဏနေမှ ပြန်မေးပေးပါဦး။"

# Web Server ကို စတင်ခြင်း
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
                # Rate Limit စစ်ဆေးခြင်း (၃ စက္ကန့်အတွင်း စာနှစ်ခုပို့ရင် ပိတ်မယ်)
                current_time = time.time()
                if chat_id in user_last_msg_time:
                    time_diff = current_time - user_last_msg_time[chat_id]
                    if time_diff < 3:
                        send(chat_id, "⏳ ခဏစောင့်ပြီးမှ ပြန်မေးပေးပါဦး။ စာပို့တာ မြန်လွန်းနေပါတယ်။")
                        continue
                
                # အချိန်ကို Update လုပ်မယ်
                user_last_msg_time[chat_id] = current_time

                try:
                    answer = ask_ai(text)
                    send(chat_id, answer[:4000])
                except Exception as e:
                    send(chat_id, "AI Error: " + str(e)[:300])

    except Exception as e:
        print("Error:", str(e))
        time.sleep(5)
