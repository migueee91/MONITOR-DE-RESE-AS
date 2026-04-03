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
    try:
        texto = "\n".join([f"- {r.get('author_name')} ({r.get('rating')}⭐): {r.get('text','')}" for r in resenas])
        prompt = f"""Analiza las resenas de {nombre} con rating {rating} sobre 5 y {total} resenas totales.
Resenas recientes: {texto}
Responde exactamente asi:
PUNTOS FUERTES: maximo 3
PUNTOS DEBILES: maximo 3
RECOMENDACIONES: maximo 2
TENDENCIA: una frase
Maximo 150 palabras."""
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        r = requests.post(url, json=payload, timeout=30)
        data = r.json()
        print(f"Gemini status: {r.status_code}")
        print(f"Gemini data: {data}")
        if "candidates" in data:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        elif "error" in data:
            print(f"Gemini error: {data['error']}")
            return "Error en analisis."
        return "Sin analisis disponible."
    except Exception as e:
        print(f"Error Gemini: {e}")
        return "Error generando analisis."

def enviar_telegram(mensaje):
    for chat_id in TELEGRAM_CHAT_IDS:
        try:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": chat_id.strip(), "text": mensaje, "parse_mode": "HTML"},
                timeout=10
            )
            print(f"✅ Enviado a {chat_id}")
        except Exception as e:
            print(f"Error Telegram: {e}")

def main():
    fecha = datetime.now().strftime("%d/%m/%Y")
    informe = f"📊 INFORME DIARIO DE RESEÑAS\n📅 {fecha} - 23:59hs\n\n"

    for lat, lng, nombre_default in LOCALES:
        print(f"Procesando {nombre_default}...")
        place_id = buscar_place_id(lat, lng, nombre_default)
        if not place_id:
            informe += f"🏪 {nombre_default}\n❌ No se encontro el local.\n\n"
            continue
        info = obtener_info_lugar(place_id)
        if not info:
            informe += f"🏪 {nombre_default}\n❌ Error obteniendo datos.\n\n"
            continue
        nombre = info.get("name", nombre_default)
        rating = info.get("rating", "N/D")
        total = info.get("user_ratings_total", 0)
        resenas = info.get("reviews", [])
        analisis = analizar_con_gemini(nombre, rating, total, resenas) if resenas else "Sin resenas recientes."
        informe += f"🏪 {nombre}\n⭐ {rating}/5 ({total} resenas totales)\n{analisis}\n\n"

    informe += "🤖 Monitor Automatico de Resenas"
    enviar_telegram(informe)
    print("✅ Informe enviado")

if __name__ == "__main__":
