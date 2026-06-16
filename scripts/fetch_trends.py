#!/usr/bin/env python3
"""
fetch_trends.py — Google Trends MX únicamente
Lee el RSS oficial de Google Trends México, filtra por palabras clave
relevantes (salud, política, economía, seguridad, ambiente) y descarta
entretenimiento, deportes y videojuegos.
"""

import json, os, re
from datetime import datetime, timezone, timedelta
import feedparser

# ─── Configuración ────────────────────────────────────────────────────────────
MAXIMO_DIAS   = 30     # descartar tendencias con más de 30 días
MAXIMO_ITEMS  = 50     # máximo de items a leer del RSS

RSS_URL = "https://trends.google.com/trending/rss?geo=MX"

# ─── Palabras clave por categoría ─────────────────────────────────────────────
CATEGORIAS = {
    "Salud": [
        "cubrebocas", "mascarilla", "pandemia", "epidemia", "brote", "vacuna",
        "covid", "coronavirus", "influenza", "gripe", "dengue", "virus",
        "salud", "hospital", "imss", "issste", "ssa", "secretaria salud",
        "contagio", "enfermedad", "cuarentena", "emergencia sanitaria",
        "fallecidos", "defunciones", "medicamento", "tratamiento", "clinica",
        "agua potable", "contaminacion agua",
    ],
    "Política": [
        "presidente", "presidenta", "sheinbaum", "claudia sheinbaum",
        "congreso", "senado", "diputados", "morena", "pan", "pri", "prd",
        "gobierno", "gobernador", "reforma", "constitucion", "scjn",
        "tribunal", "decreto", "ley", "partido", "elecciones", "candidato",
        "secretaria", "secretario", "gabinete", "cancilleria", "embajada",
        "sedena", "marina", "ejercito", "guardia nacional", "segob",
        "trump", "relaciones exteriores", "diplomacia",
    ],
    "Economía": [
        "economia", "inflacion", "pib", "peso", "dolar", "tipo de cambio",
        "banxico", "banco mexico", "deuda", "deficit", "hacienda", "shcp",
        "sat", "impuestos", "pemex", "cfe", "petroleo", "gas",
        "empleo", "desempleo", "salario", "minimo", "inegi",
        "inversion", "bolsa", "bmv", "aranceles", "tmec", "tlcan",
        "pension", "bienestar", "subsidio", "presupuesto", "remesas",
        "embargo", "contribuyentes", "fiscal", "recaudacion",
        "nearshoring", "manufactura", "exportaciones", "importaciones",
        "wells fargo", "vix", "mercados", "tasa interes", "credito",
    ],
    "Seguridad": [
        "violencia", "crimen", "homicidio", "secuestro", "extorsion",
        "cartel", "narco", "narcotrafico", "drogas", "fentanilo",
        "policia", "fiscalia", "balacera", "enfrentamiento", "operativo",
        "feminicidio", "desaparecidos", "trata", "robo", "asalto",
        "detenido", "capturado", "prision", "preso",
    ],
    "Ambiente": [
        "rio panuco", "inundacion", "sequia", "terremoto", "sismo",
        "volcan", "popocatepetl", "popo", "tormenta", "huracan", "ciclon",
        "contaminacion", "medio ambiente", "deforestacion",
        "incendio forestal", "escasez agua", "nivel mar", "clima extremo",
    ],
}

# Exclusiones explícitas (deportes, entretenimiento, videojuegos)
EXCLUSIONES = [
    "nba", "nfl", "mlb", "nhl", "liga mx", "futbol", "soccer", "tenis",
    "formula 1", "f1", "moto gp", "boxeo", "ufc", "wwe", "champions",
    "mavericks", "nuggets", "lakers", "celtics", "bulls", "spurs",
    "pistons", "hawks", "warriors", "heat", "mavs", "suns", "knicks",
    "gta", "videojuego", "nintendo", "playstation", "xbox", "steam",
    "minecraft", "fortnite", "valorant", "esports",
    "pelicula", "serie", "netflix", "disney", "hbo", "amazon prime",
    "concierto", "musica", "banda", "cantante", "album",
    "meme", "tiktok", "influencer", "youtuber",
    "receta", "cocina", "gastronomia", "restaurante",
    "moda", "ropa", "belleza", "maquillaje",
    "horoscopo", "zodiaco", "tarot",
    "mundial",   # <- quitar si quieres incluir el Mundial 2026
]

TODAS_KEYWORDS = {kw for lista in CATEGORIAS.values() for kw in lista}


# ─── Helpers ──────────────────────────────────────────────────────────────────
def limpiar(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def detectar_categoria(titulo: str) -> str | None:
    t = titulo.lower()
    for excl in EXCLUSIONES:
        if excl in t:
            return None
    for cat, keywords in CATEGORIAS.items():
        if any(kw in t for kw in keywords):
            return cat
    return None


def parsear_fecha(entry) -> tuple[datetime, str]:
    try:
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            return dt, dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        pass
    now = datetime.now(timezone.utc)
    return now, now.strftime("%d/%m/%Y %H:%M")


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    print(f"\n→ Leyendo RSS: {RSS_URL}")
    d = feedparser.parse(RSS_URL)
    print(f"  Entradas en RSS: {len(d.entries)}")

    now    = datetime.now(timezone.utc)
    corte  = now - timedelta(days=MAXIMO_DIAS)
    trends = []
    stats  = {}

    for entry in d.entries[:MAXIMO_ITEMS]:
        titulo = limpiar(entry.get("title", ""))
        if not titulo:
            continue

        # Filtro de tiempo
        fecha_dt, fecha_fmt = parsear_fecha(entry)
        if fecha_dt < corte:
            print(f"  ⏭ Descartado por antigüedad: {titulo}")
            continue

        # Filtro de categoría
        cat = detectar_categoria(titulo)
        if cat is None:
            print(f"  ✗ Sin categoría / excluido: {titulo}")
            continue

        trafico = str(getattr(entry, "ht_approx_traffic", "") or "").strip()
        imagen  = str(getattr(entry, "ht_picture",        "") or "").strip()

        trends.append({
            "titulo":   titulo,
            "trafico":  trafico if trafico else "—",
            "fecha":    fecha_fmt,
            "fecha_dt": fecha_dt.isoformat(),
            "imagen":   imagen,
            "link":     f"https://trends.google.com/trends/explore?geo=MX&q={titulo.replace(' ', '+')}",
            "categoria": cat,
        })
        stats[cat] = stats.get(cat, 0) + 1
        print(f"  ✓ [{cat}] {titulo} ({trafico})")

    salida = {
        "actualizado":      now.strftime("%d/%m/%Y %H:%M UTC"),
        "periodo":          f"Últimos {MAXIMO_DIAS} días",
        "total":            len(trends),
        "stats_categorias": stats,
        "trends":           trends,
    }

    os.makedirs("data", exist_ok=True)
    with open("data/trends.json", "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)

    print(f"\n✅ trends.json → {len(trends)} tendencias relevantes")
    for cat, n in sorted(stats.items(), key=lambda x: -x[1]):
        print(f"   {cat}: {n}")


if __name__ == "__main__":
    main()
