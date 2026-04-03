import os
import requests
from datetime import datetime

GOOGLE_PLACES_API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_IDS = os.environ.get("TELEGRAM_CHAT_IDS", "").split(",")

LOCALES = [
    ("-34.6038802", "-58.4109897", "Distrito Buenos Aires - Abasto"),
    ("-34.598775",  "-58.375071",  "Distrito Buenos Aires - Galerias"),
    ("-34.6185106", "-58.4373451", "Distrito Buenos Aires - Caballito"),
    ("-32.9014375", "-68.7992918", "Distrito Mza"),
    ("-34.5464842", "-58.4878536", "Distrito Buenos Aires - Dot"),
]

def buscar_place_id(lat, lng, nombre):
    try:
        params = {
            "input": "Distrito",
            "inputtype": "textquery",
            "locationbias": f"circle:50@{lat},{lng}",
            "fields": "place_id,name",
            "key": GOOGLE_PLACES_API_KEY
        }
        r = requests.get("https://maps.googleapis.com/maps/api/place/findplacefromtext/json", params=params, timeout=10)
        data = r.json()
        if data.get("candidates"):
            return data["candidates"][0]["place_id"]
        return None
    except Exception as e:
        print(f"Error buscando {nombre}: {e}")
        return None

def obtener_info_lugar(place_id):
    try:
        params = {
            "place_id": place_id,
            "fields": "name,rating,user_ratings_total,reviews",
            "language": "es",
            "reviews_sort": "newest",
            "key": GOOGLE_PLACES_API_KEY
        }
        r = requests.get("https://maps.googleapis.com/maps/api/place/details/json", params=params, timeout=10)
        data = r.json()
        if data.get("status") == "OK":
            return data["result"]
        print(f"Error Places API: {data.get('status')} - {data.get('error_message','')}")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def analizar_con_gemini(nombre, rating, total, resenas):
