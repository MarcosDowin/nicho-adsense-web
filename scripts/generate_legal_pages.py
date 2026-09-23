"""
Genera las paginas legales obligatorias para AdSense (Markdown con front matter)
a partir de los datos rellenados en config.json -> "legal".

Uso:
    python scripts/generate_legal_pages.py

Estas plantillas cubren lo minimo que Google AdSense y el RGPD/LSSI espanol
suelen exigir, pero son GENERICAS. Revisa (o haz revisar por un abogado) el
contenido antes de publicar el sitio, especialmente si tratas datos sensibles
o vendes productos/servicios.
"""

import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.json"
LEGAL_DIR = ROOT / "content" / "legal"


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def privacy_policy(cfg: dict) -> str:
    legal = cfg["legal"]
    today = date.today().isoformat()
    return f"""---
title: "Política de Privacidad"
slug: politica-privacidad
date: {today}
noindex: false
---

## Responsable del tratamiento

- **Titular:** {legal['owner_name']}
- **Contacto:** {legal['contact_email']}
- **Sitio web:** {cfg['base_url']}
- **País:** {legal['country']}

## Datos que recopilamos

En **{cfg['site_name']}** podemos recopilar los siguientes datos cuando visitas el sitio:

- Datos de navegación (páginas visitadas, tiempo de permanencia, origen del tráfico) recogidos mediante cookies propias y de terceros.
- Datos que nos facilites voluntariamente a través de formularios de contacto o comentarios (nombre, correo electrónico, mensaje).
- Datos recopilados por terceros con fines publicitarios, en particular **Google AdSense**, que puede utilizar cookies para mostrar anuncios basados en tus visitas a este sitio y a otros sitios web.

## Finalidad del tratamiento

Los datos se tratan para:

1. Gestionar el correcto funcionamiento del sitio web.
2. Analizar el uso del sitio con fines estadísticos.
3. Mostrar publicidad personalizada o no personalizada a través de Google AdSense.
4. Responder a las consultas que nos envíes a través de los formularios disponibles.

## Base legal

La base legal para el tratamiento de tus datos es tu **consentimiento**, otorgado al aceptar el aviso de cookies o al enviarnos voluntariamente tus datos mediante un formulario.

## Publicidad y terceros (Google AdSense)

Este sitio web utiliza **Google AdSense**, un servicio de publicidad proporcionado por Google LLC. Google puede utilizar cookies para mostrar anuncios en función de tus visitas anteriores a este y otros sitios web.

Puedes inhabilitar el uso de cookies de personalización de anuncios de Google visitando:
[Configuración de anuncios de Google](https://adssettings.google.com/).

Más información en la [Política de Privacidad de Google](https://policies.google.com/privacy).

## Derechos de los usuarios

Puedes ejercer tus derechos de **acceso, rectificación, supresión, oposición, limitación del tratamiento y portabilidad** de tus datos escribiendo a {legal['contact_email']}, indicando el derecho que deseas ejercer y adjuntando una copia de un documento que acredite tu identidad.

## Conservación de los datos

Los datos se conservarán mientras se mantenga la relación con el usuario o durante los plazos legalmente establecidos, y se eliminarán o anonimizarán una vez dejen de ser necesarios para los fines indicados.

## Medidas de seguridad

Se han adoptado las medidas técnicas y organizativas razonables para garantizar la seguridad de los datos y evitar su alteración, pérdida, tratamiento o acceso no autorizado.

## Cambios en esta política

Esta Política de Privacidad puede actualizarse. Se recomienda revisarla periódicamente. Última actualización: {today}.
"""


def cookies_policy(cfg: dict) -> str:
    legal = cfg["legal"]
    today = date.today().isoformat()
    return f"""---
title: "Política de Cookies"
slug: politica-cookies
date: {today}
noindex: false
---

## ¿Qué son las cookies?

Las cookies son pequeños archivos de texto que los sitios web almacenan en tu navegador para recordar información sobre tu visita, mejorar tu experiencia y, en algunos casos, mostrar publicidad relevante.

## Cookies que utiliza {cfg['site_name']}

| Tipo | Finalidad | Propiedad |
|---|---|---|
| Técnicas / necesarias | Permiten el funcionamiento básico del sitio | Propias |
| Analíticas | Medir el tráfico y el uso del sitio de forma agregada | Terceros |
| Publicitarias | Mostrar anuncios personalizados o no personalizados mediante **Google AdSense** | Terceros (Google) |

## Cookies de Google AdSense

Este sitio muestra anuncios gestionados por Google AdSense. Google, como tercero, puede instalar cookies para:

- Ofrecer anuncios en base a las visitas del usuario a este sitio y a otros sitios web.
- Medir el rendimiento de los anuncios mostrados.

Puedes obtener más información y gestionar tus preferencias de anuncios en:
[https://adssettings.google.com/](https://adssettings.google.com/)

## Cómo desactivar o eliminar las cookies

Puedes permitir, bloquear o eliminar las cookies instaladas en tu equipo mediante la configuración de tu navegador:

- **Chrome:** Configuración → Privacidad y seguridad → Cookies.
- **Firefox:** Opciones → Privacidad y seguridad → Cookies.
- **Safari:** Preferencias → Privacidad.
- **Edge:** Configuración → Privacidad, búsqueda y servicios.

Ten en cuenta que si bloqueas todas las cookies, algunas funciones del sitio podrían no funcionar correctamente.

## Consentimiento

Al navegar y continuar en {cfg['site_name']} sin modificar la configuración de tu navegador, se entiende que aceptas el uso de las cookies descritas en esta política, conforme al aviso mostrado en tu primera visita.

## Contacto

Para cualquier duda sobre esta Política de Cookies, escribe a {legal['contact_email']}.

Última actualización: {today}.
"""


