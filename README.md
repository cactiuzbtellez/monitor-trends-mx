# 📊 Tendencias MX — Monitor Google Trends

Dashboard de tendencias en tiempo real de **Google Trends México**, enfocado en temas de:
**Salud · Política · Economía · Seguridad**

Desplegado en GitHub Pages y actualizado automáticamente cada hora mediante GitHub Actions.

---

## 🗂 Estructura del proyecto

```
├── index.html                        # Dashboard principal (GitHub Pages)
├── data/
│   └── trends.json                   # Generado automáticamente por el Action
├── scripts/
│   └── fetch_trends.py               # Script Python que parsea el RSS de Trends
└── .github/
    └── workflows/
        └── fetch-trends.yml          # GitHub Action (corre cada hora)
```

---

## 🚀 Cómo publicar paso a paso

### 1. Crear el repositorio en GitHub
- Ve a [github.com/new](https://github.com/new)
- Nombre sugerido: `monitor-trends-mx`
- Déjalo **público** (GitHub Pages gratuito requiere repo público)
- **No** inicialices con README

### 2. Subir los archivos

**Opción A — Desde el navegador (sin terminal):**
1. Sube `index.html` y `README.md` desde **Add file → Upload files**
2. Para subcarpetas, usa **Add file → Create new file** y escribe el nombre con la ruta:
   - `scripts/fetch_trends.py`
   - `.github/workflows/fetch-trends.yml`
   - `data/trends.json`
   
**Opción B — Con GitHub Desktop (recomendado):**
1. Descarga [GitHub Desktop](https://desktop.github.com)
2. **File → Clone repository** → selecciona tu repo
3. Copia todos los archivos/carpetas en la carpeta local
4. **Commit to main** → **Push origin**

**Opción C — Terminal (Git):**
```bash
git init
git add .
git commit -m "feat: monitor de tendencias MX"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/monitor-trends-mx.git
git push -u origin main
```

### 3. Activar GitHub Pages
1. Ve a tu repo → **Settings** → **Pages**
2. Source: **Deploy from a branch**
3. Branch: `main` / Folder: `/ (root)`
4. Guarda → en ~1 minuto tendrás tu URL:
   `https://TU_USUARIO.github.io/monitor-trends-mx/`

### 4. Dar permisos de escritura al Action
El Action necesita hacer `git push` para actualizar `trends.json`:
1. Ve a **Settings** → **Actions** → **General**
2. Baja a *Workflow permissions*
3. Selecciona **Read and write permissions**
4. Guarda

### 5. Ejecutar el Action por primera vez
1. Ve a **Actions** → `Fetch Google Trends MX`
2. Click en **Run workflow** → **Run workflow**
3. Espera ~30 segundos
4. Recarga tu URL de GitHub Pages

---

## ⚙️ Categorías detectadas automáticamente

| Categoría | Ejemplos de términos |
|-----------|----------------------|
| 🏥 Salud | cubrebocas, pandemia, vacuna, covid, dengue, IMSS… |
| 🏛 Política | presidente, Sheinbaum, Morena, congreso, reforma… |
| 📈 Economía | inflación, peso, dólar, Banxico, Pemex, SAT… |
| 🚨 Seguridad | violencia, cartel, feminicidio, Guardia Nacional… |
| 🔎 General | cualquier otro trending que no clasifica arriba |

---

## ⏱ Frecuencia de actualización

El Action corre automáticamente **cada hora** (`cron: "0 * * * *"`).

Para cambiar la frecuencia edita `.github/workflows/fetch-trends.yml`:
```yaml
- cron: "*/30 * * * *"   # cada 30 minutos
- cron: "0 */2 * * *"    # cada 2 horas
```

---

## 🔧 Agregar más fuentes RSS

Edita `scripts/fetch_trends.py` y agrega entradas al array `FEEDS`:
```python
{
    "nombre": "Google Trends MX — Salud",
    "url": "https://trends.google.com/trending/rss?geo=MX&cat=m",
    "geo": "MX",
},
```

Google Trends admite el parámetro `cat` para categorías específicas.

---

## 📦 Dependencias Python

- `feedparser` — parseo del RSS
- `requests` — instalado como dependencia base

Instaladas automáticamente por el GitHub Action vía `pip install feedparser requests`.
