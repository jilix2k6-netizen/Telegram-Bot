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
    return "❤️ Lix AI V3.0 is Running!"


def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)


def keep_alive():
    Thread(target=run, daemon=True).start()


# ==========================================
# 2. API CONFIGURATION
# ==========================================

TG_API = os.environ.get("TG_API", "").rstrip("/") + "/"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

POLLINATIONS_API_KEY = os.environ.get("POLLINATIONS_API_KEY")

GEMINI_MODEL = os.environ.get(
    "GEMINI_MODEL",
    "gemini-3.8-flash"
)

IMAGE_MODEL = os.environ.get(
    "IMAGE_MODEL",
    "google/gemini-3.1-flash-image"
)

user_last_msg_time = {}


# ==========================================
# 3. TELEGRAM API
# ==========================================

def telegram(method, data=None, files=None):

    try:

        response = requests.post(
            TG_API + method,
            data=data,
            files=files,
            timeout=90
        )

        result = response.json()

        if not result.get("ok"):

            print("TELEGRAM ERROR:", result)

        return result

    except Exception as e:

        print("TELEGRAM EXCEPTION:", repr(e))

        return None


def send_message(chat_id, text):

    return telegram(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text
        }
    )


def send_typing(chat_id):

    telegram(
        "sendChatAction",
        {
            "chat_id": chat_id,
            "action": "typing"
        }
    )


# ==========================================
# 4. GEMINI AI CHAT
# ==========================================

def ask_ai(prompt):

    if not GEMINI_API_KEY:

        return "⚠️ Gemini API Key မရှိသေးပါ။"

    url = (
        "https://generativelanguage.googleapis.com/"
        f"v1beta/models/{GEMINI_MODEL}:generateContent"
    )

    headers = {
        "Content-Type": "application/json"
    }

    params = {
        "key": GEMINI_API_KEY
    }

    instruction = """
မင်းနာမည်က Lix ပါ။

မင်းဟာ ဉာဏ်ရည်ထက်မြက်ပြီး ဖော်ရွေတဲ့ AI သူငယ်ချင်းတစ်ယောက်ပါ။

စည်းကမ်းများ -

1. မြန်မာလို သဘာဝကျကျ ပြောဆိုပါ။
2. အသုံးပြုသူရဲ့ မေးခွန်းကို သေချာနားလည်ပါ။
3. တိကျတဲ့ အချက်အလက်တွေပေးပါ။
4. လိုအပ်ရင် English နဲ့လည်း ဖြေပါ။
5. သူငယ်ချင်းတစ်ယောက်လို နွေးထွေးစွာ ပြောဆိုပါ။
6. အဖြေတိုင်းရဲ့အစမှာ
'Lix ဘက်ကနေ ဘာများကူညီပေးရမလဲ ❤️'
ဆိုတဲ့စာသား ထည့်ပါ။
"""

    data = {
        "contents": [
            {
                "parts": [
                    {
                        "text": instruction + "\n\nUser: " + prompt
                    }
                ]
            }
        ]
    }

    try:

        response = requests.post(
            url,
            headers=headers,
            params=params,
            json=data,
            timeout=120
        )

        result = response.json()

        if "candidates" in result:

            parts = result["candidates"][0]["content"]["parts"]

            answer = "".join(
                p.get("text", "") for p in parts
            )

            if answer:
                return answer

        print("GEMINI ERROR:", result)

        return "⚠️ AI အဖြေထုတ်ရာမှာ အမှားဖြစ်နေပါတယ်။"

    except Exception as e:

        print("GEMINI EXCEPTION:", repr(e))

        return "⚠️ AI ချိတ်ဆက်မှု မအောင်မြင်ပါ။"


# ==========================================
# 5. ADVANCED AI IMAGE GENERATOR
# ==========================================

def generate_image(prompt):

    if not POLLINATIONS_API_KEY:

        return None, "Pollinations API Key မရှိပါ။"

    models = [
        IMAGE_MODEL,
        "google/gemini-3.1-flash-image",
        "black-forest-labs/flux.1-schnell"
    ]

    # Duplicate models ဖယ်ရှားခြင်း
    models = list(dict.fromkeys(models))

    headers = {
        "Authorization": f"Bearer {POLLINATIONS_API_KEY}"
    }

    for model in models:

        try:

            print("IMAGE MODEL:", model)

            url = (
                "https://gen.pollinations.ai/image/"
                + urllib.parse.quote(prompt, safe="")
            )

            params = {
                "model": model,
                "width": 1024,
                "height": 1024,
                "nologo": "true"
            }

            response = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=240
            )

            content_type = response.headers.get(
                "Content-Type", ""
            )

            print("IMAGE STATUS:", response.status_code)
            print("IMAGE TYPE:", content_type)

            if response.status_code == 200:

                if content_type.startswith("image/"):

                    print("IMAGE SUCCESS:", model)

                    return (
                        response.content,
                        content_type
                    )

            print(
                "IMAGE ERROR DETAIL:",
                response.text[:1000]
            )

            last_error = (
                f"Model: {model}\n"
                f"Status: {response.status_code}\n"
                f"Error: {response.text[:700]}"
            )

        except Exception as e:

            last_error = repr(e)

            print("IMAGE EXCEPTION:", last_error)

    return None, last_error


# ==========================================
# 6. SEND IMAGE TO TELEGRAM
# ==========================================

