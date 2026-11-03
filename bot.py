import os
import time
import json
import requests
import urllib.parse

from flask import Flask
from threading import Thread

# ==========================================
# 1. LIX AI WEB SERVER
# ==========================================

app = Flask(__name__)

@app.route("/")
def home():
    return "❤️ Lix AI V3.3 is Running Smoothly!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    Thread(target=run, daemon=True).start()

# ==========================================
# 2. API CONFIGURATION (Environment Variables)
# ==========================================

# Render Dashboard ထဲရှိ Environment Variables များမှ အလိုအလျောက် ယူပါမည်
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}/" if BOT_TOKEN else ""

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
POLLINATIONS_API_KEY = os.environ.get("POLLINATIONS_API_KEY", "")

# Gemini Model ကို latest / flash သို့ ပြောင်းထားပါသည်
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
IMAGE_MODEL = "flux"

user_last_msg_time = {}

# ==========================================
# 3. TELEGRAM API
# ==========================================

def telegram(method, data=None, files=None):
    if not TG_API:
        print("TELEGRAM ERROR: BOT_TOKEN is missing in Environment Variables.")
        return None

    try:
        response = requests.post(TG_API + method, data=data, files=files, timeout=90)
        if response.status_code != 200:
            print(f"TELEGRAM HTTP ERROR {response.status_code}:", response.text)
            return None

        result = response.json()
        if not result.get("ok"):
            print("TELEGRAM ERROR:", result)
        return result
    except Exception as e:
        print("TELEGRAM EXCEPTION:", repr(e))
        return None

def send_message(chat_id, text):
    return telegram("sendMessage", {"chat_id": chat_id, "text": text})

def send_typing(chat_id):
    telegram("sendChatAction", {"chat_id": chat_id, "action": "typing"})

# ==========================================
# 4. GEMINI AI CHAT
# ==========================================

def ask_ai(prompt):
    if not GEMINI_API_KEY:
        return "⚠️ Gemini API Key မရှိပါ။ Render Environment တွင် GEMINI_API_KEY ကို ထည့်ပေးပါ။"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    headers = {"Content-Type": "application/json"}
    params = {"key": GEMINI_API_KEY}

    instruction = """
မင်းနာမည်က Lix ပါ။ မင်းဟာ ဉာဏ်ရည်ထက်မြက်ပြီး ဖော်ရွေတဲ့ AI သူငယ်ချင်းတစ်ယောက်ပါ။
စည်းကမ်းများ -
1. မြန်မာလို သဘာဝကျကျ ပြောဆိုပါ။
2. အသုံးပြုသူရဲ့ မေးခွန်းကို တိကျစွာ ဖြေပါ။
3. သူငယ်ချင်းလို နွေးထွေးစွာ ပြောဆိုပါ။
4. အဖြေတိုင်းရဲ့အစမှာ 'Lix ဘက်ကနေ ဘာများကူညီပေးရမလဲ ❤️' ဆိုတဲ့စာသား ထည့်ပါ။
"""

    data = {
        "contents": [{"parts": [{"text": instruction + "\n\nUser: " + prompt}]}]
    }

    try:
        response = requests.post(url, headers=headers, params=params, json=data, timeout=120)
        if response.status_code != 200:
            print("GEMINI HTTP ERROR:", response.text)
            return f"⚠️ AI ဆာဗာ ချိတ်ဆက်ရာတွင် အမှားဖြစ်နေပါသည်။ (Error: {response.status_code})"

        result = response.json()
        if "candidates" in result and len(result["candidates"]) > 0:
            parts = result["candidates"][0]["content"]["parts"]
            answer = "".join(p.get("text", "") for p in parts)
            if answer:
                return answer

        return "⚠️ AI အဖြေထုတ်ရာမှာ အမှားဖြစ်နေပါတယ်။"
    except Exception as e:
        print("GEMINI EXCEPTION:", repr(e))
        return "⚠️ AI ချိတ်ဆက်မှု မအောင်မြင်ပါ။"

# ==========================================
# 5. ADVANCED AI IMAGE GENERATOR (Pollinations)
# ==========================================

def generate_image(prompt):
    models = [IMAGE_MODEL, "flux", "flux-realism", "any-dark"]
    models = list(dict.fromkeys(models))

    headers = {}
    if POLLINATIONS_API_KEY:
        headers["Authorization"] = f"Bearer {POLLINATIONS_API_KEY}"

    last_error = "Unknown Error"

    for model in models:
        try:
            encoded_prompt = urllib.parse.quote(prompt, safe="")
            url = f"https://image.pollinations.ai/prompt/{encoded_prompt}"
            params = {
                "model": model,
                "width": 1024,
                "height": 1024,
                "nologo": "true",
                "private": "true"
            }

            response = requests.get(url, headers=headers, params=params, timeout=180)
            content_type = response.headers.get("Content-Type", "")

            if response.status_code == 200 and ("image" in content_type or len(response.content) > 5000):
                return response.content, "image/jpeg"

            last_error = f"Model: {model}, Status: {response.status_code}"
        except Exception as e:
            last_error = repr(e)

    return None, last_error

# ==========================================
# 6. SEND IMAGE TO TELEGRAM
# ==========================================

