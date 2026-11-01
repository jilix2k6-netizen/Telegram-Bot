import os
import json
import time
import urllib.parse
import requests

from flask import Flask
from threading import Thread

# ==========================================
# 1. WEB SERVER
# ==========================================

app = Flask(__name__)

@app.route('/')
def home():
    return "❤️ Lix AI Bot V2.0 is Running!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    Thread(target=run, daemon=True).start()


# ==========================================
# 2. API SETTINGS
# ==========================================

TG_API = os.environ.get("TG_API", "").rstrip("/") + "/"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

POLLINATIONS_API_KEY = os.environ.get("POLLINATIONS_API_KEY")

IMAGE_MODEL = os.environ.get(
    "IMAGE_MODEL",
    "google/gemini-3.1-flash-image"
)

TEXT_MODEL = "gemini-2.5-flash"

user_last_msg_time = {}


# ==========================================
# 3. TELEGRAM FUNCTIONS
# ==========================================

def telegram(method, data=None, files=None):

    url = TG_API + method

    try:
        response = requests.post(
            url,
            data=data,
            files=files,
            timeout=60
        )

        result = response.json()

        if not result.get("ok"):
            print("Telegram Error:", result)

        return result

    except Exception as e:
        print("Telegram Error:", e)
        return None


def send_message(chat_id, text):

    return telegram("sendMessage", {
        "chat_id": chat_id,
        "text": text
    })


def send_typing(chat_id):

    telegram("sendChatAction", {
        "chat_id": chat_id,
        "action": "typing"
    })


# ==========================================
# 4. GEMINI AI
# ==========================================

def ask_ai(prompt):

    if not GEMINI_API_KEY:
        return "⚠️ Gemini API Key မရှိသေးပါ။"

    url = (
        "https://generativelanguage.googleapis.com/"
        f"v1beta/models/{TEXT_MODEL}:generateContent"
        f"?key={GEMINI_API_KEY}"
    )

    instruction = """
မင်းနာမည်က Lix ပါ။

မင်းဟာ ဖော်ရွေပြီး ဉာဏ်ရည်ထက်မြက်တဲ့ AI သူငယ်ချင်းတစ်ယောက်ပါ။

စည်းကမ်းများ -

1. အသုံးပြုသူကို မြန်မာလို သဘာဝကျကျ ပြန်ဖြေပါ။
2. လိုအပ်ရင် English နဲ့လည်း ဖြေနိုင်ပါတယ်။
3. အဖြေတိုင်းရဲ့အစမှာ
'Lix ဘက်ကနေ ဘာများကူညီပေးရမလဲ ❤️'
ဆိုတဲ့စာသား ထည့်ပါ။
4. မေးခွန်းကို နားလည်အောင် ကြိုးစားပါ။
5. အချက်အလက်တွေကို တိကျအောင် ဖြေပါ။
6. သူငယ်ချင်းတစ်ယောက်လို နွေးထွေးစွာ ပြောဆိုပါ။
"""

    data = {
        "contents": [{
            "parts": [{
                "text": instruction + "\n\nUser: " + prompt
            }]
        }]
    }

    try:

        response = requests.post(
            url,
            json=data,
            timeout=90
        )

        result = response.json()

        if "candidates" in result:

            return result["candidates"][0]["content"]["parts"][0]["text"]

        print("Gemini Error:", result)

        return "⚠️ AI ချိတ်ဆက်မှု အမှားဖြစ်နေပါတယ်။"

    except Exception as e:

        print("AI Error:", e)

        return "⚠️ AI အလုပ်လုပ်ရာမှာ အခက်အခဲရှိနေပါတယ်။"


# ==========================================
# 5. ADVANCED IMAGE GENERATOR
# ==========================================

def generate_image(prompt):

    encoded_prompt = urllib.parse.quote(prompt)

    url = (
        f"https://gen.pollinations.ai/image/{encoded_prompt}"
        f"?model={urllib.parse.quote(IMAGE_MODEL)}"
        "&width=1024"
        "&height=1024"
        "&nologo=true"
    )

    headers = {}

    if POLLINATIONS_API_KEY:

        headers["Authorization"] = (
            f"Bearer {POLLINATIONS_API_KEY}"
        )

    try:

        response = requests.get(
            url,
            headers=headers,
            timeout=180
        )

        response.raise_for_status()

        content_type = response.headers.get(
            "Content-Type", ""
        )

        if "image/" not in content_type:

            print("Image Error:", response.text[:500])
            return None

        return response.content

    except Exception as e:

        print("Image Generation Error:", e)

        return None


def send_photo(chat_id, image_data, caption):

    try:

        files = {
            "photo": (
                "lix_ai_image.jpg",
                image_data,
                "image/jpeg"
            )
        }

        data = {
            "chat_id": chat_id,
            "caption": caption[:1000]
        }

        result = telegram(
            "sendPhoto",
            data=data,
            files=files
        )

        return result

    except Exception as e:

        print("Photo Send Error:", e)
        return None


# ==========================================
# 6. SONG SEARCH
# ==========================================