def legal_notice(cfg: dict) -> str:
    legal = cfg["legal"]
    today = date.today().isoformat()
    return f"""---
title: "Aviso Legal"
slug: aviso-legal
date: {today}
noindex: false
---

## Datos identificativos

En cumplimiento del deber de información recogido en la normativa aplicable, se facilitan los siguientes datos:

- **Titular:** {legal['owner_name']}
- **Contacto:** {legal['contact_email']}
- **País:** {legal['country']} ({legal['city']})
- **Sitio web:** {cfg['base_url']}

## Objeto

El presente Aviso Legal regula el uso del sitio web {cfg['base_url']} (en adelante, "el sitio"), cuya finalidad es proporcionar contenido informativo sobre {cfg['niche']}.

El acceso y uso del sitio atribuye la condición de usuario e implica la aceptación plena de las condiciones incluidas en este Aviso Legal.

## Condiciones de uso

El usuario se compromete a hacer un uso adecuado y lícito del sitio, así como de los contenidos, de conformidad con la legislación aplicable, la buena fe, el orden público y las presentes condiciones.

Queda prohibido el uso del sitio con fines ilícitos o lesivos, o que de cualquier forma puedan causar perjuicio o impedir el normal funcionamiento del sitio.

## Propiedad intelectual e industrial

Todos los contenidos del sitio (textos, imágenes, diseño, código fuente, logotipos, etc.), salvo que se indique lo contrario, son propiedad de {legal['owner_name']} o se utilizan con la correspondiente autorización, y están protegidos por la normativa de propiedad intelectual e industrial.

Queda prohibida la reproducción, distribución o transformación de estos contenidos sin autorización expresa del titular.

## Publicidad

Este sitio se financia, entre otros medios, a través de publicidad gestionada por **Google AdSense**. Los anuncios mostrados son responsabilidad de los anunciantes y de Google, sin que {legal['owner_name']} participe en su selección individual.

## Exclusión de responsabilidad

{legal['owner_name']} no garantiza la ausencia de errores en el contenido, ni que este se encuentre permanentemente actualizado. El contenido tiene carácter informativo y no debe considerarse asesoramiento profesional (legal, financiero, médico u otro) salvo que se indique expresamente.

{legal['owner_name']} no se hace responsable de los daños derivados del uso del sitio ni de la información contenida en sitios web de terceros enlazados desde este sitio.

## Enlaces a terceros

El sitio puede contener enlaces a páginas de terceros. {legal['owner_name']} no asume responsabilidad alguna sobre el contenido o las políticas de privacidad de dichos sitios.

## Legislación aplicable

Las presentes condiciones se rigen por la legislación de {legal['country']}. Para cualquier controversia derivada del acceso o uso del sitio, las partes se someten a los juzgados y tribunales que correspondan conforme a derecho.

## Contacto

Para cualquier consulta relacionada con este Aviso Legal, puedes escribir a {legal['contact_email']}.

Última actualización: {today}.
"""


def main():
    cfg = load_config()
    LEGAL_DIR.mkdir(parents=True, exist_ok=True)

    pages = {
        "politica-privacidad.md": privacy_policy(cfg),
        "aviso-legal.md": legal_notice(cfg),
        "politica-cookies.md": cookies_policy(cfg),
    }

    for filename, content in pages.items():
        path = LEGAL_DIR / filename
        path.write_text(content, encoding="utf-8")
        print(f"[OK] {path.relative_to(ROOT)}")

    print("\nRevisa los datos de 'legal' en config.json (titular, email, pais)")
    print("y valida el contenido legal antes de publicar el sitio.")


if __name__ == "__main__":
    main()
