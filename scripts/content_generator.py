"""
Genera articulos extensos y optimizados para SEO a partir de ../keywords.json,
usando un modelo LLM LOCAL a traves de Ollama (sin coste, sin API de pago).

Genera cada articulo en VARIAS llamadas (esquema -> una por seccion ->
conclusion) en vez de pedir el articulo entero de una sola vez. Con modelos
pequenos (7B-8B) pedir "escribe 1200 palabras" en un solo JSON casi siempre
se queda corto; pedir "escribe 250-320 palabras de esta seccion concreta"
varias veces es mucho mas fiable y en conjunto suma mas texto.

Requisito previo: Ollama debe estar instalado y en marcha, con el modelo
configurado en config.json -> generation.ollama_model descargado, por ejemplo:

    ollama pull llama3.1:8b

Uso:
    python scripts/content_generator.py
    python scripts/content_generator.py --limit 5      # solo los 5 primeros keywords
    python scripts/content_generator.py --force         # regenera aunque ya exista el .md

AVISO SOBRE CALIDAD: los modelos locales pequenos (7B-8B) escriben rapido pero
pueden inventar datos, cifras o fuentes (alucinaciones), sobre todo en temas
factuales, de salud, legales o financieros (YMYL). Este script le pide al
modelo que NO invente cifras, estudios ni precios concretos, pero AUN ASI
debes revisar manualmente cada articulo antes de publicarlo. Si tienes
hardware suficiente, usa un modelo mayor (ollama pull qwen2.5:14b,
mistral-nemo, llama3.1:70b...) para mejor calidad y mejor seguimiento de
instrucciones, cambiando generation.ollama_model en config.json.
"""

import argparse
import json
import re
import sys
import time
import unicodedata
from datetime import date
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.json"
KEYWORDS_PATH = ROOT / "keywords.json"
POSTS_DIR = ROOT / "content" / "posts"

NUM_SECTIONS = 5

OUTLINE_PROMPT = """Eres un redactor SEO experto en español que escribe para un blog sobre "{niche}".

Vas a PLANIFICAR (todavía NO escribir el contenido completo) un artículo extenso sobre: "{keyword}".

Responde ÚNICAMENTE con un objeto JSON válido (sin texto antes ni después, sin bloques de código markdown) con esta forma exacta:

{{
  "title": "Título atractivo y optimizado para SEO, máximo 60 caracteres",
  "meta_description": "Meta descripción SEO, entre 120 y 155 caracteres, que resuma el artículo e invite al clic",
  "introduction": "Párrafo de introducción de 3-5 frases que enganche al lector y contextualice el tema (mínimo 60 palabras)",
  "sections": [
    {{"heading": "Título de la sección H2 nº1", "subsection_heading": ""}},
    {{"heading": "Título de la sección H2 nº2", "subsection_heading": ""}},
    {{"heading": "Título de la sección H2 nº3", "subsection_heading": "Título H3 opcional dentro de esta sección, o cadena vacía si no aplica"}},
    {{"heading": "Título de la sección H2 nº4", "subsection_heading": ""}},
    {{"heading": "Título de la sección H2 nº5", "subsection_heading": ""}}
  ],
  "faq": [
    {{"question": "Pregunta frecuente real que alguien buscaría en Google sobre {keyword}", "answer": "Respuesta breve y clara"}}
  ]
}}

Los 5 títulos de sección deben cubrir el tema desde ángulos distintos y complementarios, sin repetirse entre sí. Incluye 4 o 5 preguntas en "faq".
"""

