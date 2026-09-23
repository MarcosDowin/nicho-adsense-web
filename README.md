# Sistema de webs de nicho para AdSense (100% local, sin coste)

Pipeline completo: `keywords.json` → artículos generados con un LLM local (Ollama)
→ sitio estático compilado (Markdown + Jinja2) → anuncios AdSense inyectados
→ despliegue automático por Git a Cloudflare Pages / GitHub Pages.

No usa APIs de pago ni suscripciones: la generación de contenido corre en
local con Ollama, y el hosting/SSL (Cloudflare Pages o GitHub Pages) es gratuito.

## 0. Instalación (una vez)

```bash
cd "D:\Claude cosas\nicho-adsense-web"
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Ya está creado y probado: `.venv` existe y las dependencias están instaladas.

## 1. Configura tu sitio

Edita [config.json](config.json):

- `site_name`, `site_description`, `base_url`, `niche`
- `legal.*` → titular, email de contacto, país (para las páginas legales)
- `adsense.client_id` y `adsense.slots.*` → los rellenarás cuando tengas cuenta de AdSense (ver paso 5)
- `generation.ollama_model` → modelo local a usar (por defecto `llama3.1:8b`)

## 2. Genera las páginas legales obligatorias

```bash
.venv\Scripts\python.exe scripts\generate_legal_pages.py
```

Crea `content/legal/{politica-privacidad,aviso-legal,politica-cookies}.md` a
partir de los datos de `config.json`. Son plantillas genéricas en español:
revísalas (o pide revisión legal) antes de publicar, sobre todo `legal.owner_name`
y `legal.contact_email`.

## 3. Añade tus keywords

Edita [keywords.json](keywords.json) con los temas de tu nicho (ya incluye 20
de ejemplo sobre "productividad y trabajo remoto" para que puedas probar el
sistema tal cual). Formato:

```json
{"keyword": "tu tema de busqueda", "categoria": "una-categoria"}
```

## 4. Genera los artículos (Ollama, local y gratis)

Necesitas Ollama arrancado y el modelo descargado:

```bash
# Arrancar el servicio (déjalo corriendo en una terminal, o usa la app de Ollama)
"D:\Claude cosas\Ollama\ollama.exe" serve

