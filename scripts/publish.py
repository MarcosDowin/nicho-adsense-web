"""
Flujo para anadir articulos ESCRITOS A MANO (sin IA) y publicarlos:

  1. `new`     -> crea un borrador .md en content/drafts/ con el front matter
                  y el esqueleto de secciones ya listos para rellenar.
  2. `publish` -> valida el borrador, lo mueve a content/posts/ y compila
                  el sitio automaticamente (llama a build.py).
  3. `list`    -> muestra que borradores estan pendientes y que articulos
                  ya estan publicados.

Uso:
    python scripts/publish.py new "Como teletrabajar sin distracciones"
    # ... editas el .md que se ha creado en content/drafts/ ...
    python scripts/publish.py publish content/drafts/como-teletrabajar-sin-distracciones.md
    python scripts/publish.py list
"""

import argparse
import json
import re
import subprocess
import sys
import unicodedata
from datetime import date
from pathlib import Path

import frontmatter

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.json"
DRAFTS_DIR = ROOT / "content" / "drafts"
POSTS_DIR = ROOT / "content" / "posts"

TODO_MARKER = "TODO"
PLACEHOLDER_META = "TODO: escribe una meta descripción de 120-155 caracteres, resumiendo el artículo"


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text).strip("-")
    return text


def cmd_new(args):
    cfg = load_config()
    title = args.title.strip()
    slug = slugify(title)
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    draft_path = DRAFTS_DIR / f"{slug}.md"

    if draft_path.exists() and not args.force:
        print(f"[ERROR] Ya existe un borrador en {draft_path.relative_to(ROOT)} (usa --force para sobrescribir)")
        sys.exit(1)

    content = f"""---
title: "{title}"
slug: {slug}
date: {date.today().isoformat()}
category: {args.category or "general"}
meta_description: "{PLACEHOLDER_META}"
author: "{cfg.get('author', 'Redacción')}"
faq:
  - q: "TODO: pregunta frecuente 1"
    a: "TODO: respuesta"
  - q: "TODO: pregunta frecuente 2"
    a: "TODO: respuesta"
---

TODO: escribe aquí la introducción (2-4 frases que enganchen al lector).

## Primer apartado

TODO

## Segundo apartado

TODO

### Un subapartado si hace falta

TODO

## Conclusión

TODO
"""
    draft_path.write_text(content, encoding="utf-8")
    print(f"[OK] Borrador creado: {draft_path.relative_to(ROOT)}")
    print("Ábrelo, sustituye los TODO por tu contenido real y luego ejecuta:")
    print(f"    python scripts/publish.py publish {draft_path.relative_to(ROOT)}")


def _find_todos(text: str) -> list:
    return [line.strip() for line in text.splitlines() if TODO_MARKER in line]


def cmd_publish(args):
    draft_path = Path(args.file)
    if not draft_path.is_absolute():
        draft_path = ROOT / draft_path
    if not draft_path.exists():
        print(f"[ERROR] No existe el archivo: {draft_path}")
        sys.exit(1)

    fm = frontmatter.load(draft_path)
    required = ["title", "slug", "date", "meta_description", "category"]
    missing = [k for k in required if not fm.metadata.get(k)]
    if missing:
        print(f"[ERROR] Faltan campos en el front matter: {missing}")
        sys.exit(1)

    todos = _find_todos(draft_path.read_text(encoding="utf-8"))
    if todos and not args.force:
        print(f"[ERROR] El artículo todavía tiene {len(todos)} marcador(es) TODO sin rellenar:")
        for t in todos[:10]:
            print(f"    - {t}")
        print("Complétalos o usa --force para publicar igualmente.")
        sys.exit(1)

    word_count = len(fm.content.split())
    min_words = load_config()["generation"]["min_words_per_article"]
    if word_count < min_words:
        print(f"[AVISO] El artículo tiene {word_count} palabras (recomendado: {min_words}+). Se publica igualmente.")

    if not args.keep_date:
        fm.metadata["date"] = date.today().isoformat()

    slug = fm.metadata["slug"]
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = POSTS_DIR / f"{slug}.md"

    if out_path.exists() and not args.force:
        print(f"[ERROR] Ya existe un artículo publicado con ese slug: {out_path.relative_to(ROOT)}")
        print("        Usa --force para sobrescribirlo.")
        sys.exit(1)

    frontmatter.dump(fm, out_path)
    draft_path.unlink()
    print(f"[OK] Publicado: {out_path.relative_to(ROOT)} ({word_count} palabras)")

    if not args.no_build:
        print("\n== Compilando el sitio ==")
        sys.stdout.flush()
        subprocess.run([sys.executable, str(ROOT / "scripts" / "build.py")], check=True)


def cmd_list(args):
    drafts = sorted(DRAFTS_DIR.glob("*.md")) if DRAFTS_DIR.exists() else []
    posts = sorted(POSTS_DIR.glob("*.md")) if POSTS_DIR.exists() else []

    print(f"Borradores pendientes ({len(drafts)}):")
    for d in drafts:
        todos = _find_todos(d.read_text(encoding="utf-8"))
        estado = f"{len(todos)} TODO pendientes" if todos else "listo para publicar"
        print(f"  - {d.name}  [{estado}]")

    print(f"\nArtículos publicados ({len(posts)}):")
    for p in posts:
        print(f"  - {p.name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_new = sub.add_parser("new", help="Crear un borrador nuevo")
    p_new.add_argument("title", help="Título del artículo")
    p_new.add_argument("--category", default=None, help="Categoría (por defecto: general)")
    p_new.add_argument("--force", action="store_true", help="Sobrescribir si ya existe un borrador con ese slug")
    p_new.set_defaults(func=cmd_new)

    p_pub = sub.add_parser("publish", help="Publicar un borrador y compilar el sitio")
    p_pub.add_argument("file", help="Ruta al borrador .md (dentro o fuera de content/drafts/)")
    p_pub.add_argument("--force", action="store_true", help="Publicar aunque queden TODO o el slug ya exista")
    p_pub.add_argument("--keep-date", action="store_true", help="Mantener la fecha del borrador en vez de usar hoy")
    p_pub.add_argument("--no-build", action="store_true", help="No compilar el sitio tras publicar")
    p_pub.set_defaults(func=cmd_publish)

    p_list = sub.add_parser("list", help="Ver borradores pendientes y artículos publicados")
    p_list.set_defaults(func=cmd_list)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