SECTION_PROMPT = """Estás escribiendo un artículo en español titulado "{title}", sobre el tema "{keyword}".

Escribe SOLO el contenido de la sección "{heading}" (no repitas el título como texto, no escribas el resto del artículo, no escribas introducción ni conclusión).

Reglas:
- Extensión: entre {min_words} y {max_words} palabras, en 2-4 párrafos.
- No inventes estadísticas, cifras exactas, porcentajes, estudios o precios concretos que no puedas verificar. Esto incluye NO inventar "casos de éxito" ni empresas (reales o genéricas) con resultados numéricos concretos (por ejemplo, "aumentó un 30% la productividad"): si el título de la sección sugiere ejemplos o casos reales, habla en términos generales ("es habitual observar...", "muchos equipos notan...") en vez de inventar un caso concreto con cifras. Puedes nombrar herramientas, métodos o conceptos reales y conocidos si aportan valor, pero sin inventar datos sobre ellos.
- Contenido práctico y original; no repitas ideas de una introducción genérica.
{subsection_instruction}

Responde ÚNICAMENTE con un objeto JSON válido con esta forma exacta:
{{
  "content": "Contenido de la sección, con \\n\\n entre párrafos",
  "subsection_content": {subsection_json_hint}
}}
"""

CONCLUSION_PROMPT = """Estás terminando de escribir un artículo en español titulado "{title}", sobre "{keyword}".

Escribe SOLO el párrafo de conclusión, de 100 a 160 palabras: resume las ideas clave del artículo y anima al lector a pasar a la acción. No inventes cifras ni estudios. No repitas frases literales de una introducción.

Responde ÚNICAMENTE con un objeto JSON válido: {{"conclusion": "..."}}
"""


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text).strip("-")
    return text


def check_ollama(base_url: str):
    ping_url = base_url.rsplit("/api/", 1)[0]
    try:
        requests.get(ping_url, timeout=3)
    except requests.exceptions.ConnectionError:
        print(f"[ERROR] No se puede conectar con Ollama en {ping_url}")
        print("        Arranca el servicio antes de continuar, por ejemplo:")
        print('        & "D:\\Claude cosas\\Ollama\\ollama.exe" serve')
        sys.exit(1)


def call_ollama_json(cfg: dict, prompt: str) -> dict:
    gen_cfg = cfg["generation"]
    payload = {
        "model": gen_cfg["ollama_model"],
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": gen_cfg.get("temperature", 0.6),
            "num_predict": gen_cfg.get("num_predict", 900),
        },
    }
    resp = requests.post(gen_cfg["ollama_url"], json=payload, timeout=300)
    resp.raise_for_status()
    raw = resp.json()["response"]
    return json.loads(raw)


def call_with_retries(cfg: dict, prompt: str, required_keys: list, label: str, validate=None) -> dict:
    max_retries = cfg["generation"].get("max_retries", 3)
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            data = call_ollama_json(cfg, prompt)
            missing = [k for k in required_keys if k not in data]
            if missing:
                raise ValueError(f"Faltan campos en el JSON: {missing}")
            if validate:
                validate(data)
            return data
        except (json.JSONDecodeError, ValueError, requests.RequestException) as exc:
            last_error = exc
            print(f"      [{label}] intento {attempt}/{max_retries} fallido: {exc}")
            time.sleep(2)
    raise RuntimeError(f"'{label}' falló tras {max_retries} intentos: {last_error}")


ENDING_PUNCTUATION = ".!?»\"”)"


def _looks_truncated(text: str) -> bool:
    text = text.strip()
    return bool(text) and text[-1] not in ENDING_PUNCTUATION


def _validate_section(data: dict):
    content = (data.get("content") or "").strip()
    if not content or _looks_truncated(content):
        raise ValueError("el contenido de la sección parece cortado (no termina en una frase completa)")
    subsection_content = (data.get("subsection_content") or "").strip()
    if subsection_content and _looks_truncated(subsection_content):
        raise ValueError("el subapartado parece cortado (no termina en una frase completa)")


def strip_heading_echo(text: str, heading: str) -> str:
    """Quita, si aparece, el propio titulo repetido como primera 'frase' del texto (una o mas veces)."""
    text = text.strip()
    normalized_heading = heading.strip().rstrip(".:").lower()
    while True:
        match = re.search(r"[.!?\n]", text)
        boundary = match.end() if match else len(text)
        candidate = text[:boundary].strip().rstrip(".:").lower()
        if candidate == normalized_heading and match:
            text = text[boundary:].strip()
        else:
            break
    return text