# En otra terminal, descarga el modelo (una vez)
"D:\Claude cosas\Ollama\ollama.exe" pull llama3.1:8b
```

Luego genera los artículos:

```bash
.venv\Scripts\python.exe scripts\content_generator.py
```

- Escribe un `.md` por keyword en `content/posts/`, con front matter (título,
  meta description, FAQ) y cuerpo en Markdown con H2/H3.
- Salta los que ya existen (usa `--force` para regenerar, `--limit N` para
  probar con pocos primero).
- Ya hay un artículo de ejemplo (`tecnica-pomodoro-guia-completa.md`) generado
  a mano para que veas el formato esperado.

**Importante — revisión manual:** los modelos locales de 7-8B (como
`llama3.1:8b`) escriben rápido pero pueden inventar datos o cifras
(alucinaciones), sobre todo en temas factuales, de salud, legales o
financieros. El prompt les pide explícitamente que no inventen estadísticas,
pero **debes revisar cada artículo antes de publicarlo**, igual que harías con
cualquier redactor nuevo. Para más calidad, usa un modelo mayor si tu equipo
lo soporta (`ollama pull llama3.1:70b`, `qwen2.5:14b`, `mistral-nemo`, etc.)
cambiando `generation.ollama_model` en `config.json`.

Repite este paso hasta tener 15-20 artículos publicables (mínimo recomendado
por AdSense para evitar el rechazo por "contenido de escaso valor").

## 4b. Alternativa: escribir artículos a mano (`publish.py`)

Si prefieres escribir tú el contenido en vez de generarlo con Ollama:

```bash
.venv\Scripts\python.exe scripts\publish.py new "Título de tu artículo" --category teletrabajo
```

Crea un borrador en `content/drafts/` con el front matter y las secciones
(H2/H3, FAQ) ya esqueletadas con marcadores `TODO`. Ábrelo en tu editor,
escribe el contenido real y luego publícalo:

```bash
.venv\Scripts\python.exe scripts\publish.py publish content\drafts\tu-articulo.md
```

Esto valida que no queden `TODO` sin rellenar, mueve el archivo a
`content/posts/` y **compila el sitio automáticamente**. Añade `--force` para
publicar aunque queden TODO o el slug ya exista, o `--no-build` para no
recompilar. `publish.py list` muestra los borradores pendientes y los
artículos ya publicados.

Puedes combinar ambos flujos: usa `content_generator.py` para tener volumen
rápido con Ollama, y `publish.py` para tus artículos "ancla" escritos a mano.

## 5. Activa AdSense (cuando tengas cuenta aprobada)

1. Crea tu cuenta en [Google AdSense](https://adsense.google.com/) (gratis) y
   añade tu dominio.
2. Copia tu `data-ad-client` (formato `ca-pub-XXXXXXXXXXXXXXXX`) y los
   `data-ad-slot` de los bloques de anuncio que crees en tu panel de AdSense.
3. En `config.json`, rellena `adsense.client_id` y `adsense.slots.*`, y pon
   `"enabled": true`.

Hasta que `enabled` sea `true`, `build.py` no inyecta ningún anuncio (para no
publicar un sitio con AdSense roto antes de tener cuenta).

## 6. Compila el sitio

```bash
.venv\Scripts\python.exe scripts\build.py
```

Genera `dist/` con HTML estático: home, un directorio por artículo (URLs
limpias tipo `/mi-articulo/`), las 3 páginas legales, `sitemap.xml` y
`robots.txt`. En cada artículo inserta el JSON-LD de `Article` + `FAQPage`
(si tiene preguntas frecuentes) y, si AdSense está activado, los 3 bloques de
anuncios (`adsense_injector.py`): tras el primer párrafo, a mitad de
artículo y antes de la conclusión.

Para previsualizarlo en local antes de publicar:

```bash
cd dist
"..\.venv\Scripts\python.exe" -m http.server 8000
# abre http://localhost:8000
```

## 7. Despliegue automático (Git → GitHub → Cloudflare Pages)

El repositorio local ya está inicializado (`git init`, rama `main`). Te falta
solo la parte que requiere tu cuenta:

**Configuración única (una vez), la haces tú:**

1. Crea un repositorio vacío en GitHub (sin README/licencia, para que no
   choque con lo que ya tienes aquí).
2. Conéctalo como remoto:
   ```bash
   git remote add origin https://github.com/tu-usuario/tu-repo.git
   ```
3. En el dashboard de [Cloudflare Pages](https://dash.cloudflare.com/):
   "Workers & Pages" → "Create application" → "Pages" → "Connect to Git" →
   elige el repo. **Build command:** vacío. **Build output directory:** `dist`.
   (Como `dist/` ya se sube compilado con cada push, Cloudflare no necesita
   ejecutar Python: solo sirve los archivos estáticos.)

Con eso, cada `git push` a `main` dispara un despliegue automático en
Cloudflare Pages, con SSL y CDN gratis.

**Cada vez que quieras publicar cambios:**

```bash
./deploy.sh
```

(o en Windows sin Git Bash: `.venv\Scripts\python.exe scripts\deploy.py`).
Ambos hacen lo mismo: compilar el sitio (`build.py`) y `git add/commit/push`.
`deploy.sh` es un envoltorio fino sobre `deploy.py` para tener el punto de
entrada en shell.

Opciones (funcionan igual en `deploy.sh` y `deploy.py`):
- `--branch gh-pages` → publica solo `dist/` en una rama dedicada (útil para
  GitHub Pages sirviendo la raíz de esa rama, en vez de Cloudflare Pages).
- `--dry-run` → muestra qué cambios subiría, sin hacer commit ni push.
- `--no-build` → sube el `dist/` actual sin recompilar.

## Flujo completo resumido

```bash
.venv\Scripts\python.exe scripts\generate_legal_pages.py       # una vez
.venv\Scripts\python.exe scripts\content_generator.py          # volumen rápido con Ollama
.venv\Scripts\python.exe scripts\publish.py new "Mi título"     # o escrito a mano...
.venv\Scripts\python.exe scripts\publish.py publish content\drafts\mi-titulo.md  # ...compila solo
./deploy.sh                                                     # publica en GitHub + Cloudflare Pages
```

## Nota sobre PageSpeed 100/100

Las plantillas están hechas para minimizar el coste de rendimiento: sin
frameworks JS, sin fuentes web externas, un único CSS pequeño, HTML semántico,
`<details>` nativo para el FAQ (sin JS). Con esto, el sitio *sin* anuncios
debería acercarse a 100/100 en PageSpeed/Lighthouse. En cuanto actives
AdSense, el propio script de Google (`adsbygoogle.js`, de terceros e
inevitable si quieres monetizar) suele restar algunos puntos en Rendimiento:
es normal y lo hacen todos los sitios con AdSense, no es un fallo del código.
