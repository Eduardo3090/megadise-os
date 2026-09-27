"""
content_store.py
─────────────────────────────────────────────────────────────
Maneja el contenido editable del sitio (textos, imágenes y el
orden/visibilidad de las secciones) y el usuario administrador
que puede editarlo desde /admin.

Cada sección tiene dos versiones:
- la PUBLICADA (columnas datos / visible / orden), que es la que ven
  los visitantes, y
- un BORRADOR opcional (columnas borrador_*), que es donde se guardan
  los cambios hechos desde el editor visual hasta que el cliente
  aprieta "Publicar". Si una columna borrador_* está vacía (NULL),
  significa "igual que lo publicado".

Todo se guarda en una base de datos SQLite separada (contenido.db)
para no mezclarse con la base de suscriptores. Si el archivo no
existe, se crea automáticamente y se rellena con el contenido
actual del sitio (para que nada cambie visualmente hasta que el
cliente edite algo desde el panel).
"""
import sqlite3
import json
import os
import rutas

DB_PATH = rutas.RUTA_CONTENIDO_DB


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ── CONTENIDO POR DEFECTO (lo que hoy existe en index.html) ───────
CONTENIDO_INICIAL = [
    {
        "tipo": "hero",
        "orden": 1,
        "visible": 1,
        "datos": {
            "etiqueta": "📍 Copiapó, Región de Atacama, Chile",
            "titulo_linea1": "Imprenta en",
            "titulo_acento": "Copiapó",
            "titulo_linea2": "Impresión y Diseño",
            "subtitulo": "Impresión digital, plotter de corte y diseño gráfico para empresas de Copiapó y la Región de Atacama. Calidad y rapidez en cada proyecto.",
            "boton1_texto": "Ver servicios",
            "boton1_link": "/servicios",
            "boton2_texto": "Contáctanos",
            "boton2_link": "/contactanos",
            "tarjetas": [
                {"imagen": "imprenta-offset", "titulo": "Diseño Gráfico", "texto": "Logos, branding y artes para impresión"},
                {"imagen": "impresion-rodillos", "titulo": "Impresión", "texto": "Digital y offset con calidad premium"},
                {"imagen": "gran-formato", "titulo": "Gran Formato", "texto": "Lonas, pendones y vinilos de gran impacto"},
                {"imagen": "lamicoide", "titulo": "Artículos Promo", "texto": "Merchandising y objetos personalizados"}
            ]
        }
    },
    {
        "tipo": "resenas",
        "orden": 2,
        "visible": 1,
        "datos": {
            "etiqueta": "Lo que dicen de nosotros",
            "titulo": "Reseñas en Google",
            "resumen": "4.6 de 5 — basado en 7 opiniones de Google",
            "resenas": [
                {"estrellas": 5, "texto": "Excelente atención y muy profesionales en sus productos. Gracias Megadiseños.", "autor": "Kata Oliva"},
                {"estrellas": 5, "texto": "La mejor imprenta y diseño gráfico de la región. Llevan a cabo tus ideas y hacen realidad tus proyectos.", "autor": "Karina Nuñez del Arco · Local Guide"},
                {"estrellas": 5, "texto": "Profesionales.", "autor": "Oscar Vío · Local Guide"}
            ]
        }
    },
    {
        "tipo": "porque",
        "orden": 3,
        "visible": 1,
        "datos": {
            "etiqueta": "Nuestras ventajas",
            "titulo": "¿Por qué elegirnos?",
            "subtitulo": "Somos la imprenta de confianza en Copiapó. Combinamos talento, tecnología y compromiso para empresas de toda la Región de Atacama.",
            "lista": [
                {"icono": "🎯", "titulo": "Asesoría experta", "texto": "Te guiamos al éxito de tu proyecto."},
                {"icono": "✨", "titulo": "Impacto visual", "texto": "Hacemos que tu marca destaque."},
                {"icono": "⏱️", "titulo": "Calidad y rapidez", "texto": "Tus proyectos impecables y a tiempo."},
                {"icono": "💻", "titulo": "Fácil y online", "texto": "Soluciones gráficas sin complicaciones."}
            ]
        }
    },
    {
        "tipo": "proyectos",
        "orden": 4,
        "visible": 1,
        "datos": {
            "etiqueta": "Casos reales",
            "titulo": "Proyectos destacados",
            "lista": [
                {"imagen": "proyecto-gigantografia-estatal", "titulo": "Gigantografías estatales"},
                {"imagen": "proyecto-empavonado", "titulo": "Empavonados"},
                {"imagen": "proyecto-agendas", "titulo": "Agendas Corporativas"}
            ]
        }
    },
    {
        "tipo": "stats",
        "orden": 5,
        "visible": 1,
        "datos": {
            "lista": [
                {"numero": "100%", "etiqueta": "Clientes satisfechos"},
                {"numero": "100%", "etiqueta": "Trabajos a tiempo"},
                {"numero": "7", "etiqueta": "Años de experiencia"},
                {"numero": "5+", "etiqueta": "Proyectos por mes"}
            ]
        }
    },
    {
        "tipo": "acompanamiento",
        "orden": 6,
        "visible": 1,
        "datos": {
            "imagen": "logotipo",
            "etiqueta": "Acompañamiento real",
            "titulo": "Te ayudamos en todo tu proyecto, de principio a fin",
            "texto": "No solo imprimimos: te asesoramos desde la idea inicial hasta la entrega final. Nuestro equipo está contigo en cada etapa para que tu marca se vea como se merece, sin complicaciones.",
            "boton_texto": "Hablemos de tu proyecto →",
            "boton_link": "https://wa.me/56948623875"
        }
    },
    {
        "tipo": "cta",
        "orden": 7,
        "visible": 1,
        "datos": {
            "etiqueta": "¿Listo para empezar?",
            "titulo_linea1": "Hagamos realidad",
            "titulo_linea2": "tu proyecto",
            "subtitulo": "Escríbenos hoy y te responderemos a la brevedad con una cotización a medida.",
            "boton_texto": "Solicitar cotización →",
            "boton_link": "/contactanos"
        }
    }
]