def generate_outline(cfg: dict, keyword: str) -> dict:
    prompt = OUTLINE_PROMPT.format(niche=cfg["niche"], keyword=keyword)
    outline = call_with_retries(cfg, prompt, ["title", "meta_description", "introduction", "sections", "faq"], "esquema")
    if len(outline["sections"]) < 3:
        raise RuntimeError("El esquema generado tiene menos de 3 secciones, se descarta el artículo")
    return outline


def generate_section(cfg: dict, title: str, keyword: str, heading: str, subsection_heading: str, min_words: int, max_words: int) -> dict:
    if subsection_heading:
        subsection_instruction = f'- Además, escribe un subapartado propio titulado "{subsection_heading}", de 100 a 150 palabras, con ideas que no repitan el contenido principal de la sección.'
        subsection_hint = '"Contenido del subapartado, 100-150 palabras"'
    else:
        subsection_instruction = ""
        subsection_hint = '""'

    prompt = SECTION_PROMPT.format(
        title=title,
        keyword=keyword,
        heading=heading,
        min_words=min_words,
        max_words=max_words,
        subsection_instruction=subsection_instruction,
        subsection_json_hint=subsection_hint,
    )
    result = call_with_retries(cfg, prompt, ["content"], f"sección '{heading}'", validate=_validate_section)
    result["content"] = strip_heading_echo(result["content"], heading)
    if subsection_heading and result.get("subsection_content"):
        result["subsection_content"] = strip_heading_echo(result["subsection_content"], subsection_heading)
    return result


def generate_conclusion(cfg: dict, title: str, keyword: str) -> str:
    prompt = CONCLUSION_PROMPT.format(title=title, keyword=keyword)
    data = call_with_retries(cfg, prompt, ["conclusion"], "conclusión")
    return data["conclusion"]


def generate_article(cfg: dict, keyword_entry: dict) -> dict:
    keyword = keyword_entry["keyword"]
    min_words_total = cfg["generation"]["min_words_per_article"]

    outline = generate_outline(cfg, keyword)
    title = outline["title"]

    section_min = max(150, round(min_words_total * 0.16))
    section_max = section_min + 100

    sections = []
    for sec in outline["sections"]:
        heading = sec["heading"]
        subsection_heading = (sec.get("subsection_heading") or "").strip()
        print(f"      generando sección: {heading}")
        result = generate_section(cfg, title, keyword, heading, subsection_heading, section_min, section_max)
        section = {"heading": heading, "content": result["content"], "subsections": []}
        subsection_content = (result.get("subsection_content") or "").strip()
        if subsection_heading and subsection_content:
            section["subsections"].append({"heading": subsection_heading, "content": subsection_content})
        sections.append(section)

    conclusion = generate_conclusion(cfg, title, keyword)

    return {
        "title": title,
        "meta_description": outline["meta_description"],
        "introduction": outline["introduction"],
        "sections": sections,
        "faq": outline["faq"],
        "conclusion": conclusion,
    }


def article_word_count(article: dict) -> int:
    parts = [article.get("introduction", ""), article.get("conclusion", "")]
    for section in article.get("sections", []):
        parts.append(section.get("content", ""))
        for sub in section.get("subsections", []):
            parts.append(sub.get("content", ""))
    for faq in article.get("faq", []):
        parts.append(faq.get("answer", ""))
    return sum(len(p.split()) for p in parts)


def build_markdown_body(article: dict) -> str:
    lines = [article["introduction"].strip(), ""]
    for section in article.get("sections", []):
        lines.append(f"## {section['heading']}")
        lines.append("")
        lines.append(section["content"].strip())
        lines.append("")
        for sub in section.get("subsections", []):
            lines.append(f"### {sub['heading']}")
            lines.append("")
            lines.append(sub["content"].strip())
            lines.append("")
    lines.append("## Conclusión")
    lines.append("")
    lines.append(article["conclusion"].strip())
    lines.append("")
    return "\n".join(lines)


