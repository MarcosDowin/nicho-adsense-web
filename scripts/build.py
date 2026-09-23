"""
Generador de sitio estatico: compila content/posts/*.md y content/legal/*.md
a HTML (dist/), aplicando plantillas Jinja2, inyectando AdSense, generando
JSON-LD (Article + FAQPage), sitemap.xml y robots.txt.

Uso:
    python scripts/build.py
"""

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

import frontmatter
import markdown as md
from jinja2 import Environment, FileSystemLoader

sys.path.insert(0, str(Path(__file__).resolve().parent))
from adsense_injector import inject_ads  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.json"
POSTS_DIR = ROOT / "content" / "posts"
LEGAL_DIR = ROOT / "content" / "legal"
TEMPLATES_DIR = ROOT / "templates"
STATIC_DIR = ROOT / "static"
DIST_DIR = ROOT / "dist"

MESES_ES = [
    "", "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]

MD_EXTENSIONS = ["extra", "sane_lists", "toc"]


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def date_display(iso_date: str) -> str:
    d = datetime.fromisoformat(iso_date)
    return f"{d.day} de {MESES_ES[d.month]} de {d.year}"


def reading_time(word_count: int) -> int:
    return max(1, round(word_count / 200))


def render_markdown_body(text: str) -> str:
    return md.markdown(text, extensions=MD_EXTENSIONS)


def build_article_jsonld(post: dict, cfg: dict) -> str:
    url = f"{cfg['base_url']}/{post['slug']}/"
    data = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Article",
                "headline": post["title"],
                "description": post["meta_description"],
                "datePublished": post["date"],
                "dateModified": post["date"],
                "author": {"@type": "Person", "name": post.get("author") or cfg.get("author", "Redacción")},
                "publisher": {"@type": "Organization", "name": cfg["site_name"]},
                "mainEntityOfPage": {"@type": "WebPage", "@id": url},
            }
        ],
    }
    if post.get("faq"):
        data["@graph"].append(
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": item["q"],
                        "acceptedAnswer": {"@type": "Answer", "text": item["a"]},
                    }
                    for item in post["faq"]
                ],
            }
        )
    return json.dumps(data, ensure_ascii=False)


def load_posts(cfg: dict) -> list:
    posts = []
    for path in sorted(POSTS_DIR.glob("*.md")):
        fm = frontmatter.load(path)
        html_content = render_markdown_body(fm.content)
        word_count = len(fm.content.split())

        adsense = cfg.get("adsense", {})
        if adsense.get("enabled"):
            html_content = inject_ads(html_content, adsense["client_id"], adsense.get("slots", {}))

        post = dict(fm.metadata)
        post["html_content"] = html_content
        raw_date = post["date"]
        date_iso = raw_date.isoformat() if hasattr(raw_date, "isoformat") else str(raw_date)
        post["date_display"] = date_display(date_iso)
        post["date"] = date_iso
        post["reading_time"] = reading_time(word_count)
        post.setdefault("faq", [])
        post.setdefault("category", "general")
        posts.append(post)

    posts.sort(key=lambda p: p["date"], reverse=True)
    return posts


def load_legal_pages() -> list:
    pages = []
    for path in sorted(LEGAL_DIR.glob("*.md")):
        fm = frontmatter.load(path)
        page = dict(fm.metadata)
        page["html_content"] = render_markdown_body(fm.content)
        pages.append(page)
    return pages


def base_context(cfg: dict) -> dict:
    adsense = cfg.get("adsense", {})
    return {
        "site_name": cfg["site_name"],
        "site_description": cfg["site_description"],
        "lang": cfg.get("language", "es"),
        "current_year": datetime.now().year,
        "adsense_enabled": adsense.get("enabled", False),
        "adsense_client_id": adsense.get("client_id", ""),
    }


def write_page(env: Environment, template_name: str, out_path: Path, context: dict):
    template = env.get_template(template_name)
    html = template.render(**context)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")


def build_sitemap(cfg: dict, posts: list, legal_pages: list):
    base = cfg["base_url"].rstrip("/")
    urls = [f"{base}/"]
    urls += [f"{base}/{p['slug']}/" for p in posts]
    urls += [f"{base}/{p['slug']}/" for p in legal_pages]

    items = "\n".join(f"  <url><loc>{u}</loc></url>" for u in urls)
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{items}\n"
        "</urlset>\n"
    )
    (DIST_DIR / "sitemap.xml").write_text(xml, encoding="utf-8")


def build_robots(cfg: dict):
    base = cfg["base_url"].rstrip("/")
    content = f"User-agent: *\nAllow: /\n\nSitemap: {base}/sitemap.xml\n"
    (DIST_DIR / "robots.txt").write_text(content, encoding="utf-8")


def main():
    cfg = load_config()

    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir(parents=True)

    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))

    posts = load_posts(cfg)
    legal_pages = load_legal_pages()

    if not posts:
        print("[AVISO] No hay artículos en content/posts/. Ejecuta content_generator.py primero.")

    # Home
    ctx = base_context(cfg)
    ctx.update(
        {
            "page_title": f"{cfg['site_name']} — {cfg['site_description']}",
            "meta_description": cfg["site_description"],
            "canonical_url": cfg["base_url"] + "/",
            "posts": posts,
            "json_ld": None,
            "noindex": False,
        }
    )
    write_page(env, "index.html", DIST_DIR / "index.html", ctx)

    # Posts
    for post in posts:
        related = [p for p in posts if p["slug"] != post["slug"]][:4]
        ctx = base_context(cfg)
        ctx.update(
            {
                "page_title": f"{post['title']} — {cfg['site_name']}",
                "meta_description": post["meta_description"],
                "canonical_url": f"{cfg['base_url']}/{post['slug']}/",
                "post": post,
                "related_posts": related,
                "json_ld": build_article_jsonld(post, cfg),
                "og_type": "article",
                "noindex": False,
            }
        )
        write_page(env, "post.html", DIST_DIR / post["slug"] / "index.html", ctx)

    # Legal pages
    for page in legal_pages:
        ctx = base_context(cfg)
        ctx.update(
            {
                "page_title": f"{page['title']} — {cfg['site_name']}",
                "meta_description": page["title"],
                "canonical_url": f"{cfg['base_url']}/{page['slug']}/",
                "page": page,
                "json_ld": None,
                "noindex": page.get("noindex", False),
            }
        )
        write_page(env, "legal.html", DIST_DIR / page["slug"] / "index.html", ctx)

    # Static assets
    shutil.copytree(STATIC_DIR, DIST_DIR / "static", dirs_exist_ok=True)

    build_sitemap(cfg, posts, legal_pages)
    build_robots(cfg)

    print(f"[OK] Sitio compilado en {DIST_DIR}")
    print(f"     Artículos: {len(posts)} | Páginas legales: {len(legal_pages)}")


if __name__ == "__main__":
    main()
