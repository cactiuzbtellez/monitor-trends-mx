#!/usr/bin/env python3
"""
fetch_trends.py — v2
Combina pytrends (API real de Google Trends) + RSS para México.
Filtra:
  - Solo últimas 4 semanas por fecha de publicación
  - Por categorías relevantes: Salud, Política, Economía, Seguridad
  - Excluye deporte, entretenimiento, videojuegos

Ejecutar: python scripts/fetch_trends.py
"""

import json, os, re, sys
from datetime import datetime, timezone, timedelta
import feedparser

# ─── Configuración de tiempo ────────────────────────────────────────────────
MAXIMO_DIAS = 30          # descartar tendencias con más de 30 días
MAXIMO_POR_FEED = 50      # items máximos por fuente RSS

# ─── Feeds RSS por categoría Google Trends ──────────────────────────────────
# Google Trends RSS no filtra bien por cat, pero intentamos los feeds
# categorizados y lo combinamos con palabras clave
RSS_FEEDS = [
    # Feed general MX — base de todo
    {"url": "https://trends.google.com/trending/rss?geo=MX",       "label": "General MX"},
    # Feeds de noticias mexicanas de referencia
    {"url": "https://www.eluniversal.com.mx/arc/outboundfeeds/rss/category/nacion/",    "label": "El Universal Nación"},
    {"url": "https://www.eluniversal.com.mx/arc/outboundfeeds/rss/category/finanzas/",  "label": "El Universal Finanzas"},
    {"url": "https://www.jornada.com.mx/rss/politica.xml",                               "label": "La Jornada Política"},
    {"url": "https://www.jornada.com.mx/rss/economia.xml",                               "label": "La Jornada Economía"},
    {"url": "https://www.infobae.com/feeds/rss/salud/",                                  "label": "Infobae Salud"},
    {"url": "https://www.infobae.com/feeds/rss/economia/",                               "label": "Infobae Economía"},
    {"url": "https://www.elfinanciero.com.mx/arc/outboundfeeds/rss/category/economia/", "label": "El Financiero Economía"},
    {"url": "https://www.elfinanciero.com.mx/arc/outboundfeeds/rss/category/politica/", "label": "El Financiero Política"},
    {"url": "https://www.proceso.com.mx/rss/",                                           "label": "Proceso"},
]

# ─── Palabras clave por categoría ───────────────────────────────────────────
CATEGORIAS = {
    "Salud": [
        "cubrebocas", "mascarilla", "pandemia", "epidemia", "brote", "vacuna",
        "covid", "coronavirus", "sars", "influenza", "gripe", "dengue",
        "salud", "hospital", "ssa", "imss", "issste", "secretaria salud",
        "contagio", "enfermedad", "virus", "bacteria", "cuarentena",
        "emergencia sanitaria", "crisis sanitaria", "fallecidos", "defunciones",
        "medicamento", "farmaco", "tratamiento", "clinica", "doctor", "medico",
        "agua potable", "contaminacion agua", "calidad aire", "smog",
    ],
    "Política": [
        "presidente", "presidenta", "claudia sheinbaum", "sheinbaum",
        "congreso", "senado", "camara diputados", "morena", "pan", "pri",
        "prd", "mc", "pvem", "gobierno", "gobernador", "gobernadora",
        "alcalde", "alcaldesa", "elecciones", "reforma", "constitucion",
        "suprema corte", "scjn", "tribunal", "juicio", "ministerio",
        "cancilleria", "secretaria", "secretario", "gabinete", "decreto",
        "ley", "legislacion", "iniciativa", "voto", "partido", "candidato",
        "segob", "sspc", "marina", "ejercito", "sedena", "fuerzas armadas",
        "trump", "relaciones exteriores", "embajada", "diplomatico",
        "oposicion", "diputado", "senador", "cabildo", "municipio",
    ],
    "Economía": [
        "economia", "inflacion", "pib", "peso", "dolar", "tipo de cambio",
        "banxico", "banco mexico", "reservas", "deuda", "deficit",
        "hacienda", "shcp", "sat", "impuestos", "iva", "isr",
        "pemex", "cfe", "energia", "petroleo", "gas", "electricidad",
        "empleo", "desempleo", "salario", "minimo", "inegi",
        "empresa", "inversion", "bolsa", "bmv", "exportaciones",
        "aranceles", "tlcan", "tmec", "recesion", "crisis economica",
        "finanzas", "presupuesto", "egresos", "nearshoring", "manufactura",
        "comercio", "pension", "bienestar", "subsidio", "apoyo",
        "devaluacion", "bono", "tasa interes", "credito", "bancario",
        "embargo", "sello sat", "contribuyentes", "fiscal", "recaudacion",
        "wells fargo", "vix", "mercados", "acciones", "fondo",
        "remesas", "dolarizacion", "migrante dinero",
    ],
    "Seguridad": [
        "violencia", "crimen", "delito", "homicidio", "secuestro", "extorsion",
        "cartel", "narco", "narcotrafico", "drogas", "fentanilo",
        "policia", "guardia nacional", "gn", "fiscal", "fiscalia",
        "asesinato", "balacera", "enfrentamiento", "operativo",
        "feminicidio", "desaparecidos", "trata", "migrantes",
        "robo", "asalto", "detenido", "capturado", "sentenciado",
        "prision", "penal", "recluso", "preso", "liberado",
    ],
    "Ambiente": [
        "rio panuco", "rio", "inundacion", "sequia", "terremoto", "sismo",
        "erupcion", "volcan", "popocatepetl", "popo",
        "clima", "lluvia", "tormenta", "huracan", "ciclón", "ciclon",
        "contaminacion", "medio ambiente", "ecologia", "deforestacion",
        "incendio forestal", "agua", "escasez", "nivel mar",
    ],
}

