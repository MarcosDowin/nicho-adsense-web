"""
Inyecta bloques de anuncios de Google AdSense en puntos estrategicos del HTML
ya renderizado de un articulo: tras el primer parrafo, hacia la mitad del
articulo, y antes de la conclusion.

No se usa como script independiente: build.py importa `inject_ads()` para
cada articulo durante la compilacion del sitio.
"""

from bs4 import BeautifulSoup

AD_BLOCK_TEMPLATE = """
<div class="ad-container" data-ad-position="{position}">
  <ins class="adsbygoogle"
       style="display:block"
       data-ad-client="{client_id}"
       data-ad-slot="{slot}"
       data-ad-format="auto"
       data-full-width-responsive="true"></ins>
  <script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>
</div>
"""

# Nivel de bloque tras el que se considera "parrafo de contenido" a efectos
# de contar posiciones (evita contar encabezados como parrafos).
CONTENT_TAGS = ["p"]


def _make_ad_node(soup: BeautifulSoup, client_id: str, slot: str, position: str):
    html = AD_BLOCK_TEMPLATE.format(position=position, client_id=client_id, slot=slot)
    return BeautifulSoup(html, "html.parser")


def inject_ads(html: str, client_id: str, slots: dict) -> str:
    """
    Recibe el HTML de un articulo (ya convertido desde Markdown) y devuelve
    el HTML con anuncios insertados:
      - despues del primer <p>
      - a mitad del articulo (por numero de parrafos)
      - antes del ultimo <h2> (normalmente "Conclusion"), o al final si no hay
    """
    if not client_id or client_id.startswith("ca-pub-0000000000"):
        # AdSense no configurado todavia: no inyectamos nada para no romper el HTML.
        return html

    soup = BeautifulSoup(html, "html.parser")
    paragraphs = soup.find_all(CONTENT_TAGS)

    if not paragraphs:
        return str(soup)

    # 1) Tras el primer parrafo
    first_p = paragraphs[0]
    ad1 = _make_ad_node(soup, client_id, slots.get("after_first_paragraph", ""), "after_first_paragraph")
    first_p.insert_after(ad1)

    # 2) A mitad del articulo (por indice de parrafo, sin contar el ya insertado)
    if len(paragraphs) >= 4:
        mid_index = len(paragraphs) // 2
        mid_p = paragraphs[mid_index]
        ad2 = _make_ad_node(soup, client_id, slots.get("mid_article", ""), "mid_article")
        mid_p.insert_after(ad2)

    # 3) Antes de la conclusion: buscamos el ultimo <h2> (la seccion "Conclusion")
    headings_h2 = soup.find_all("h2")
    ad3 = _make_ad_node(soup, client_id, slots.get("before_conclusion", ""), "before_conclusion")
    if headings_h2:
        last_h2 = headings_h2[-1]
        last_h2.insert_before(ad3)
    else:
        soup.append(ad3)

    return str(soup)
