import os
import urllib.request
import urllib.parse
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
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print("Send Error:", e)

def send_photo(chat_id, photo_url, caption=""):
    url = TG_API + "sendPhoto"
    data = json.dumps({"chat_id": chat_id, "photo": photo_url, "caption": caption}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=15)
    except Exception as e:
        print("Photo Error:", e)
        send_message(chat_id, "ပုံပို့လို့ မရဖြစ်သွားပါတယ်။ ခဏနေမှ ပြန်စမ်းပါဦး။")

def send_audio(chat_id, audio_url, title, performer):
    url = TG_API + "sendAudio"
    data = json.dumps({
        "chat_id": chat_id, 
        "audio": audio_url, 
        "title": title, 
        "performer": performer
    }).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=15)
    except Exception as e:
        print("Audio Error:", e)
        send_message(chat_id, "သီချင်းပို့လို့ မရဖြစ်သွားပါတယ်။ ခဏနေမှ ပြန်စမ်းပါဦး။")

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
    model_name = "gemini-2.0-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    instruction = (
        "မင်းနာမည်က Lix ပါ။ မင်းက ကူညီပေးတတ်တဲ့ AI သူငယ်ချင်းတစ်ယောက်ပါ။ "
        "အသုံးပြုသူက စာပို့လာတိုင်း မင်းရဲ့ အဖြေရဲ့ အစမှာ 'Lix ဘက်ကနေ ဘာများကူညီပေးရမလဲ' ဆိုတဲ့ စကားလေးကို အမြဲထည့်ပြီး ပြန်ဖြေပေးပါ။ "
        "မင်းက အသံနဲ့ စကားပြောလို့ မရသေးပါဘူး။ စာသားနဲ့ပဲ ကူညီပေးနိုင်တယ်ဆိုတာကို သိထားပါ။"
    )
    full_prompt = f"{instruction}\n\nUser: {prompt}"
    data = {"contents": [{"parts": [{"text": full_prompt}]}]}
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=120)
        result = response.json()
        if 'candidates' in result:
            return result['candidates'][0]['content']['parts'][0]['text']
        else:
            return "⚠️ AI နဲ့ ချိတ်ဆက်ရာမှာ အမှားအယွင်း ဖြစ်သွားပါတယ်။ ခဏနေမှ ပြန်ကြိုးစားပေးပါဦး။"
    except Exception as e:
        print("Ask AI Error:", str(e))
        return "⚠️ AI ဖြေဖို့ အချိန်ကြာနေပါတယ်။ ခဏနေမှ ပြန်မေးပေးပါဦး။"

# ==========================================
# ၅။ iTunes ကနေ သီချင်းရှာတဲ့ Function
# ==========================================
def search_song(song_name):
    query = urllib.parse.quote(song_name)
    url = f"https://itunes.apple.com/search?term={query}&limit=1&media=music"
    try:
        response = requests.get(url, timeout=10)
        result = response.json()
        if result['resultCount'] > 0:
            track = result['results'][0]
            return {
                "preview_url": track.get("previewUrl"),
                "title": track.get("trackName"),
                "artist": track.get("artistName")
            }
    except Exception as e:
        print("Song Search Error:", e)
    return None

# ==========================================
# ၆။ Main Loop (Bot အလုပ်လုပ်တဲ့ နေရာ)
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

            # Rate Limit (၃ စက္ကန့်အတွင်း ၂ ခါ မပို့ရအောင်)
            current_time = time.time()
            if chat_id in user_last_msg_time:
                if current_time - user_last_msg_time[chat_id] < 3:
                    send_message(chat_id, "⏳ ခဏစောင့်ပြီးမှ ပြန်မေးပေးပါဦး။")
                    continue
            user_last_msg_time[chat_id] = current_time

            # Start Command
            if text == "/start":
                send_message(chat_id, "မင်္ဂလာပါ ❤️ Lixll Ai Bot မှ ကြိုဆိုပါတယ်။\n\nကျွန်တော့်ကို အောက်ပါအတိုင်း အသုံးပြုနိုင်ပါတယ် -\n\n💬 စကားပြောရန် - 'မင်္ဂလာပါ' လို့ ရိုက်ပါ\n🎵 သီချင်းရှာရန် - 'သီချင်း Shape of You' လို့ ရိုက်ပါ\n🎨 ပုံဆွဲရန် - 'ပုံဆွဲပေးပါ ကြောင်လေးတစ်ကောင်' လို့ ရိုက်ပါ")
                continue

            # ပုံဆွဲခိုင်းတဲ့အခါ (Flux AI)
            if "ပုံဆွဲ" in text.lower() or "draw" in text.lower() or "image" in text.lower():
                send_typing(chat_id)
                prompt = text.replace("ပုံဆွဲပေးပါ", "").replace("ပုံဆွဲ", "").replace("draw", "").replace("image", "").strip()
                
                if not prompt:
                    send_message(chat_id, "ဘယ်လိုပုံမျိုး ဆွဲပေးရမလဲဆိုတာ ပြောပြပါဦး။ (ဥပမာ - ပုံဆွဲပေးပါ နေဝင်ချိန် ကမ်းခြေ)")
                    continue
                
                encoded_prompt = urllib.parse.quote(prompt)
                image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&model=flux&nologo=true&enhance=true"
                send_photo(chat_id, image_url, f"🎨 Lix ရဲ့ Flux AI နဲ့ ဆွဲပေးထားတဲ့ ပုံလေးပါ - \n'{prompt}'")
                continue

            # သီချင်းရှာခိုင်းတဲ့အခါ (iTunes Audio)
            if "သီချင်း" in text.lower() or "song" in text.lower() or "music" in text.lower():
                send_typing(chat_id)
                song_query = text.replace("သီချင်း", "").replace("ရှာပေးပါ", "").replace("song", "").replace("music", "").strip()
                
                if not song_query:
                    send_message(chat_id, "ဘယ်သီချင်းမျိုး ရှာပေးရမလဲဆိုတာ ပြောပြပါဦး။ (ဥပမာ - သီချင်း Believer)")
                    continue

                song_data = search_song(song_query)
                
                if song_data and song_data['preview_url']:
                    send_audio(chat_id, song_data['preview_url'], song_data['title'], song_data['artist'])
                    send_message(chat_id, "🎵 အပေါ်က သီချင်းလေးက ၃၀ စက္ကန့်စာ နားဆင်နိုင်တဲ့ အပိုင်းလေးပါ။")
                else:
                    send_message(chat_id, f"'{song_query}' ဆိုတဲ့ သီချင်းကို ရှာမတွေ့ပါဘူး။ နာမည် ပြန်စစ်ပြီး ရှာကြည့်ပါဦး။")
                continue

            # ကျန်တဲ့ ရိုးရိုးစာသားတွေအတွက် AI ကို မေးမယ်
            try:
                send_typing(chat_id)
                answer = ask_ai(text)
                send_message(chat_id, answer[:4000])
            except Exception as e:
                send_message(chat_id, "System Error: " + str(e)[:300])

    except Exception as e:
        print("Loop Error:", str(e))
        time.sleep(5)