def build_frontmatter(article: dict, keyword_entry: dict, cfg: dict) -> str:
    slug = slugify(article["title"])
    today = date.today().isoformat()
    meta_desc = article["meta_description"].replace('"', "'")
    title = article["title"].replace('"', "'")

    faq_yaml_lines = ["faq:"]
    for item in article.get("faq", []):
        q = item["question"].replace('"', "'")
        a = item["answer"].replace('"', "'").replace("\n", " ")
        faq_yaml_lines.append(f'  - q: "{q}"')
        faq_yaml_lines.append(f'    a: "{a}"')
    faq_yaml = "\n".join(faq_yaml_lines) if article.get("faq") else "faq: []"

    return (
        "---\n"
        f'title: "{title}"\n'
        f"slug: {slug}\n"
        f"date: {today}\n"
        f'keyword: "{keyword_entry["keyword"]}"\n'
        f'category: {keyword_entry.get("categoria", "general")}\n'
        f'meta_description: "{meta_desc}"\n'
        f'author: "{cfg.get("author", "Redacción")}"\n'
        f"{faq_yaml}\n"
        "---\n\n"
    ), slug


def existing_posts_by_keyword(posts_dir: Path) -> dict:
    """Mapea keyword -> Path leyendo el campo 'keyword' del front matter de cada .md publicado.

    El nombre de archivo se basa en el título que inventa el modelo (no en el
    keyword original), así que no sirve para detectar duplicados por prefijo.
    """
    mapping = {}
    for path in posts_dir.glob("*.md"):
        text = path.read_text(encoding="utf-8")
        match = re.search(r'^keyword:\s*"(.*)"\s*$', text, re.MULTILINE)
        if match:
            mapping[match.group(1)] = path
    return mapping


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Generar solo los N primeros keywords")
    parser.add_argument("--force", action="store_true", help="Regenerar aunque el .md ya exista")
    args = parser.parse_args()

    cfg = load_json(CONFIG_PATH)
    keywords = load_json(KEYWORDS_PATH)
    if args.limit:
        keywords = keywords[: args.limit]

    check_ollama(cfg["generation"]["ollama_url"])
    POSTS_DIR.mkdir(parents=True, exist_ok=True)

    min_words = cfg["generation"]["min_words_per_article"]
    ok, skipped, failed = 0, 0, 0

    for i, kw in enumerate(keywords, 1):
        print(f"[{i}/{len(keywords)}] {kw['keyword']}")
        existing_map = existing_posts_by_keyword(POSTS_DIR)
        existing_path = existing_map.get(kw["keyword"])
        if existing_path and not args.force:
            print(f"    ya existe ({existing_path.name}), se omite (usa --force para regenerar)")
            skipped += 1
            continue
        if existing_path and args.force:
            existing_path.unlink()

        try:
            article = generate_article(cfg, kw)
        except RuntimeError as exc:
            print(f"    [ERROR] {exc}")
            failed += 1
            continue

        words = article_word_count(article)
        if words < min_words:
            print(f"    [AVISO] solo {words} palabras (mínimo {min_words}), revisa manualmente")

        frontmatter, slug = build_frontmatter(article, kw, cfg)
        body = build_markdown_body(article)
        out_path = POSTS_DIR / f"{slug}.md"
        out_path.write_text(frontmatter + body, encoding="utf-8")
        print(f"    [OK] {out_path.relative_to(ROOT)} ({words} palabras)")
        ok += 1

    print(f"\nHecho. Generados: {ok} | Omitidos: {skipped} | Fallidos: {failed}")
    print("Revisa manualmente el contenido antes de publicar (datos, cifras, afirmaciones factuales).")


if __name__ == "__main__":
    main()