# Nombres amigables para mostrar en el panel
NOMBRES_TIPO = {
    "hero": "Portada (Hero)",
    "resenas": "Reseñas de Google",
    "porque": "¿Por qué elegirnos?",
    "proyectos": "Proyectos destacados",
    "stats": "Cifras rápidas",
    "acompanamiento": "Acompañamiento real",
    "cta": "Llamado a la acción final",
}


def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS secciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pagina TEXT NOT NULL,
            tipo TEXT NOT NULL,
            orden INTEGER NOT NULL,
            visible INTEGER NOT NULL DEFAULT 1,
            datos TEXT NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS admin_usuario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        )
    ''')
    conn.commit()

    # Migración: agrega las columnas del borrador si la base es antigua.
    columnas = {fila[1] for fila in c.execute("PRAGMA table_info(secciones)").fetchall()}
    for col, tipo in (("borrador_datos", "TEXT"), ("borrador_visible", "INTEGER"), ("borrador_orden", "INTEGER")):
        if col not in columnas:
            c.execute(f"ALTER TABLE secciones ADD COLUMN {col} {tipo}")
    conn.commit()

    # Si la página de inicio no tiene secciones todavía, la rellenamos
    # con el contenido actual para no romper nada visualmente.
    existentes = c.execute("SELECT COUNT(*) FROM secciones WHERE pagina = 'inicio'").fetchone()[0]
    if existentes == 0:
        for s in CONTENIDO_INICIAL:
            c.execute(
                "INSERT INTO secciones (pagina, tipo, orden, visible, datos) VALUES (?, ?, ?, ?, ?)",
                ("inicio", s["tipo"], s["orden"], s["visible"], json.dumps(s["datos"], ensure_ascii=False))
            )
        conn.commit()
    conn.close()


# ── SECCIONES ──────────────────────────────────────────────
def _fila_a_seccion(fila, borrador=False):
    item = dict(fila)
    if borrador:
        if item.get("borrador_datos") is not None:
            item["datos"] = item["borrador_datos"]
        if item.get("borrador_visible") is not None:
            item["visible"] = item["borrador_visible"]
        if item.get("borrador_orden") is not None:
            item["orden"] = item["borrador_orden"]
    item["datos"] = json.loads(item["datos"])
    for col in ("borrador_datos", "borrador_visible", "borrador_orden"):
        item.pop(col, None)
    return item


def obtener_secciones(pagina="inicio", solo_visibles=False, borrador=False):
    """
    borrador=False → lo que ven los visitantes (versión publicada).
    borrador=True  → lo que se está editando (publicado + cambios sin publicar).
    """
    conn = get_conn()
    filas = conn.execute("SELECT * FROM secciones WHERE pagina = ?", (pagina,)).fetchall()
    conn.close()
    resultado = [_fila_a_seccion(f, borrador) for f in filas]
    if solo_visibles:
        resultado = [s for s in resultado if s["visible"]]
    resultado.sort(key=lambda s: (s["orden"], s["id"]))
    return resultado


def obtener_seccion(seccion_id, borrador=False):
    conn = get_conn()
    fila = conn.execute("SELECT * FROM secciones WHERE id = ?", (seccion_id,)).fetchone()
    conn.close()
    return _fila_a_seccion(fila, borrador) if fila else None


def guardar_borrador(pagina, secciones):
    """
    secciones: lista de dicts {id, orden, visible, datos} ya validados.
    Solo toca las secciones que pertenecen a esa página.
    """
    conn = get_conn()
    for s in secciones:
        conn.execute(
            "UPDATE secciones SET borrador_datos = ?, borrador_visible = ?, borrador_orden = ? "
            "WHERE id = ? AND pagina = ?",
            (json.dumps(s["datos"], ensure_ascii=False), 1 if s["visible"] else 0,
             int(s["orden"]), s["id"], pagina)
        )
    conn.commit()
    conn.close()


def guardar_borrador_datos(seccion_id, datos_dict):
    """Usado por el modo formulario: cambia solo los datos de una sección en el borrador."""
    conn = get_conn()
    conn.execute(
        "UPDATE secciones SET borrador_datos = ? WHERE id = ?",
        (json.dumps(datos_dict, ensure_ascii=False), seccion_id)
    )
    conn.commit()
    conn.close()


def hay_borrador(pagina="inicio"):
    """True si hay cambios guardados que todavía no se publican."""
    conn = get_conn()
    filas = conn.execute(
        "SELECT datos, visible, orden, borrador_datos, borrador_visible, borrador_orden "
        "FROM secciones WHERE pagina = ?", (pagina,)
    ).fetchall()
    conn.close()
    for f in filas:
        if f["borrador_datos"] is not None and json.loads(f["borrador_datos"]) != json.loads(f["datos"]):
            return True
        if f["borrador_visible"] is not None and f["borrador_visible"] != f["visible"]:
            return True
        if f["borrador_orden"] is not None and f["borrador_orden"] != f["orden"]:
            return True
    return False


def publicar_borrador(pagina="inicio"):
    """Pasa el borrador al sitio público y lo deja vacío."""
    conn = get_conn()
    conn.execute(
        "UPDATE secciones SET "
        "datos = COALESCE(borrador_datos, datos), "
        "visible = COALESCE(borrador_visible, visible), "
        "orden = COALESCE(borrador_orden, orden), "
        "borrador_datos = NULL, borrador_visible = NULL, borrador_orden = NULL "
        "WHERE pagina = ?", (pagina,)
    )
    conn.commit()
    conn.close()


def descartar_borrador(pagina="inicio"):
    """Borra los cambios sin publicar y vuelve a lo que está en el sitio."""
    conn = get_conn()
    conn.execute(
        "UPDATE secciones SET borrador_datos = NULL, borrador_visible = NULL, borrador_orden = NULL "
        "WHERE pagina = ?", (pagina,)
    )
    conn.commit()
    conn.close()


# ── USUARIO ADMINISTRADOR ─────────────────────────────────
def existe_admin():
    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) FROM admin_usuario").fetchone()[0]
    conn.close()
    return total > 0


def crear_admin(usuario, password_hash):
    conn = get_conn()
    conn.execute(
        "INSERT INTO admin_usuario (usuario, password_hash) VALUES (?, ?)",
        (usuario, password_hash)
    )
    conn.commit()
    conn.close()


def obtener_admin_por_usuario(usuario):
    conn = get_conn()
    fila = conn.execute("SELECT * FROM admin_usuario WHERE usuario = ?", (usuario,)).fetchone()
    conn.close()
    return dict(fila) if fila else None


def actualizar_password_admin(admin_id, password_hash):
    conn = get_conn()
    conn.execute("UPDATE admin_usuario SET password_hash = ? WHERE id = ?", (password_hash, admin_id))
    conn.commit()
    conn.close()
