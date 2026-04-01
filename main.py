import os
import requests
import json
import schedule
import time
from datetime import datetime
import google.generativeai as genai

# ============================================================
# CONFIGURACIÓN - Reemplazá con tus credenciales
# ============================================================
GOOGLE_PLACES_API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY", "TU_GOOGLE_PLACES_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "TU_GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "TU_TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_IDS = os.environ.get("TELEGRAM_CHAT_IDS", "TU_CHAT_ID").split(",")

# Links de Google Maps de los locales
LOCALES_MAPS_URLS = [
    "https://maps.app.goo.gl/eohCcwA5x82d699x9",
    "https://maps.app.goo.gl/WDN318BxM4n3FtZt8",
    "https://maps.app.goo.gl/AMATkvQaTKUx7G7v5",
    "https://maps.app.goo.gl/JZvtwQEzi9An6eQH8",
    "https://maps.app.goo.gl/TUCe7EEokJMpMANv5",
]

# ============================================================
# FUNCIONES
# ============================================================

def resolver_place_id(maps_url):
    """Resuelve el Place ID a partir de un link de Google Maps"""
    try:
        # Seguir redirecciones para obtener la URL completa
        response = requests.get(maps_url, allow_redirects=True, timeout=10)
        final_url = response.url
        
        # Buscar el lugar por texto usando la URL resuelta
        # Extraer nombre del lugar de la URL
        search_url = f"https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
        
        # Intentar extraer coordenadas o nombre de la URL
        import re
        # Buscar patrón de coordenadas en la URL
        coords_match = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', final_url)
        
        if coords_match:
            lat = coords_match.group(1)
            lng = coords_match.group(2)
            
            # Buscar nearby places
            nearby_url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            params = {
                "location": f"{lat},{lng}",
                "radius": 50,
                "key": GOOGLE_PLACES_API_KEY
            }
            resp = requests.get(nearby_url, params=params)
            data = resp.json()
            
            if data.get("results"):
                return data["results"][0]["place_id"], data["results"][0]["name"]
        
        return None, None
    except Exception as e:
        print(f"Error resolviendo URL {maps_url}: {e}")
        return None, None


def obtener_info_lugar(place_id):
    """Obtiene información y reseñas de un lugar usando Places API"""
    try:
        url = "https://maps.googleapis.com/maps/api/place/details/json"
        params = {
            "place_id": place_id,
            "fields": "name,rating,user_ratings_total,reviews,formatted_address",
            "language": "es",
            "reviews_sort": "newest",
            "key": GOOGLE_PLACES_API_KEY
        }
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if data.get("status") == "OK":
            return data["result"]
        else:
            print(f"Error Places API: {data.get('status')} - {data.get('error_message', '')}")
            return None
    except Exception as e:
        print(f"Error obteniendo info del lugar: {e}")
        return None


def analizar_resenas_con_gemini(nombre, rating, total_resenas, resenas):
    """Analiza las reseñas usando Gemini y genera un informe"""
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Preparar texto de reseñas
        texto_resenas = ""
        for r in resenas:
            autor = r.get("author_name", "Anónimo")
            estrellas = r.get("rating", 0)
            texto = r.get("text", "Sin texto")
            fecha = r.get("relative_time_description", "")
            texto_resenas += f"- {autor} ({estrellas}⭐, {fecha}): {texto}\n"
        
        prompt = f"""Analizá las siguientes reseñas del local "{nombre}" y generá un informe ejecutivo en español.

DATOS GENERALES:
- Rating actual: {rating}/5
- Total de reseñas: {total_resenas}

RESEÑAS RECIENTES:
{texto_resenas}

Generá un informe con este formato exacto:
✅ PUNTOS FUERTES: (máximo 3, una línea cada uno)
⚠️ PUNTOS DÉBILES: (máximo 3, una línea cada uno)  
💡 RECOMENDACIONES: (máximo 2 acciones concretas)
📊 TENDENCIA: (una frase sobre si va bien, mal o estable)

Sé conciso y directo. Máximo 150 palabras en total."""

        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Error con Gemini: {e}")
        return "No se pudo generar el análisis."


def enviar_telegram(mensaje):
    """Envía un mensaje por Telegram a todos los destinatarios"""
    for chat_id in TELEGRAM_CHAT_IDS:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": chat_id.strip(),
                "text": mensaje,
                "parse_mode": "HTML"
            }
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                print(f"✅ Mensaje enviado a {chat_id}")
            else:
                print(f"❌ Error enviando a {chat_id}: {response.text}")
        except Exception as e:
            print(f"Error Telegram: {e}")


def generar_y_enviar_informe():
    """Función principal que genera y envía el informe diario"""
    print(f"\n🚀 Iniciando informe diario - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    
    fecha = datetime.now().strftime("%d/%m/%Y")
    informe_completo = f"📊 <b>INFORME DIARIO DE RESEÑAS</b>\n📅 {fecha} - 23:59hs\n"
    informe_completo += "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    locales_procesados = 0
    
    for i, maps_url in enumerate(LOCALES_MAPS_URLS, 1):
        print(f"Procesando local {i}/{len(LOCALES_MAPS_URLS)}...")
        
        # Resolver Place ID
        place_id, nombre_detectado = resolver_place_id(maps_url)
        
        if not place_id:
            informe_completo += f"🏪 <b>Local {i}</b>\n❌ No se pudo acceder al local.\n\n"
            continue
        
        # Obtener info y reseñas
        info = obtener_info_lugar(place_id)
        
        if not info:
            informe_completo += f"🏪 <b>Local {i}</b>\n❌ Error obteniendo datos.\n\n"
            continue
        
        nombre = info.get("name", f"Local {i}")
        rating = info.get("rating", "N/D")
        total_resenas = info.get("user_ratings_total", 0)
        resenas = info.get("reviews", [])
        
        # Analizar con Gemini
        if resenas:
            analisis = analizar_resenas_con_gemini(nombre, rating, total_resenas, resenas)
        else:
            analisis = "No hay reseñas recientes disponibles."
        
        # Armar sección del local
        informe_completo += f"🏪 <b>{nombre}</b>\n"
        informe_completo += f"⭐ Rating: {rating}/5 ({total_resenas} reseñas totales)\n"
        informe_completo += f"{analisis}\n"
        informe_completo += "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        locales_procesados += 1
        time.sleep(1)  # Pausa para no saturar las APIs
    
    informe_completo += f"✅ Informe generado automáticamente\n🤖 Monitor de Reseñas"
    
    # Enviar por Telegram
    enviar_telegram(informe_completo)
    print(f"✅ Informe enviado - {locales_procesados} locales procesados")


def test_conexiones():
    """Prueba que todas las conexiones funcionen"""
    print("🔍 Probando conexiones...")
    
    # Test Telegram
    enviar_telegram("🤖 <b>Monitor de Reseñas activado</b>\n✅ Sistema funcionando correctamente.\nRecibirás el informe diario a las 23:59hs.")
    print("✅ Telegram OK")


# ============================================================
# SCHEDULER - Ejecutar todos los días a las 23:59
# ============================================================
if __name__ == "__main__":
    print("🚀 Monitor de Reseñas iniciando...")
    
    # Probar conexiones al arrancar
    test_conexiones()
    
    # Programar informe diario a las 23:59
    schedule.every().day.at("23:59").do(generar_y_enviar_informe)
    
    print("⏰ Scheduler activo - Informe programado para las 23:59hs")
    print("💡 Para probar ahora, el sistema enviará un mensaje de prueba.")
    
    # Loop principal
    while True:
        schedule.run_pending()
        time.sleep(60)
