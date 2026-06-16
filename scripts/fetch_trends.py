#!/usr/bin/env python3
"""
fetch_trends.py — simple
Lee los RSS de Google Trends MX y guarda TODO lo que tenga
menos de 30 días. Sin filtros de categoría, sin keywords, sin IA.
"""

import json, os, re, requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

MAXIMO_DIAS = 30
MAX_ITEMS   = 50
NS = {"ht": "https://trends.google.com/trending/rss"}

FEEDS = [
    "https://trends.google.com/trending/rss?geo=MX",
    "https://trends.google.com/trending/rss?geo=MX&cat=3",
    "https://trends.google.com/trending/rss?geo=MX&cat=396",
    "https://trends.google.com/trending/rss?geo=MX&cat=45",
    "https://trends.google.com/trending/rss?geo=MX&cat=16",
    "https://trends.google.com/trending/rss?geo=MX&cat=174",
    "https://trends.google.com/trending/rss?geo=MX&cat=1166",
]

def limpiar(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    return re.sub(r"\s+", " ", s).strip()

def parsear_fecha(pub_str):
    try:
        dt = parsedate_to_datetime(pub_str).astimezone(timezone.utc)
        return dt, dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        now = datetime.now(timezone.utc)
        return now, now.strftime("%d/%m/%Y %H:%M")

def fetch_feed(url):
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        r.raise_for_status()
        root = ET.fromstring(r.content)
    except Exception as e:
        print(f"  ✗ {url} → {e}")
        return []

    now   = datetime.now(timezone.utc)
    corte = now - timedelta(days=MAXIMO_DIAS)
    items = []

    for item in list(root.findall(".//item"))[:MAX_ITEMS]:
        titulo  = limpiar(item.findtext("title", ""))
        trafico = limpiar(item.findtext("ht:approx_traffic", "", NS))
        imagen  = limpiar(item.findtext("ht:picture", "", NS))
        pub_str = limpiar(item.findtext("pubDate", ""))

        news = [limpiar(n.findtext("ht:news_item_title", "", NS))
                for n in item.findall("ht:news_item", NS)]
        news = [t for t in news if t]

        fecha_dt, fecha_fmt = parsear_fecha(pub_str)
        if fecha_dt < corte or not titulo:
            continue

        items.append({
            "titulo":      titulo,
            "descripcion": news[0][:240] if news else "",
            "trafico":     trafico or "—",
            "fecha":       fecha_fmt,
            "fecha_dt":    fecha_dt.isoformat(),
            "imagen":      imagen,
            "link":        f"https://trends.google.com/trending?geo=MX&q={titulo.replace(' ', '+')}",
        })

    return items

def main():
    now = datetime.now(timezone.utc)
    print(f"\n→ {now.strftime('%d/%m/%Y %H:%M UTC')}")

    todos  = []
    vistos = set()

    for url in FEEDS:
        items = fetch_feed(url)
        n = 0
        for item in items:
            clave = item["titulo"].lower()
            if clave in vistos:
                continue
            vistos.add(clave)
            todos.append(item)
            n += 1
            print(f"  ✓ {item['titulo']}  ({item['trafico']})")
        print(f"  [{url.split('cat=')[-1] if 'cat=' in url else 'general'}] → {n} trends\n")

    def trafico_a_numero(t):
        """Convierte '200+', '2000+', '20K+', '200K+' a entero para ordenar."""
        s = t.get("trafico", "0").replace("+", "").replace(",", "").strip().upper()
        try:
            if s.endswith("K"):
                return int(float(s[:-1]) * 1_000)
            return int(s)
        except Exception:
            return 0

    todos.sort(key=trafico_a_numero, reverse=True)

    salida = {
        "actualizado": now.strftime("%d/%m/%Y %H:%M UTC"),
        "periodo":     f"Últimos {MAXIMO_DIAS} días · Google Trends MX",
        "total":       len(todos),
        "trends":      todos,
    }

    os.makedirs("data", exist_ok=True)
    with open("data/trends.json", "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)

    print(f"✅ trends.json → {len(todos)} tendencias")

if __name__ == "__main__":
    main()