def send_photo(chat_id, image_data, content_type, caption):

    try:

        extension = "png"

        if "jpeg" in content_type:
            extension = "jpg"

        files = {
            "photo": (
                f"lix_image.{extension}",
                image_data,
                content_type
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

        return bool(result and result.get("ok"))

    except Exception as e:

        print("PHOTO ERROR:", repr(e))

        return False


# ==========================================
# 7. ITUNES SONG SEARCH
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
                "title": track.get("trackName"),
                "artist": track.get("artistName"),
                "preview": track.get("previewUrl"),
                "album": track.get("collectionName")
            }

    except Exception as e:

        print("SONG SEARCH ERROR:", repr(e))

    return None


# ==========================================
# 8. SEND SONG IN ONE MESSAGE
# ==========================================

def send_audio(chat_id, song):

    try:

        data = {
            "chat_id": chat_id,
            "audio": song["preview"],
            "title": song["title"],
            "performer": song["artist"],
            "caption": (
                "🎵 " + song["title"] +
                "\n🎤 " + song["artist"] +
                "\n\n❤️ Lix AI Music"
            )
        }

        result = telegram(
            "sendAudio",
            data=data
        )

        return bool(result and result.get("ok"))

    except Exception as e:

        print("AUDIO ERROR:", repr(e))

        return False


# ==========================================
# 9. TEXT COMMAND CLEANER
# ==========================================

def clean_song_name(text):

    words = [
        "သီချင်း",
        "ရှာပေးပါ",
        "ရှာပေး",
        "ရှာပေးပါဦး",
        "song",
        "music",
        "search"
    ]

    result = text

    for word in words:

        result = result.replace(word, "")

    return result.strip()


def clean_image_prompt(text):

    words = [
        "ပုံဆွဲပေးပါ",
        "ပုံဆွဲပေး",
        "ပုံဆွဲ",
        "draw",
        "image",
        "generate"
    ]

    result = text

    for word in words:

        result = result.replace(word, "")

    return result.strip()


# ==========================================
# 10. MAIN BOT SYSTEM
# ==========================================

def main():

    if not TG_API.strip("/"):

        print("ERROR: TG_API NOT FOUND")
        return

    offset = 0

    print("❤️ LIX AI V3.0 STARTED!")

    while True:

        try:

            response = requests.get(
                TG_API + "getUpdates",
                params={
                    "offset": offset,
                    "timeout": 25,
                    "allowed_updates": json.dumps(["message"])
                },
                timeout=35
            )

            result = response.json()

            if not result.get("ok"):

                print("GET UPDATES ERROR:", result)

                time.sleep(5)
                continue

            updates = result.get("result", [])

            for update in updates:

                offset = update["update_id"] + 1

                msg = update.get("message", {})

                chat_id = msg.get(
                    "chat", {}
                ).get("id")

                text = msg.get("text", "").strip()

                if not chat_id or not text:
                    continue

                # RATE LIMIT

                current_time = time.time()

                last_time = user_last_msg_time.get(
                    chat_id, 0
                )

                if current_time - last_time < 3:

                    send_message(
                        chat_id,
                        "⏳ ခဏလေးစောင့်ပြီးမှ ပြန်မေးပေးပါဦး ❤️"
                    )

                    continue

                user_last_msg_time[chat_id] = current_time

                lower_text = text.lower()

                # START COMMAND

                if text == "/start":

                    send_message(
                        chat_id,
                        """
❤️ မင်္ဂလာပါ။ Lix AI V3.0 မှ ကြိုဆိုပါတယ်။

ကျွန်တော်က Lix ပါ။

အသုံးပြုနိုင်တဲ့ Features များ -

💬 AI စကားပြောရန်
စာတစ်ခုခု ရိုက်ပို့လိုက်ပါ။

🎨 AI ပုံဆွဲရန်
ပုံဆွဲပေးပါ ကြောင်လေးတစ်ကောင်

🎵 သီချင်းရှာရန်
သီချင်း Shape of You

❤️ Lix AI V3.0
"""
                    )

                    continue

                # IMAGE GENERATION

                if (
                    "ပုံဆွဲ" in lower_text
                    or "draw" in lower_text
                    or "image" in lower_text
                    or "generate image" in lower_text
                ):

                    send_typing(chat_id)

                    prompt = clean_image_prompt(text)

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

                    image_data, content_type = generate_image(prompt)

                    if image_data:

                        success = send_photo(
                            chat_id,
                            image_data,
                            content_type,
                            "🎨 Lix AI Image Generator\n\n" + prompt
                        )

                        if not success:

                            send_message(
                                chat_id,
                                "⚠️ ပုံဖန်တီးပြီးပါပြီ။ Telegram ကို ပို့ရာမှာ အမှားဖြစ်နေပါတယ်။"
                            )

                    else:

                        send_message(
                            chat_id,
                            "⚠️ ပုံဆွဲမအောင်မြင်ပါ။\n\n"
                            + str(content_type)[:2500]
                        )

                    continue

                # SONG SEARCH

                if (
                    "သီချင်း" in lower_text
                    or "song" in lower_text
                    or "music" in lower_text
                ):

                    send_typing(chat_id)

                    song_query = clean_song_name(text)

                    if not song_query:

                        send_message(
                            chat_id,
                            "🎵 ဘယ်သီချင်းရှာပေးရမလဲ ပြောပြပါဦး။"
                        )

                        continue

                    song = search_song(song_query)

                    if song and song.get("preview"):

                        success = send_audio(
                            chat_id,
                            song
                        )

                        if not success:

                            send_message(
                                chat_id,
                                "⚠️ သီချင်းပို့လို့ မရသေးပါဘူး။"
                            )

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

            print("MAIN LOOP ERROR:", repr(e))

            time.sleep(5)


# ==========================================
# 11. START APPLICATION
# ==========================================

if __name__ == "__main__":

    keep_alive()

    main()
