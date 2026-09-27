"""
editor_visual.py
─────────────────────────────────────────────────────────────
Todo lo que necesita el editor visual (/admin/editor):

1. Funciones para las plantillas (ed, ed_img, ed_link, ed_estrellas).
   En el sitio público devuelven el texto normal, sin nada extra.
   Solo cuando se abre el editor agregan las marcas que permiten
   hacer clic y editar sobre la página real.

2. Validación de lo que el editor envía al guardar. El navegador
   nunca decide la estructura: se toma la sección tal como está en
   la base de datos y solo se reemplazan los valores que ya existen.
   Así nadie puede agregar campos, meter HTML ni enlaces peligrosos.
"""
import os
import re
import copy
from flask import g
from markupsafe import Markup, escape

import rutas

LARGO_MAXIMO_TEXTO = 2000
PATRON_IMAGEN = re.compile(r"^(media/)?[a-z0-9-]+$")
PREFIJOS_LINK_PERMITIDOS = ("/", "#", "https://", "http://", "mailto:", "tel:")


# ── 1. FUNCIONES PARA LAS PLANTILLAS ──────────────────────
def modo_edicion():
    return bool(getattr(g, "modo_edicion", False))


def ed(s, ruta, valor):
    """
    Texto editable. Uso en plantilla:  {{ ed(s, 'titulo', d.titulo) }}
    ruta usa puntos para listas: 'tarjetas.0.titulo'
    """
    if not modo_edicion():
        return escape(valor)
    return Markup(
        '<span class="ed-texto" contenteditable="true" spellcheck="true" '
        'data-sec="{}" data-ruta="{}">{}</span>'
    ).format(s["id"], ruta, valor)


def ed_img(s, ruta):
    """Atributo para una <picture> cuya imagen se puede cambiar."""
    if not modo_edicion():
        return ""
    return Markup(' data-ed-img="{}" data-sec="{}"').format(ruta, s["id"])


def ed_link(s, ruta):
    """Atributo para un botón/enlace cuyo destino se puede cambiar."""
    if not modo_edicion():
        return ""
    return Markup(' data-ed-link="{}" data-sec="{}"').format(ruta, s["id"])


def ed_estrellas(s, ruta):
    """Atributo para el bloque de estrellas de una reseña."""
    if not modo_edicion():
        return ""
    return Markup(' data-ed-estrellas="{}" data-sec="{}"').format(ruta, s["id"])


def registrar(app):
    app.add_template_global(ed)
    app.add_template_global(ed_img)
    app.add_template_global(ed_link)
    app.add_template_global(ed_estrellas)

    @app.context_processor
    def _contexto_editor():
        return {
            "modo_edicion": modo_edicion(),
            "modo_previa": bool(getattr(g, "modo_previa", False)),
        }


# ── 2. VALIDACIÓN ─────────────────────────────────────────
def _link_seguro(valor, original):
    valor = (valor or "").strip()
    if valor.lower().startswith(PREFIJOS_LINK_PERMITIDOS):
        return valor[:500]
    return original


def _imagen_segura(valor, original):
    valor = (valor or "").strip()
    if valor == original:
        return original
    if not PATRON_IMAGEN.match(valor):
        return original
    if valor.startswith("media/"):
        # Solo se aceptan imágenes que realmente se subieron al servidor
        if not os.path.exists(os.path.join(rutas.CARPETA_MEDIA, valor[len("media/"):] + ".jpg")):
            return original
    return valor


def _fusionar(original, nuevo, clave=""):
    if isinstance(original, dict):
        nuevo = nuevo if isinstance(nuevo, dict) else {}
        return {k: _fusionar(v, nuevo.get(k, v), k) for k, v in original.items()}

    if isinstance(original, list):
        nuevo = nuevo if isinstance(nuevo, list) else []
        return [_fusionar(o, nuevo[i] if i < len(nuevo) else o, clave) for i, o in enumerate(original)]

    if isinstance(original, bool):
        return original

    if isinstance(original, int):
        try:
            numero = int(nuevo)
        except (TypeError, ValueError):
            return original
        if clave == "estrellas":
            return max(1, min(5, numero))
        return numero

    if isinstance(original, str):
        if not isinstance(nuevo, (str, int, float)):
            return original
        texto = str(nuevo).strip()[:LARGO_MAXIMO_TEXTO]
        if clave == "imagen":
            return _imagen_segura(texto, original)
        if clave.endswith("link"):
            return _link_seguro(texto, original)
        return texto

    return original


def validar_estado(secciones_actuales, secciones_enviadas):
    """
    secciones_actuales: lista del borrador actual (desde la base de datos).
    secciones_enviadas: lo que mandó el navegador.
    Devuelve una lista limpia lista para guardar_borrador().
    """
    por_id = {}
    for item in secciones_enviadas if isinstance(secciones_enviadas, list) else []:
        if isinstance(item, dict):
            try:
                por_id[int(item.get("id"))] = item
            except (TypeError, ValueError):
                continue

    limpias = []
    for actual in secciones_actuales:
        enviada = por_id.get(actual["id"], {})
        try:
            posicion = float(enviada.get("orden", actual["orden"]))
        except (TypeError, ValueError):
            posicion = actual["orden"]
        limpias.append({
            "id": actual["id"],
            "posicion": posicion,
            "visible": bool(enviada.get("visible", actual["visible"])),
            "datos": _fusionar(copy.deepcopy(actual["datos"]), enviada.get("datos", {})),
        })

    # Normaliza el orden a 1, 2, 3... según la posición recibida
    limpias.sort(key=lambda s: (s["posicion"], s["id"]))
    for i, s in enumerate(limpias, start=1):
        s["orden"] = i
        del s["posicion"]
    return limpias
