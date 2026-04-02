import os
import requests
from datetime import datetime
import google.generativeai as genai

GOOGLE_PLACES_API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_IDS = os.environ.get("TELEGRAM_CHAT_IDS", "").split(",")

LOCALES_MAPS_URLS = [
    "https://maps.app.goo.gl/eohCcwA5x82d699x9",
    "https://maps.app.goo.gl/WDN318BxM4n3FtZt8",
    "https://maps.app.goo.gl/AMATkvQaTKUx7G7v5",
    "https://maps.app.goo.gl/JZvtwQEzi9An6eQH8",
    "https://maps.app.goo.gl/TUCe7EEokJMpMANv5",
]

def resolver_place_id(maps_url):
    try:
        response = requests.get(maps_url, allow_redirects=True, timeout=10)
        final_url = response.url
        import re
        coords_match = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', final_url)
        if coords_match:
            lat = coords_match.group(1)
            lng = coords_match.group(2)
            params = {"location": f"{lat},{lng}", "radius": 50, "key": GOOGLE_PLACES_API_KEY}
            resp = requests.get("https://maps.googleapis.com/maps/api/place/nearbysearch/json", params=params, timeout=10)
            data = resp.json()
            if data.get("results"):
                return data["results"][0]["place_id"], data["results"][0]["name"]
        return None, None
    except Exception as e:
        print(f"Error: {e}")
        return None, None

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
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": chat_id.strip(), "text": mensaje, "parse_mode": "HTML"}, timeout=10)
            print(f"✅ Enviado a {chat_id}")
        except Exception as e:
            print(f"Error: {e}")

def main():
    fecha = datetime.now().strftime("%d/%m/%Y")
    informe = f"📊 <b>INFORME DIARIO DE RESEÑAS</b>\n📅 {fecha} - 23:59hs\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
    for i, url in enumerate(LOCALES_MAPS_URLS, 1):
        print(f"Procesando local {i}...")
        place_id, _ = resolver_place_id(url)
        if not place_id:
            informe += f"🏪 <b>Local {i}</b>\n❌ No se pudo acceder.\n\n"
            continue
        info = obtener_info_lugar(place_id)
        if not info:
            informe += f"🏪 <b>Local {i}</b>\n❌ Error obteniendo datos.\n\n"
            continue
        nombre = info.get("name", f"Local {i}")
        rating = info.get("rating", "N/D")
        total = info.get("user_ratings_total", 0)
        resenas = info.get("reviews", [])
        analisis = analizar_con_gemini(nombre, rating, total, resenas) if resenas else "Sin reseñas recientes."
        informe += f"🏪 <b>{nombre}</b>\n⭐ {rating}/5 ({total} reseñas)\n{analisis}\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
    informe += "🤖 Monitor Automático de Reseñas"
    enviar_telegram(informe)
    print("✅ Informe enviado")

if __name__ == "__main__":
    main()
