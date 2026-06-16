#!/usr/bin/env python3
"""
fetch_trends.py
Descarga Google Trends RSS para México, filtra por temas relevantes
(salud, política, economía, seguridad) y genera data/trends.json
"""

import json
import re
import feedparser
from datetime import datetime, timezone

# ─── Fuentes RSS ──────────────────────────────────────────────────────────────
FEEDS = [
    {
        "nombre": "Google Trends MX — General",
        "url": "https://trends.google.com/trending/rss?geo=MX",
        "geo": "MX",
    },
]

# ─── Palabras clave para categorización ───────────────────────────────────────
CATEGORIAS = {
    "Salud": [
        "cubrebocas", "mascarilla", "pandemia", "epidemia", "brote", "vacuna",
        "covid", "coronavirus", "sars", "influenza", "gripe", "dengue",
        "salud", "hospital", "ssa", "imss", "issste", "secretaria salud",
        "contagio", "enfermedad", "virus", "bacteria", "cuarentena",
        "emergencia sanitaria", "crisis sanitaria", "fallecidos", "defunciones",
        "medicamento", "farmaco", "tratamiento", "clinica", "doctor", "medico",
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
    ],
    "Economía": [
        "economia", "inflacion", "pib", "peso", "dolar", "tipo de cambio",
        "banxico", "banco mexico", "reservas", "deuda", "deficit",
        "hacienda", "shcp", "sat", "impuestos", "iva", "isr",
        "pemex", "cfe", "energia", "petroleo", "gas", "electricidad",
        "empleo", "desempleo", "salario", "minimo", "inegi",
        "paro", "empresa", "inversión", "inversion", "bolsa", "bmv",
        "exportaciones", "importaciones", "aranceles", "tlcan", "tmec",
        "recesion", "crisis economica", "finanzas", "presupuesto", "egresos",
        "nearshoring", "industria", "manufactura", "comercio",
    ],
    "Seguridad": [
        "violencia", "crimen", "delito", "homicidio", "secuestro", "extorsion",
        "cartel", "narco", "narcotrafico", "drogas", "fentanilo",
        "policia", "guardia nacional", "gn", "fiscal", "fiscalia",
        "asesinato", "balacera", "enfrentamiento", "operativo",
        "feminicidio", "desaparecidos", "trata", "migrantes",
    ],
}

# Conjunto plano para filtrado rápido
TODAS_KEYWORDS = {kw for lista in CATEGORIAS.values() for kw in lista}


def detectar_categoria(texto: str) -> str | None:
    """Devuelve la primera categoría que coincide, o None si no aplica."""
    texto_lower = texto.lower()
    for cat, keywords in CATEGORIAS.items():
        if any(kw in texto_lower for kw in keywords):
            return cat
    return None


def es_relevante(titulo: str, descripcion: str = "") -> bool:
    texto = f"{titulo} {descripcion}".lower()
    return any(kw in texto for kw in TODAS_KEYWORDS)


def parsear_fecha(entry) -> str:
    try:
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        pass
    return datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")


def limpiar(texto: str) -> str:
    texto = re.sub(r"<[^>]+>", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto[:280] if len(texto) > 280 else texto


def fetch_trends():
    todos = []
    sin_filtro = []   # backup: todos los trending sin filtrar

    for feed_cfg in FEEDS:
        print(f"\n→ Descargando: {feed_cfg['url']}")
        try:
            d = feedparser.parse(feed_cfg["url"])
            print(f"  Entradas encontradas: {len(d.entries)}")

            for entry in d.entries:
                titulo = limpiar(entry.get("title", ""))
                descripcion = limpiar(entry.get("summary", "") or "")
                trafico_raw = getattr(entry, "ht_approx_traffic", "N/D")

                # Datos de noticias relacionadas
                noticias_rel = []
                for attr in dir(entry):
                    if attr.startswith("ht_news_item"):
                        pass  # feedparser pone cada campo por separado

                # Intentar extraer noticias del namespace ht
                # feedparser las pone en entry.tags o en campos especiales
                news_titles = getattr(entry, "ht_news_item_title", [])
                news_urls   = getattr(entry, "ht_news_item_url", [])
                news_sources= getattr(entry, "ht_news_item_source", [])

                # Imagen principal del trend
                imagen = getattr(entry, "ht_picture", "") or ""

                categoria = detectar_categoria(titulo)

                item = {
                    "titulo": titulo,
                    "trafico": str(trafico_raw).replace("+", "+").strip(),
                    "fecha": parsear_fecha(entry),
                    "link": entry.get("link", ""),
                    "imagen": imagen,
                    "categoria": categoria or "General",
                    "relevante": categoria is not None,
                    "geo": feed_cfg["geo"],
                }

                sin_filtro.append(item)
                if categoria:
                    todos.append(item)

        except Exception as e:
            print(f"  ✗ ERROR: {e}")

    # Si no hay trends filtrados (el RSS puede variar), incluir todos
    if not todos:
        todos = sin_filtro
        print("  ⚠ Sin tendencias filtradas; usando todos los trends disponibles")

    # Estadísticas por categoría
    stats = {}
    for item in todos:
        cat = item["categoria"]
        stats[cat] = stats.get(cat, 0) + 1

    salida = {
        "actualizado": datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC"),
        "total": len(todos),
        "total_sin_filtro": len(sin_filtro),
        "stats_categorias": stats,
        "trends": todos,
    }

    import os
    os.makedirs("data", exist_ok=True)
    with open("data/trends.json", "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)

    print(f"\n✅ trends.json → {len(todos)} tendencias ({len(sin_filtro)} total)")
    for cat, n in stats.items():
        print(f"   {cat}: {n}")


if __name__ == "__main__":
    fetch_trends()