def search_song(song_name):

    url = "https://itunes.apple.com/search"

    params = {
        "term": song_name,
        "limit": 1,
        "media": "music",
        "entity": "song"
    }

    try:

        response = requests.get(
            url,
            params=params,
            timeout=20
        )

        result = response.json()

        if result.get("resultCount", 0) > 0:

            track = result["results"][0]

            return {
                "preview_url": track.get("previewUrl"),
                "title": track.get("trackName"),
                "artist": track.get("artistName"),
                "album": track.get("collectionName")
            }

    except Exception as e:

        print("Song Search Error:", e)

    return None


# ==========================================
# 7. SEND SONG IN ONE MESSAGE
# ==========================================

def send_audio(chat_id, song):

    try:

        data = {
            "chat_id": chat_id,
            "audio": song["preview_url"],
            "title": song["title"],
            "performer": song["artist"],
            "caption": (
                "🎵 " + song["title"] +
                "\n🎤 Artist: " + song["artist"] +
                "\n\n❤️ Sent by Lix AI"
            )
        }

        result = telegram("sendAudio", data)

        return result

    except Exception as e:

        print("Audio Error:", e)
        return None


# ==========================================
# 8. MAIN BOT
# ==========================================

keep_alive()

offset = 0

print("❤️ LIX AI BOT V2.0 RUNNING!")


while True:

    try:

        response = requests.get(
            TG_API + "getUpdates",
            params={
                "offset": offset,
                "timeout": 25
            },
            timeout=35
        )

        updates = response.json().get("result", [])

        for update in updates:

            offset = update["update_id"] + 1

            msg = update.get("message", {})

            chat_id = msg.get("chat", {}).get("id")

            text = msg.get("text", "").strip()

            if not chat_id or not text:
                continue

            # RATE LIMIT

            current_time = time.time()

            if chat_id in user_last_msg_time:

                if current_time - user_last_msg_time[chat_id] < 3:

                    send_message(
                        chat_id,
                        "⏳ ခဏလေးစောင့်ပြီးမှ ပြန်မေးပေးပါဦး ❤️"
                    )

                    continue

            user_last_msg_time[chat_id] = current_time


            # START COMMAND

            if text == "/start":

                send_message(
                    chat_id,
                    """
❤️ မင်္ဂလာပါ။ Lix AI Bot မှ ကြိုဆိုပါတယ်။

ကျွန်တော်က Lix ပါ။

အသုံးပြုနိုင်တဲ့ Features များ -

💬 AI စကားပြောရန်
စာတစ်ခုခု ရိုက်ပို့လိုက်ပါ။

🎵 သီချင်းရှာရန်
သီချင်း Shape of You

🎨 AI ပုံဆွဲရန်
ပုံဆွဲပေးပါ ကြောင်လေးတစ်ကောင်

❤️ Lix AI V2.0
"""
                )

                continue


            # IMAGE GENERATION

            if (
                "ပုံဆွဲ" in text.lower()
                or "draw" in text.lower()
                or "image" in text.lower()
            ):

                send_typing(chat_id)

                prompt = text

                for word in [
                    "ပုံဆွဲပေးပါ",
                    "ပုံဆွဲ",
                    "draw",
                    "image"
                ]:

                    prompt = prompt.replace(word, "")

                prompt = prompt.strip()

                if not prompt:

                    send_message(
                        chat_id,
                        "🎨 ဘယ်လိုပုံမျိုး ဆွဲပေးရမလဲ ပြောပြပါဦး။"
                    )

                    continue

                send_message(
                    chat_id,
                    "🎨 Lix AI က ပုံဖန်တီးနေပါတယ်။ ခဏစောင့်ပေးပါဦး ❤️"
                )

                image_data = generate_image(prompt)

                if image_data:

                    send_photo(
                        chat_id,
                        image_data,
                        "🎨 Lix AI Image Generator\n\n" + prompt
                    )

                else:

                    send_message(
                        chat_id,
                        "⚠️ ပုံဆွဲရာမှာ အမှားဖြစ်သွားပါတယ်။ API Key နဲ့ Model ကို ပြန်စစ်ပေးပါ။"
                    )

                continue


            # SONG SEARCH

            if (
                "သီချင်း" in text.lower()
                or "song" in text.lower()
                or "music" in text.lower()
            ):

                send_typing(chat_id)

                song_query = text

                for word in [
                    "သီချင်း",
                    "ရှာပေးပါ",
                    "ရှာပေး",
                    "song",
                    "music"
                ]:

                    song_query = song_query.replace(word, "")

                song_query = song_query.strip()

                if not song_query:

                    send_message(
                        chat_id,
                        "🎵 ဘယ်သီချင်းရှာပေးရမလဲ ပြောပြပါဦး။"
                    )

                    continue

                song_data = search_song(song_query)

                if song_data and song_data["preview_url"]:

                    send_audio(chat_id, song_data)

                else:

                    send_message(
                        chat_id,
                        "😔 သီချင်းရှာမတွေ့ပါဘူး။ နာမည်ပြန်စစ်ပေးပါဦး။"
                    )

                continue


            # NORMAL AI CHAT

            send_typing(chat_id)

            answer = ask_ai(text)

            send_message(
                chat_id,
                answer[:4000]
            )


    except Exception as e:

        print("Main Loop Error:", str(e))

        time.sleep(5)