def send_photo(chat_id, image_data, content_type, caption):
    try:
        files = {"photo": ("lix_image.jpg", image_data, content_type)}
        data = {"chat_id": chat_id, "caption": caption[:1000]}
        result = telegram("sendPhoto", data=data, files=files)
        return bool(result and result.get("ok"))
    except Exception as e:
        print("PHOTO ERROR:", repr(e))
        return False

# ==========================================
# 7. ITUNES SONG SEARCH
# ==========================================

def search_song(song_name):
    url = "https://itunes.apple.com/search"
    params = {"term": song_name, "limit": 1, "media": "music", "entity": "song"}
    try:
        response = requests.get(url, params=params, timeout=20)
        if response.status_code != 200:
            return None
        result = response.json()
        if result.get("resultCount", 0) > 0:
            track = result["results"][0]
            return {
                "title": track.get("trackName"),
                "artist": track.get("artistName"),
                "preview": track.get("previewUrl"),
                "album": track.get("collectionName")
            }
    except Exception as e:
        print("SONG SEARCH ERROR:", repr(e))
    return None

def send_audio(chat_id, song):
    try:
        data = {
            "chat_id": chat_id,
            "audio": song["preview"],
            "title": song["title"],
            "performer": song["artist"],
            "caption": f"🎵 {song['title']}\n🎤 {song['artist']}\n\n❤️ Lix AI Music"
        }
        result = telegram("sendAudio", data=data)
        return bool(result and result.get("ok"))
    except Exception as e:
        print("AUDIO ERROR:", repr(e))
        return False

# ==========================================
# 8. TEXT CLEANERS
# ==========================================

def clean_song_name(text):
    for w in ["သီချင်း", "ရှာပေးပါ", "ရှာပေး", "ရှာပေးပါဦး", "song", "music", "search"]:
        text = text.replace(w, "")
    return text.strip()

def clean_image_prompt(text):
    for w in ["ပုံဆွဲပေးပါ", "ပုံဆွဲပေး", "ပုံဆွဲ", "draw", "image", "generate"]:
        text = text.replace(w, "")
    return text.strip()

# ==========================================
# 9. MAIN BOT SYSTEM
# ==========================================

def main():
    if not BOT_TOKEN:
        print("ERROR: BOT_TOKEN Environment Variable is missing!")
        return

    offset = 0
    print("❤️ LIX AI V3.3 STARTED SUCCESSFULLY!")

    while True:
        try:
            response = requests.get(
                TG_API + "getUpdates",
                params={"offset": offset, "timeout": 25, "allowed_updates": json.dumps(["message"])},
                timeout=35
            )
            if response.status_code != 200:
                time.sleep(5)
                continue

            result = response.json()
            if not result.get("ok"):
                time.sleep(5)
                continue

            for update in result.get("result", []):
                offset = update["update_id"] + 1
                msg = update.get("message", {})
                chat_id = msg.get("chat", {}).get("id")
                text = msg.get("text", "").strip()

                if not chat_id or not text:
                    continue

                # Rate Limit
                current_time = time.time()
                if current_time - user_last_msg_time.get(chat_id, 0) < 2:
                    send_message(chat_id, "⏳ ခဏလေးစောင့်ပါဦး ❤️")
                    continue
                user_last_msg_time[chat_id] = current_time
                lower_text = text.lower()

                # Start
                if text == "/start":
                    send_message(chat_id, "❤️ မင်္ဂလာပါ။ Lix AI V3.3 မှ ကြိုဆိုပါတယ်။ ပုံဆွဲရန်၊ သီချင်းရှာရန်နှင့် စကားပြောရန် အသင့်ဖြစ်နေပါပြီ။")
                    continue

                # Image Generation
                if any(k in lower_text for k in ["ပုံဆွဲ", "draw", "image", "generate"]):
                    send_typing(chat_id)
                    prompt = clean_image_prompt(text)
                    if not prompt:
                        send_message(chat_id, "🎨 ဘယ်လိုပုံမျိုး ဆွဲပေးရမလဲ ပြောပြပါဦး။")
                        continue
                    send_message(chat_id, "🎨 Lix AI က ပုံဖန်တီးနေပါတယ်။ ခဏစောင့်ပေးပါဦး ❤️")
                    image_data, c_type = generate_image(prompt)
                    if image_data:
                        send_photo(chat_id, image_data, c_type, "🎨 Lix AI Image Generator\n\n" + prompt)
                    else:
                        send_message(chat_id, "⚠️ ပုံဆွဲမအောင်မြင်ပါ။ နောက်တစ်ကြိမ် ထပ်ကြိုးစားပါ။")
                    continue

                # Song Search
                if any(k in lower_text for k in ["သီချင်း", "song", "music"]):
                    send_typing(chat_id)
                    song_query = clean_song_name(text)
                    if not song_query:
                        send_message(chat_id, "🎵 ဘယ်သီချင်းရှာပေးရမလဲ ပြောပြပါဦး။")
                        continue
                    song = search_song(song_query)
                    if song and song.get("preview"):
                        send_audio(chat_id, song)
                    else:
                        send_message(chat_id, "😔 သီချင်းရှာမတွေ့ပါဘူး။ နာမည်ပြန်စစ်ပေးပါဦး။")
                    continue

                # Normal Chat
                send_typing(chat_id)
                answer = ask_ai(text)
                send_message(chat_id, answer[:4000])

        except Exception as e:
            print("MAIN LOOP ERROR:", repr(e))
            time.sleep(5)

if __name__ == "__main__":
    keep_alive()
    main()
