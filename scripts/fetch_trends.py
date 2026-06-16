#!/usr/bin/env python3
"""
fetch_trends.py — v6
Fuente principal: CSV de Google Trends (Export) — todos los trends con volumen real.
Fuente secundaria: RSS — para completar con imagen y descripción.
"""

import csv, io, json, os, re, requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

MAXIMO_DIAS = 30
NS = {"ht": "https://trends.google.com/trending/rss"}

HEADERS = {
    "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "es-MX,es;q=0.9",
    "Referer":         "https://trends.google.com/trending?geo=MX",
}

# CSV con TODOS los trends ordenados por volumen — mismo botón "Export" del sitio
CSV_URLS = [
    "https://trends.google.com/trending/export?geo=MX&hours=24&hl=es-MX",   # últimas 24h
    "https://trends.google.com/trending/export?geo=MX&hours=168&hl=es-MX",  # última semana
]

# RSS para obtener imágenes y descripciones
RSS_URLS = [
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


def trafico_a_numero(trafico_str):
    s = str(trafico_str).replace("+", "").replace(",", "").strip().upper()
    try:
        if s.endswith("K"):
            return int(float(s[:-1]) * 1_000)
        if s.endswith("M"):
            return int(float(s[:-1]) * 1_000_000)
        return int(s)
    except Exception:
        return 0


def fetch_csv():
    """
    Descarga el CSV de Export de Google Trends.
    Columnas típicas: Rank, Trend, Volume, Started, Status, Breakdown
    """
    ahora = datetime.now(timezone.utc)
    corte = ahora - timedelta(days=MAXIMO_DIAS)
    todos = []
    vistos = set()

    for url in CSV_URLS:
        print(f"→ CSV: {url}")
        try:
            r = requests.get(url, headers=HEADERS, timeout=20, allow_redirects=False)
            # Si hay redirección, seguirla manualmente para corregir /trends/trending/ → /trending/
            if r.status_code in (301, 302, 303, 307, 308):
                location = r.headers.get("Location", "")
                location = location.replace("/trends/trending/", "/trending/")
                print(f"   Redirigido a: {location}")
                r = requests.get(location, headers=HEADERS, timeout=20)
            r.raise_for_status()

            # Detectar encoding
            content = r.content.decode("utf-8-sig", errors="replace")
            reader  = csv.DictReader(io.StringIO(content))

            n = 0
            for row in reader:
                # Normalizar nombres de columna (pueden variar por idioma)
                row = {k.strip().lower(): v.strip() for k, v in row.items()}

                titulo  = limpiar(row.get("trend") or row.get("tendencia") or "")
                trafico = limpiar(row.get("search volume") or row.get("volumen de búsquedas") or row.get("volume") or "")
                started = limpiar(row.get("started") or row.get("iniciado") or "")
                status  = limpiar(row.get("status") or row.get("estado") or "")

                if not titulo or titulo.lower() in vistos:
                    continue

                # Fecha: "X hours ago" o timestamp
                fecha_dt = ahora
                fecha_fmt = ahora.strftime("%d/%m/%Y %H:%M")
                if "hours ago" in started.lower():
                    try:
                        h = int(re.search(r"(\d+)", started).group(1))
                        fecha_dt  = ahora - timedelta(hours=h)
                        fecha_fmt = fecha_dt.strftime("%d/%m/%Y %H:%M")
                    except Exception:
                        pass
                elif "minutes ago" in started.lower():
                    try:
                        m = int(re.search(r"(\d+)", started).group(1))
                        fecha_dt  = ahora - timedelta(minutes=m)
                        fecha_fmt = fecha_dt.strftime("%d/%m/%Y %H:%M")
                    except Exception:
                        pass

                if fecha_dt < corte:
                    continue

                vistos.add(titulo.lower())
                n += 1
                todos.append({
                    "titulo":      titulo,
                    "descripcion": "",
                    "trafico":     trafico or "—",
                    "trafico_num": trafico_a_numero(trafico),
                    "fecha":       fecha_fmt,
                    "fecha_dt":    fecha_dt.isoformat(),
                    "imagen":      "",
                    "link":        f"https://trends.google.com/trending?geo=MX&q={titulo.replace(' ', '+')}",
                    "status":      status,
                })

            print(f"   ✓ {n} trends del CSV")

        except Exception as e:
            print(f"   ✗ Error CSV: {e}")

    return todos, vistos


def fetch_rss(vistos_titulos):
    """
    Descarga RSS para obtener imágenes y descripciones.
    También agrega trends que no estaban en el CSV.
    """
    ahora = datetime.now(timezone.utc)
    corte = ahora - timedelta(days=MAXIMO_DIAS)
    extras = []
    media  = {}   # titulo_lower → {imagen, descripcion}

    for url in RSS_URLS:
        print(f"→ RSS: {url.split('?')[1]}")
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            root = ET.fromstring(r.content)
        except Exception as e:
            print(f"   ✗ {e}")
            continue

        for item in root.findall(".//item"):
            titulo  = limpiar(item.findtext("title", ""))
            trafico = limpiar(item.findtext("ht:approx_traffic", "", NS))
            imagen  = limpiar(item.findtext("ht:picture", "", NS))
            pub_str = limpiar(item.findtext("pubDate", ""))

            news = [limpiar(n.findtext("ht:news_item_title", "", NS))
                    for n in item.findall("ht:news_item", NS)]
            desc = next((t for t in news if t), "")

            clave = titulo.lower()

            # Guardar imagen/desc para enriquecer los del CSV
            if imagen or desc:
                media[clave] = {"imagen": imagen, "descripcion": desc[:240]}

            # Si no estaba en CSV, agregarlo como extra
            if clave not in vistos_titulos:
                fecha_dt, fecha_fmt = ahora, ahora.strftime("%d/%m/%Y %H:%M")
                try:
                    from email.utils import parsedate_to_datetime
                    fecha_dt  = parsedate_to_datetime(pub_str).astimezone(timezone.utc)
                    fecha_fmt = fecha_dt.strftime("%d/%m/%Y %H:%M")
                except Exception:
                    pass

                if fecha_dt < corte:
                    continue

                vistos_titulos.add(clave)
                extras.append({
                    "titulo":      titulo,
                    "descripcion": desc[:240],
                    "trafico":     trafico or "—",
                    "trafico_num": trafico_a_numero(trafico),
                    "fecha":       fecha_fmt,
                    "fecha_dt":    fecha_dt.isoformat(),
                    "imagen":      imagen,
                    "link":        f"https://trends.google.com/trending?geo=MX&q={titulo.replace(' ', '+')}",
                    "status":      "",
                })

    print(f"   + {len(extras)} trends adicionales del RSS")
    return extras, media


def main():
    ahora = datetime.now(timezone.utc)
    print(f"\n═══ Tendencias MX · {ahora.strftime('%d/%m/%Y %H:%M UTC')} ═══\n")

    # 1. CSV — fuente principal (volumen real, todos los trends)
    todos, vistos = fetch_csv()

    # 2. RSS — imágenes, descripciones y trends extra
    extras, media = fetch_rss(vistos)

    # 3. Enriquecer trends del CSV con imagen/desc del RSS
    for t in todos:
        m = media.get(t["titulo"].lower(), {})
        if m.get("imagen"):
            t["imagen"] = m["imagen"]
        if m.get("descripcion"):
            t["descripcion"] = m["descripcion"]

    # 4. Combinar y ordenar por volumen descendente
    todos = todos + extras
    todos.sort(key=lambda x: x.get("trafico_num", 0), reverse=True)

    # Limpiar campo interno
    for t in todos:
        t.pop("trafico_num", None)

    salida = {
        "actualizado": ahora.strftime("%d/%m/%Y %H:%M UTC"),
        "periodo":     f"Últimos {MAXIMO_DIAS} días · Google Trends MX",
        "total":       len(todos),
        "trends":      todos,
    }

    os.makedirs("data", exist_ok=True)
    with open("data/trends.json", "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)

    print(f"\n✅ trends.json → {len(todos)} tendencias")
    for t in todos[:10]:
        print(f"   {t['trafico']:>8}  {t['titulo']}")


if __name__ == "__main__":
    main()
