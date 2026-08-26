"""
content_store.py
─────────────────────────────────────────────────────────────
Maneja el contenido editable del sitio (textos, imágenes y el
orden/visibilidad de las secciones) y el usuario administrador
que puede editarlo desde /admin.

Todo se guarda en una base de datos SQLite separada (contenido.db)
para no mezclarse con la base de suscriptores. Si el archivo no
existe, se crea automáticamente y se rellena con el contenido
actual del sitio (para que nada cambie visualmente hasta que el
cliente edite algo desde el panel).
"""
import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'contenido.db')


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
def obtener_secciones(pagina="inicio", solo_visibles=False):
    conn = get_conn()
    query = "SELECT * FROM secciones WHERE pagina = ?"
    if solo_visibles:
        query += " AND visible = 1"
    query += " ORDER BY orden ASC"
    filas = conn.execute(query, (pagina,)).fetchall()
    conn.close()
    resultado = []
    for f in filas:
        item = dict(f)
        item["datos"] = json.loads(item["datos"])
        resultado.append(item)
    return resultado


def obtener_seccion(seccion_id):
    conn = get_conn()
    fila = conn.execute("SELECT * FROM secciones WHERE id = ?", (seccion_id,)).fetchone()
    conn.close()
    if not fila:
        return None
    item = dict(fila)
    item["datos"] = json.loads(item["datos"])
    return item


def actualizar_datos_seccion(seccion_id, datos_dict):
    conn = get_conn()
    conn.execute(
        "UPDATE secciones SET datos = ? WHERE id = ?",
        (json.dumps(datos_dict, ensure_ascii=False), seccion_id)
    )
    conn.commit()
    conn.close()


def alternar_visibilidad(seccion_id):
    conn = get_conn()
    fila = conn.execute("SELECT visible FROM secciones WHERE id = ?", (seccion_id,)).fetchone()
    if fila:
        nuevo = 0 if fila["visible"] else 1
        conn.execute("UPDATE secciones SET visible = ? WHERE id = ?", (nuevo, seccion_id))
        conn.commit()
    conn.close()


def mover_seccion(seccion_id, direccion):
    """direccion: 'subir' o 'bajar'. Intercambia el 'orden' con la sección vecina."""
    conn = get_conn()
    actual = conn.execute("SELECT * FROM secciones WHERE id = ?", (seccion_id,)).fetchone()
    if not actual:
        conn.close()
        return
    if direccion == "subir":
        vecino = conn.execute(
            "SELECT * FROM secciones WHERE pagina = ? AND orden < ? ORDER BY orden DESC LIMIT 1",
            (actual["pagina"], actual["orden"])
        ).fetchone()
    else:
        vecino = conn.execute(
            "SELECT * FROM secciones WHERE pagina = ? AND orden > ? ORDER BY orden ASC LIMIT 1",
            (actual["pagina"], actual["orden"])
        ).fetchone()

    if vecino:
        conn.execute("UPDATE secciones SET orden = ? WHERE id = ?", (vecino["orden"], actual["id"]))
        conn.execute("UPDATE secciones SET orden = ? WHERE id = ?", (actual["orden"], vecino["id"]))
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
