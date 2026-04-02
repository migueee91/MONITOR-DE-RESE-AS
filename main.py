import os
import requests
from datetime import datetime
import google.generativeai as genai

GOOGLE_PLACES_API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_IDS = os.environ.get("TELEGRAM_CHAT_IDS", "").split(",")

LOCALES = [
    ("ChIJS-EB_2PLvJARuPs7C79WkL4", "Distrito Buenos Aires - Abasto"),
    ("ChIJza1fbHPLvJAR5WJiv93cXJ8", "Distrito Buenos Aires - Galerias"),
    ("ChIJs4GTPatcvJARMAtJ7kaxxPI", "Distrito Buenos Aires - Caballito"),
    ("ChIJjd8nNVN17pYR1gAy8B-WJNk", "Distrito Mza"),
    ("ChIJl6rV9eW3vJARz0u2NvD9Xi4", "Distrito Buenos Aires - Dot"),
]

def obtener_info_lugar(place_id):
    try:
        params = {
            "place_id": place_id,
            "fields": "name,rating,user_ratings_total,reviews",
            "language": "es",
            "reviews_sort": "newest",
            "key": GOOGLE_PLACES_API_KEY
        }
        response = requests.get("https://maps.googleapis.com/maps/api/place/details/json", params=params, timeout=10)
        data = response.json()
        if data.get("status") == "OK":
            return data["result"]
        print(f"Error Places API: {data.get('status')} - {data.get('error_message','')}")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def analizar_con_gemini(nombre, rating, total, resenas):
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        texto = "\n".join([f"- {r.get('author_name')} ({r.get('rating')}⭐): {r.get('text','')}" for r in resenas])
        prompt = f"""Analizá las reseñas de "{nombre}" (Rating: {rating}/5, Total: {total}).
RESEÑAS: {texto}
Respondé exactamente así:
✅ PUNTOS FUERTES: (máximo 3)
⚠️ PUNTOS DÉBILES: (máximo 3)
💡 RECOMENDACIONES: (máximo 2)
📊 TENDENCIA: (una frase)
Máximo 150 palabras."""
        return model.generate_content(prompt).text
    except Exception as e:
        return f"Error análisis: {e}"

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
    informe = f"📊 <b>INFORME DIARIO DE RESEÑAS</b>\n📅 {fecha} - 23:59hs\n━━━━━━━━━━━━━━━━━━━━━━\n\n"

    for place_id, nombre_default in LOCALES:
        print(f"Procesando {nombre_default}...")
        info = obtener_info_lugar(place_id)
        if not info:
            informe += f"🏪 <b>{nombre_default}</b>\n❌ Error obteniendo datos.\n\n"
            continue
        nombre = info.get("name", nombre_default)
        rating = info.get("rating", "N/D")
        total = info.get("user_ratings_total", 0)
        resenas = info.get("reviews", [])
        analisis = analizar_con_gemini(nombre, rating, total, resenas) if resenas else "Sin reseñas recientes."
        informe += f"🏪 <b>{nombre}</b>\n⭐ {rating}/5 ({total} reseñas totales)\n{analisis}\n━━━━━━━━━━━━━━━━━━━━━━\n\n"

    informe += "🤖 Monitor Automático de Reseñas"
    enviar_telegram(informe)
    print("✅ Informe enviado")

if __name__ == "__main__":
    main()
