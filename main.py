import os,requests
from datetime import datetime

GOOGLE_PLACES_API_KEY=os.environ.get("GOOGLE_PLACES_API_KEY","")
GEMINI_API_KEY=os.environ.get("GEMINI_API_KEY","")
TELEGRAM_BOT_TOKEN=os.environ.get("TELEGRAM_BOT_TOKEN","")
TELEGRAM_CHAT_IDS=os.environ.get("TELEGRAM_CHAT_IDS","").split(",")

LOCALES=[("-34.6038802","-58.4109897","Distrito Buenos Aires - Abasto"),("-34.598775","-58.375071","Distrito Buenos Aires - Galerias"),("-34.6185106","-58.4373451","Distrito Buenos Aires - Caballito"),("-32.9014375","-68.7992918","Distrito Mza"),("-34.5464842","-58.4878536","Distrito Buenos Aires - Dot")]

def buscar_place_id(lat,lng):
 params={"input":"Distrito","inputtype":"textquery","locationbias":f"circle:50@{lat},{lng}","fields":"place_id","key":GOOGLE_PLACES_API_KEY}
 r=requests.get("https://maps.googleapis.com/maps/api/place/findplacefromtext/json",params=params,timeout=10)
 d=r.json()
 return d["candidates"][0]["place_id"] if d.get("candidates") else None

def obtener_info(place_id):
 params={"place_id":place_id,"fields":"name,rating,user_ratings_total,reviews","language":"es","reviews_sort":"newest","key":GOOGLE_PLACES_API_KEY}
 r=requests.get("https://maps.googleapis.com/maps/api/place/details/json",params=params,timeout=10)
 d=r.json()
 return d["result"] if d.get("status")=="OK" else None

def analizar(nombre,rating,total,resenas):
 texto="\n".join([f"- {r.get('author_name')} ({r.get('rating')} estrellas): {r.get('text','')}" for r in resenas])
 prompt=f"Analiza resenas de {nombre} rating {rating}/5 total {total}. Resenas: {texto}. Responde en espanol con emojis exactamente asi: PUNTOS FUERTES (maximo 3), PUNTOS DEBILES (maximo 3), RECOMENDACIONES (maximo 2), TENDENCIA (1 frase). Maximo 150 palabras."
 payload={"contents":[{"parts":[{"text":prompt}]}]}
 url=f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent?key={GEMINI_API_KEY}"
 r=requests.post(url,json=payload,timeout=30)
 d=r.json()
 print(f"Gemini: {r.status_code}")
 if "candidates" in d:
  return d["candidates"][0]["content"]["parts"][0]["text"]
 print(f"Gemini error: {d}")
 return "Sin analisis disponible."

def enviar(msg):
 for chat_id in TELEGRAM_CHAT_IDS:
  requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",json={"chat_id":chat_id.strip(),"text":msg},timeout=10)
  print(f"Enviado a {chat_id}")

def main():
 fecha=datetime.now().strftime("%d/%m/%Y")
 informe=f"📊 INFORME DIARIO DE RESEÑAS\n📅 {fecha} - 23:59hs\n\n"
 for lat,lng,nombre_default in LOCALES:
  print(f"Procesando {nombre_default}...")
  place_id=buscar_place_id(lat,lng)
  if not place_id:
   informe+=f"🏪 {nombre_default}\n❌ No se encontro el local.\n\n"
   continue
  info=obtener_info(place_id)
  if not info:
   informe+=f"🏪 {nombre_default}\n❌ Error obteniendo datos.\n\n"
   continue
  nombre=info.get("name",nombre_default)
  rating=info.get("rating","N/D")
  total=info.get("user_ratings_total",0)
  resenas=info.get("reviews",[])
  analisis=analizar(nombre,rating,total,resenas) if resenas else "Sin reseñas recientes."
  informe+=f"🏪 {nombre_default}\n⭐ {rating}/5 ({total} reseñas totales)\n{analisis}\n\n"
 informe+="🤖 Monitor Automatico de Reseñas"
 enviar(informe)
 print("Informe enviado")

main()