# Palabras clave para EXCLUIR (deporte, entretenimiento, videojuegos)
EXCLUSIONES = [
    "nba", "nfl", "mlb", "nhl", "liga mx", "futbol", "soccer", "tenis",
    "formula 1", "f1", "moto gp", "boxeo", "ufc", "wwe",
    "mavericks", "nuggets", "lakers", "celtics", "bulls", "spurs",
    "piston", "hawks", "warriors", "heat", "mavs", "suns",
    "gta", "videojuego", "nintendo", "playstation", "xbox", "steam",
    "minecraft", "fortnite", "valorant", "lol", "esports",
    "pelicula", "serie netflix", "disney", "hbo", "amazon prime",
    "cancion", "musica pop", "reggaeton", "banda", "concierto",
    "meme", "viral tiktok", "influencer", "youtuber",
    "receta", "cocina", "gastronomia", "restaurante", "chef",
    "moda", "ropa", "belleza", "maquillaje", "skincare",
    "horoscopo", "zodiaco", "tarot",
]

TODAS_KEYWORDS = {kw for lista in CATEGORIAS.values() for kw in lista}


def texto_limpio(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def detectar_categoria(titulo: str, desc: str = "") -> str | None:
    t = f"{titulo} {desc}".lower()
    # Primero revisar exclusiones
    for excl in EXCLUSIONES:
        if excl in t:
            return None
    # Luego detectar categoría
    for cat, keywords in CATEGORIAS.items():
        if any(kw in t for kw in keywords):
            return cat
    return None


def parsear_fecha(entry) -> tuple[datetime | None, str]:
    """Devuelve (datetime_utc, string_formateado)."""
    try:
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            return dt, dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        pass
    now = datetime.now(timezone.utc)
    return now, now.strftime("%d/%m/%Y %H:%M")


def fetch_pytrends() -> list[dict]:
    """Usa pytrends para obtener trending real de México."""
    try:
        from pytrends.request import TrendReq
        pt = TrendReq(hl='es-MX', tz=360, timeout=(10, 25))
        df = pt.realtime_trending_searches(pn='MX', cat='all', count=100)
        
        items = []
        now = datetime.now(timezone.utc)
        corte = now - timedelta(days=MAXIMO_DIAS)
        
        for _, row in df.iterrows():
            titulo = str(row.get('title', '') or '').strip()
            desc   = str(row.get('description', '') or '').strip()
            link   = str(row.get('shareUrl', '') or '').strip()
            imagen = str(row.get('image', '') or '').strip()
            
            # Fecha (pytrends a veces trae pubDate)
            pub_str = str(row.get('pubDate', '') or '')
            fecha_dt = now
            fecha_fmt = now.strftime("%d/%m/%Y %H:%M")
            if pub_str:
                try:
                    from email.utils import parsedate_to_datetime
                    fecha_dt = parsedate_to_datetime(pub_str).astimezone(timezone.utc)
                    fecha_fmt = fecha_dt.strftime("%d/%m/%Y %H:%M")
                except Exception:
                    pass
            
            if fecha_dt < corte:
                continue
            
            cat = detectar_categoria(titulo, desc)
            if cat is None:
                continue
            
            items.append({
                "titulo": titulo,
                "descripcion": texto_limpio(desc)[:240],
                "trafico": "N/D",
                "fecha": fecha_fmt,
                "fecha_dt": fecha_dt.isoformat(),
                "link": link,
                "imagen": imagen,
                "fuente": "Google Trends (pytrends)",
                "categoria": cat,
            })
        
        print(f"  pytrends → {len(items)} tendencias relevantes")
        return items
    except Exception as e:
        print(f"  pytrends ERROR: {e}")
        return []


def fetch_rss() -> list[dict]:
    """Parsea múltiples feeds RSS y filtra por tiempo y categoría."""
    items = []
    now = datetime.now(timezone.utc)
    corte = now - timedelta(days=MAXIMO_DIAS)
    vistos = set()

    for cfg in RSS_FEEDS:
        print(f"  → {cfg['label']}")
        try:
            d = feedparser.parse(cfg["url"])
            n_validos = 0
            for entry in d.entries[:MAXIMO_POR_FEED]:
                titulo = texto_limpio(entry.get("title", ""))
                if not titulo or titulo.lower() in vistos:
                    continue
                
                desc   = texto_limpio(entry.get("summary", "") or "")
                fecha_dt, fecha_fmt = parsear_fecha(entry)
                
                # Filtro de tiempo
                if fecha_dt < corte:
                    continue
                
                # Categoría
                cat = detectar_categoria(titulo, desc)
                if cat is None:
                    continue
                
                # Tráfico (solo en RSS de Google Trends)
                trafico = getattr(entry, "ht_approx_traffic", "") or ""
                trafico = str(trafico).strip()
                imagen  = getattr(entry, "ht_picture", "") or ""
                link    = entry.get("link", "") or ""
                
                vistos.add(titulo.lower())
                n_validos += 1
                items.append({
                    "titulo":      titulo,
                    "descripcion": desc[:240],
                    "trafico":     trafico if trafico else "—",
                    "fecha":       fecha_fmt,
                    "fecha_dt":    fecha_dt.isoformat(),
                    "link":        link,
                    "imagen":      imagen,
                    "fuente":      cfg["label"],
                    "categoria":   cat,
                })
            print(f"     ✓ {n_validos} artículos relevantes (últimos {MAXIMO_DIAS} días)")
        except Exception as e:
            print(f"     ✗ ERROR: {e}")
    
    return items


def main():
    print("\n═══════════════════════════════════════")
    print("  Monitor Tendencias MX — fetch v2")
    print("═══════════════════════════════════════\n")
    
    # 1. pytrends (fuente primaria)
    print("── pytrends ──")
    items_pytrends = fetch_pytrends()
    
    # 2. RSS (fuente complementaria)
    print("\n── RSS feeds ──")
    items_rss = fetch_rss()
    
    # Combinar y deduplicar por título
    todos = items_pytrends + items_rss
    vistos_titulos: set[str] = set()
    unicos = []
    for item in todos:
        clave = item["titulo"].lower()[:80]
        if clave not in vistos_titulos:
            vistos_titulos.add(clave)
            unicos.append(item)
    
    # Ordenar por fecha descendente
    unicos.sort(key=lambda x: x.get("fecha_dt", ""), reverse=True)
    
    # Stats por categoría
    stats: dict[str, int] = {}
    for item in unicos:
        cat = item["categoria"]
        stats[cat] = stats.get(cat, 0) + 1
    
    salida = {
        "actualizado":      datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC"),
        "periodo":          f"Últimos {MAXIMO_DIAS} días",
        "total":            len(unicos),
        "stats_categorias": stats,
        "trends":           unicos,
    }
    
    os.makedirs("data", exist_ok=True)
    with open("data/trends.json", "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ trends.json → {len(unicos)} tendencias (últimos {MAXIMO_DIAS} días)")
    for cat, n in sorted(stats.items(), key=lambda x: -x[1]):
        print(f"   {cat:12}: {n}")


if __name__ == "__main__":
    main()
