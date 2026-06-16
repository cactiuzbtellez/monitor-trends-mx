#!/usr/bin/env python3
"""
fetch_trends.py — v3 · Google Trends MX con categorías reales
Lee múltiples RSS feeds de Google Trends usando los IDs de categoría
que usa el propio sitio web (cat=3, cat=45, etc.).
Sin medios externos. Solo Google Trends.
"""

import json, os, re
from datetime import datetime, timezone, timedelta
import feedparser

# ─── Configuración ────────────────────────────────────────────────────────────
MAXIMO_DIAS  = 30
MAX_POR_FEED = 50

# ─── Feeds RSS con IDs de categoría reales de Google Trends ─────────────────
# IDs extraídos de la URL del sitio: trends.google.com/trending?geo=MX&category=N
FEEDS = [
    # Categorías de interés principal
    {"cat_id": 3,    "nombre": "Negocios y Finanzas",   "categoria": "Economía"},
    {"cat_id": 396,  "nombre": "Política",               "categoria": "Política"},
    {"cat_id": 45,   "nombre": "Salud",                  "categoria": "Salud"},
    {"cat_id": 174,  "nombre": "Ciencia",                "categoria": "Ciencia"},
    {"cat_id": 1166, "nombre": "Clima y Ambiente",       "categoria": "Ambiente"},
    {"cat_id": 16,   "nombre": "Noticias",               "categoria": "General"},
    # Feed general — para capturar lo que no entra en las categorías anteriores
    # y luego filtrar manualmente
    {"cat_id": None, "nombre": "General MX",             "categoria": None},
]

# ─── Palabras para clasificar el feed general ─────────────────────────────────
KEYWORDS_EXTRA = {
    "Economía":  ["inflacion","peso","dolar","banxico","sat","pemex","cfe","hacienda",
                  "shcp","aranceles","tmec","tlcan","recession","deuda","embargo",
                  "pension","bienestar","inversion","empleo","desempleo","salario",
                  "manufactura","exportaciones","nearshoring","remesas","impuesto"],
    "Política":  ["presidente","presidenta","sheinbaum","congreso","senado","diputados",
                  "morena","pan","pri","prd","gobierno","gobernador","reforma",
                  "constitucion","scjn","decreto","ley","partido","elecciones","sedena",
                  "marina","ejercito","guardia nacional","trump","diplomacia"],
    "Salud":     ["covid","coronavirus","pandemia","epidemia","vacuna","dengue",
                  "influenza","virus","hospital","imss","issste","cubrebocas",
                  "contagio","enfermedad","cuarentena","medicamento","clinica"],
    "Seguridad": ["violencia","homicidio","secuestro","cartel","narco","drogas",
                  "feminicidio","desaparecidos","balacera","policia","fiscalia",
                  "detenido","robo","asalto","extorsion","fentanilo"],
    "Ambiente":  ["inundacion","sequia","sismo","terremoto","huracan","ciclon",
                  "contaminacion","incendio forestal","popocatepetl","agua potable",
                  "escasez agua","tormenta","deforestacion"],
}

# Términos a EXCLUIR del feed general (ya están en sus propios feeds categorizados)
EXCLUSIONES_GENERAL = [
    "nba","nfl","mlb","liga mx","futbol","soccer","tenis","formula 1","boxeo","ufc",
    "mavericks","nuggets","lakers","celtics","pistons","hawks","warriors","knicks",
    "gta","videojuego","nintendo","playstation","xbox","minecraft","fortnite",
    "pelicula","serie","netflix","disney","hbo","concierto","musica","cantante",
    "receta","cocina","gastronomia","moda","belleza","maquillaje","horoscopo",
    "mundial",  # quitar esta línea si quieres incluir el Mundial 2026
]


# ─── Helpers ──────────────────────────────────────────────────────────────────
def limpiar(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def parsear_fecha(entry) -> tuple[datetime, str]:
    try:
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            return dt, dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        pass
    now = datetime.now(timezone.utc)
    return now, now.strftime("%d/%m/%Y %H:%M")

def clasificar_general(titulo: str) -> str | None:
    """Para el feed general: excluye entretenimiento y clasifica por keywords."""
    t = titulo.lower()
    for excl in EXCLUSIONES_GENERAL:
        if excl in t:
            return None
    for cat, keywords in KEYWORDS_EXTRA.items():
        if any(kw in t for kw in keywords):
            return cat
    return None  # Ni excluido ni clasificado → descartar del general


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    now   = datetime.now(timezone.utc)
    corte = now - timedelta(days=MAXIMO_DIAS)
    
    todos    = []
    vistos   = set()       # deduplicar por título
    stats    = {}

    print(f"\n═══ Monitor Tendencias MX · {now.strftime('%d/%m/%Y %H:%M UTC')} ═══\n")

    for feed_cfg in FEEDS:
        cat_id   = feed_cfg["cat_id"]
        nombre   = feed_cfg["nombre"]
        cat_fija = feed_cfg["categoria"]   # None = feed general, clasificar por keywords

        if cat_id is not None:
            url = f"https://trends.google.com/trending/rss?geo=MX&cat={cat_id}"
        else:
            url = "https://trends.google.com/trending/rss?geo=MX"

        print(f"→ [{nombre}]  {url}")
        
        try:
            d = feedparser.parse(url)
            n_ok = 0

            for entry in d.entries[:MAX_POR_FEED]:
                titulo = limpiar(entry.get("title", ""))
                if not titulo:
                    continue

                # Deduplicar
                clave = titulo.lower()
                if clave in vistos:
                    continue

                # Filtro de tiempo
                fecha_dt, fecha_fmt = parsear_fecha(entry)
                if fecha_dt < corte:
                    continue

                # Determinar categoría
                if cat_fija is not None:
                    # Feed categorizado → categoría fija
                    categoria = cat_fija
                else:
                    # Feed general → clasificar por keywords o descartar
                    categoria = clasificar_general(titulo)
                    if categoria is None:
                        continue

                trafico = str(getattr(entry, "ht_approx_traffic", "") or "").strip()
                imagen  = str(getattr(entry, "ht_picture",        "") or "").strip()
                link    = (f"https://trends.google.com/trends/explore"
                           f"?geo=MX&q={titulo.replace(' ', '+')}")

                vistos.add(clave)
                n_ok += 1
                todos.append({
                    "titulo":    titulo,
                    "trafico":   trafico if trafico else "—",
                    "fecha":     fecha_fmt,
                    "fecha_dt":  fecha_dt.isoformat(),
                    "imagen":    imagen,
                    "link":      link,
                    "categoria": categoria,
                    "feed":      nombre,
                })
                stats[categoria] = stats.get(categoria, 0) + 1
                print(f"   ✓ [{categoria}] {titulo}  ({trafico})")

            print(f"   → {n_ok} tendencias añadidas\n")

        except Exception as e:
            print(f"   ✗ ERROR: {e}\n")

    # Ordenar por fecha descendente
    todos.sort(key=lambda x: x.get("fecha_dt", ""), reverse=True)

    salida = {
        "actualizado":      now.strftime("%d/%m/%Y %H:%M UTC"),
        "periodo":          f"Últimos {MAXIMO_DIAS} días · Google Trends MX",
        "total":            len(todos),
        "stats_categorias": stats,
        "trends":           todos,
    }

    os.makedirs("data", exist_ok=True)
    with open("data/trends.json", "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)

    print(f"\n✅ trends.json → {len(todos)} tendencias relevantes")
    for cat, n in sorted(stats.items(), key=lambda x: -x[1]):
        print(f"   {cat:15}: {n}")


if __name__ == "__main__":
    main()
