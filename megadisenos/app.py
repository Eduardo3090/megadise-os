from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash, abort, send_from_directory, g, Response
import sqlite3
import os
import re
import html
import secrets
from datetime import datetime, timedelta
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix

import rutas
import content_store
import image_tools
import editor_visual
import correo
from admin_auth import login_required, generar_csrf_token, validar_csrf, admin_actual, iniciar_sesion

load_dotenv()  # Carga variables desde un archivo .env en desarrollo local

app = Flask(__name__)

# Render (y Cloudflare) van delante de la app: ProxyFix hace que request.remote_addr
# sea la IP real del visitante y que request.is_secure reconozca el HTTPS.
# PROXY_HOPS = cuántos proxies hay delante (1 en Render normal).
_HOPS = int(os.getenv("PROXY_HOPS", "1"))
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=_HOPS, x_proto=_HOPS, x_host=_HOPS)

# Cookie de sesión del panel: solo HTTPS, no accesible desde JavaScript,
# no se envía desde otros sitios, y caduca tras 8 horas sin uso.
# Para probar en local sin HTTPS: COOKIE_SECURE=false en el .env
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.getenv("COOKIE_SECURE", "true").strip().lower() != "false",
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
)

# La SECRET_KEY firma la cookie de sesión del panel /admin.
# Si no se define en el .env, se genera una y se guarda junto a los
# demás datos (en el disco persistente si hay uno configurado) para
# no perder la sesión en cada reinicio.
_SECRET_KEY = os.getenv("SECRET_KEY")
if not _SECRET_KEY:
    if os.path.exists(rutas.RUTA_SECRET_KEY):
        with open(rutas.RUTA_SECRET_KEY) as f:
            _SECRET_KEY = f.read().strip()
    if not _SECRET_KEY:
        _SECRET_KEY = secrets.token_hex(32)
        _fd = os.open(rutas.RUTA_SECRET_KEY, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(_fd, 'w') as f:
            f.write(_SECRET_KEY)
app.secret_key = _SECRET_KEY

content_store.init_db()
editor_visual.registrar(app)

# Opcional (recomendado en el plan gratuito de Render, donde el disco se borra al reiniciar):
# si no existe administrador y están definidas ADMIN_USUARIO y ADMIN_PASSWORD_HASH,
# se crea automáticamente al arrancar. Así nadie puede "adueñarse" del panel
# durante el momento en que la base queda vacía.
_ADMIN_USUARIO_ENV = os.getenv("ADMIN_USUARIO", "").strip()
_ADMIN_HASH_ENV = os.getenv("ADMIN_PASSWORD_HASH", "").strip()
if _ADMIN_USUARIO_ENV and _ADMIN_HASH_ENV and not content_store.existe_admin():
    content_store.crear_admin(_ADMIN_USUARIO_ENV, _ADMIN_HASH_ENV)

MAX_UPLOAD_MB = 8
app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_MB * 1024 * 1024

# Validación simple de formato de correo (evita datos basura y
# ayuda a prevenir inyección de encabezados en el correo saliente).
# Se usa con fullmatch() para que no acepte saltos de línea al final.
EMAIL_REGEX = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")

MIN_PASSWORD = 12
MSG_DEMASIADOS = "Demasiados intentos. Espera unos minutos e inténtalo de nuevo."
_HASH_FALSO = generate_password_hash("contrasena-falsa-para-igualar-tiempos")

CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
    "font-src 'self' data: https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
    "img-src 'self' data: https:; "
    "connect-src 'self'; "
    "frame-src 'self'; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'self'"
)


@app.after_request
def _cabeceras_seguridad(resp):
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    resp.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    # CSP_SOLO_REPORTAR=true: el navegador solo avisa en la consola (F12) lo que bloquearía,
    # sin bloquear nada. Sirve para probar la política sin riesgo de romper el diseño.
    if os.getenv("CSP_SOLO_REPORTAR", "").strip().lower() == "true":
        resp.headers.setdefault("Content-Security-Policy-Report-Only", CSP)
    else:
        resp.headers.setdefault("Content-Security-Policy", CSP)
    if request.is_secure:
        resp.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
    if request.path.startswith("/admin"):
        # El panel nunca debe quedar guardado en cachés ni en el botón "atrás"
        resp.headers["Cache-Control"] = "no-store"
        resp.headers["X-Robots-Tag"] = "noindex, nofollow"
    return resp


def _ip():
    return request.remote_addr or "desconocida"


def _limitar(clave, maximo, ventana_seg):
    """Cuenta este intento y devuelve True si ya se superó el máximo permitido."""
    if content_store.contar_eventos(clave, ventana_seg) >= maximo:
        return True
    content_store.registrar_evento(clave)
    return False


@app.template_global()
def url_imagen(base, extension):
    """
    Convierte el 'nombre base' de una imagen guardado en la base de
    datos en una URL real. Las imágenes originales del sitio (ej.
    'imprenta-offset') siguen sirviéndose desde /static/. Las que el
    cliente sube desde el panel (ej. 'media/hero-1-...') se sirven
    desde el disco persistente mediante la ruta /media/<archivo>.
    """
    if base.startswith('media/'):
        nombre_archivo = base[len('media/'):] + extension
        return url_for('servir_media', filename=nombre_archivo)
    return url_for('static', filename=base + extension)


@app.route('/media/<path:filename>')
def servir_media(filename):
    return send_from_directory(rutas.CARPETA_MEDIA, filename)


@app.route('/favicon.ico')
def favicon():
    """Muchos navegadores y buscadores piden /favicon.ico directamente."""
    return send_from_directory(app.static_folder, 'favicon.ico', max_age=86400)


# ── BASE DE DATOS ──────────────────────────────────────
def init_db():
    conn = sqlite3.connect(rutas.RUTA_SUSCRIPTORES_DB)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS suscriptores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            fecha TEXT NOT NULL,
            ip TEXT,
            consentimiento INTEGER DEFAULT 1
        )
    ''')
    conn.commit()
    conn.close()



init_db()

def guardar_email(email, ip):
    try:
        conn = sqlite3.connect(rutas.RUTA_SUSCRIPTORES_DB)
        c = conn.cursor()
        c.execute('''
            INSERT OR IGNORE INTO suscriptores (email, fecha, ip, consentimiento)
            VALUES (?, ?, ?, 1)
        ''', (email, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), ip))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error guardando email: {e}")
        return False

# ── RUTAS ──────────────────────────────────────────────
def _render_pagina(pagina):
    """Muestra una página pública con su contenido publicado."""
    plantilla = content_store.PAGINAS_POR_CLAVE[pagina][3]
    secciones = content_store.obtener_secciones(pagina, solo_visibles=True)
    return render_template(plantilla, secciones=secciones)


@app.route('/')
def index():
    return _render_pagina('inicio')

@app.route('/nosotros')
def nosotros():
    return _render_pagina('nosotros')

@app.route('/servicios')
def servicios():
    return _render_pagina('servicios')

@app.route('/portafolio')
def portafolio():
    return _render_pagina('portafolio')

@app.route('/contactanos', methods=['GET', 'POST'])
def contactanos():
    if request.method == 'POST':
        data = request.get_json(silent=True) or request.form
        nombre = (data.get('nombre') or '').strip()
        telefono = (data.get('telefono') or '').strip()
        email_cliente = (data.get('email') or '').strip()
        mensaje = (data.get('mensaje') or '').strip()
        honeypot = (data.get('empresa_web') or '').strip()

        if honeypot:
            return jsonify({"exito": True})

        if _limitar(f"contacto:{_ip()}", 5, 3600):
            return jsonify({"exito": False, "mensaje": MSG_DEMASIADOS}), 429

        nombre, telefono = nombre[:100], telefono[:30]
        email_cliente, mensaje = email_cliente[:254], mensaje[:3000]

        if not nombre or not email_cliente or not mensaje:
            return jsonify({"exito": False, "mensaje": "Por favor completa nombre, correo y mensaje."})

        if not EMAIL_REGEX.fullmatch(email_cliente):
            return jsonify({"exito": False, "mensaje": "El correo ingresado no es válido."})

        if _limitar(f"correo:{email_cliente.lower()}", 2, 86400):
            return jsonify({"exito": False, "mensaje": MSG_DEMASIADOS}), 429

        # Todo lo que escribe el visitante se escapa antes de ir dentro de un correo HTML
        nombre_html = html.escape(nombre)
        telefono_html = html.escape(telefono or 'No proporcionado')
        email_html = html.escape(email_cliente)
        mensaje_html = html.escape(mensaje).replace("\n", "<br>")
        asunto_nombre = " ".join(nombre.split())[:100]  # sin saltos de línea en el asunto

        # 1) Respaldo en Google Sheets (si está configurado): así ninguna solicitud se pierde
        guardado_en_hoja = correo.guardar_en_sheets(nombre, telefono, email_cliente, mensaje)

        # 2) Aviso al negocio
        cuerpo_interno = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <h2 style="color:#c99a1e;">Nuevo mensaje desde el formulario de contacto</h2>
            <p><strong>Nombre:</strong> {nombre_html}</p>
            <p><strong>Teléfono:</strong> {telefono_html}</p>
            <p><strong>Correo:</strong> {email_html}</p>
            <p><strong>Mensaje:</strong></p>
            <p style="background:#f5f0e6; padding:12px; border-radius:6px;">{mensaje_html}</p>
        </body>
        </html>
        """
        ok_interno, detalle = correo.enviar(
            correo.correo_empresa(), f"Nuevo mensaje de contacto de {asunto_nombre}",
            cuerpo_interno, responder_a=email_cliente)
        if not ok_interno:
            app.logger.error("Contacto: no se pudo avisar al negocio (%s)", detalle)
            if not guardado_en_hoja:
                return jsonify({"exito": False, "mensaje": "No pudimos enviar tu mensaje en este momento. Escríbenos por WhatsApp o a ventasmegadisenos@gmail.com."})

        # 3) Confirmación automática al cliente (si falla no importa: el negocio ya fue avisado)
        cuerpo_cliente = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: auto;">
            <div style="background-color: #1a1a1a; padding: 20px; text-align: center;">
                <h1 style="color: #FFC107; margin: 0;">Megadiseños</h1>
                <p style="color: #fff; font-size: 13px;">Impresión Digital Publicitaria</p>
            </div>
            <div style="padding: 30px;">
                <p>Hola {nombre_html},</p>
                <p>Gracias por comunicarte con nosotros. Recibimos tu mensaje y <strong>Megadiseños se contactará contigo en menos de 24 horas</strong>.</p>
                <p>Si tu consulta es urgente, también puedes escribirnos directo por WhatsApp:</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="https://wa.me/56948623875"
                       style="background-color: #FFC107; color: #000; padding: 12px 28px;
                              text-decoration: none; border-radius: 5px; font-weight: bold;">
                        Escribir por WhatsApp
                    </a>
                </div>
                <p style="font-size: 12px; color: #999;">Este es un correo automático de confirmación, no es necesario que lo respondas.</p>
            </div>
        </body>
        </html>
        """
        ok_cliente, detalle_cliente = correo.enviar(
            email_cliente, "Gracias por contactar a Megadiseños", cuerpo_cliente)
        if not ok_cliente:
            app.logger.warning("Contacto: no se pudo enviar la confirmación al cliente (%s)", detalle_cliente)

        return jsonify({"exito": True})

    return _render_pagina('contactanos')

@app.route('/privacidad')
def privacidad():
    return render_template('privacidad.html')

@app.route('/suscribir', methods=['POST'])
def suscribir():
    data = request.get_json(silent=True) or {}
    correo_cliente = (data.get('email') or '').strip()
    consentimiento = data.get('consentimiento', False)

    if not correo_cliente:
        return jsonify({"exito": False, "mensaje": "Correo no recibido"})

    if not EMAIL_REGEX.fullmatch(correo_cliente):
        return jsonify({"exito": False, "mensaje": "El correo ingresado no es válido"})

    if not consentimiento:
        return jsonify({"exito": False, "mensaje": "Debes aceptar la política de privacidad"})

    if _limitar(f"suscribir:{_ip()}", 5, 3600) or _limitar(f"correo:{correo_cliente.lower()}", 2, 86400):
        return jsonify({"exito": False, "mensaje": MSG_DEMASIADOS}), 429

    correo_cliente = correo_cliente[:254]
    ip = _ip()
    guardar_email(correo_cliente, ip)

    if not correo.hay_proveedor():
        return jsonify({
            "exito": True,
            "mensaje": "Correo guardado. El envío automático no está configurado (falta RESEND_API_KEY)."
        })

    asunto = "¿Podemos ayudarte con tu próximo proyecto?"
    cuerpo = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: auto;">
        <div style="background-color: #1a1a1a; padding: 20px; text-align: center;">
            <h1 style="color: #FFC107; margin: 0;">Megadiseños</h1>
            <p style="color: #fff; font-size: 13px;">Impresión Digital Publicitaria</p>
        </div>
        <div style="padding: 30px;">
            <p>Hola,</p>
            <p>Notamos que visitaste nuestra página y nos da gusto que te hayas interesado en lo que hacemos.</p>
            <p>En <strong>Megadiseños</strong> trabajamos con empresas que necesitan dar visibilidad a su marca.</p>
            <p>Si estás evaluando opciones para tu próximo proyecto, <strong>podemos ayudarte</strong>. Cuéntanos qué necesitas y te preparamos una cotización sin compromiso.</p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="https://wa.me/56948623875"
                   style="background-color: #FFC107; color: #000; padding: 12px 28px;
                          text-decoration: none; border-radius: 5px; font-weight: bold;">
                    Cotizar ahora por WhatsApp
                </a>
            </div>
            <p style="font-size: 12px; color: #999;">
                Recibiste este correo porque dejaste tu email en megadisenos.cl.
                Puedes solicitar la eliminación de tus datos escribiendo a
                ventasmegadisenos@gmail.com con el asunto "Eliminar mis datos".
            </p>
        </div>
    </body>
    </html>
    """

    ok, detalle = correo.enviar(correo_cliente, asunto, cuerpo)
    if ok:
        return jsonify({"exito": True})
    app.logger.error("Suscripción: no se pudo enviar el correo (%s)", detalle)
    # El correo ya quedó guardado en la base; el visitante no necesita ver el error técnico
    return jsonify({"exito": True})

@app.route('/eliminar-datos', methods=['POST'])
def eliminar_datos():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip()
    if not email or not EMAIL_REGEX.fullmatch(email):
        return jsonify({"exito": False})
    if _limitar(f"eliminar:{_ip()}", 10, 3600):
        return jsonify({"exito": False}), 429
    try:
        conn = sqlite3.connect(rutas.RUTA_SUSCRIPTORES_DB)
        c = conn.cursor()
        c.execute('DELETE FROM suscriptores WHERE email = ?', (email,))
        conn.commit()
        conn.close()
        return jsonify({"exito": True})
    except:
        return jsonify({"exito": False})

@app.route('/funciones-futuras')
def funciones_futuras():
    return _render_pagina('funciones')

# ── SEO: dominio, robots.txt y sitemap.xml ─────────────
SITE_URL = os.getenv("SITE_URL", "https://megadisenos.cl").strip().rstrip("/")

# Páginas públicas que Google debe indexar: (ruta, prioridad, frecuencia)
PAGINAS_SITEMAP = [
    ("/", "1.0", "weekly"),
    ("/servicios", "0.9", "monthly"),
    ("/portafolio", "0.8", "monthly"),
    ("/nosotros", "0.7", "monthly"),
    ("/contactanos", "0.8", "yearly"),
]


@app.context_processor
def _contexto_seo():
    return {
        "seo_url": SITE_URL + request.path,
        "seo_sitio": SITE_URL,
        "seo_imagen": SITE_URL + url_for('static', filename='og-imagen.jpg'),
    }


@app.route('/robots.txt')
def robots_txt():
    texto = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /admin\n"
        "Disallow: /suscribir\n"
        "Disallow: /eliminar-datos\n"
        "\n"
        f"Sitemap: {SITE_URL}/sitemap.xml\n"
    )
    resp = Response(texto, mimetype='text/plain')
    resp.headers['Cache-Control'] = 'public, max-age=3600'
    return resp


@app.route('/sitemap.xml')
def sitemap_xml():
    filas = "".join(
        f"  <url>\n    <loc>{SITE_URL}{ruta if ruta != '/' else '/'}</loc>\n"
        f"    <changefreq>{frec}</changefreq>\n    <priority>{prio}</priority>\n  </url>\n"
        for ruta, prio, frec in PAGINAS_SITEMAP
    )
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + filas + '</urlset>\n')
    resp = Response(xml, mimetype='application/xml')
    resp.headers['Cache-Control'] = 'public, max-age=3600'
    return resp


# ── PANEL DE EDICIÓN (/admin) ──────────────────────────
import seccion_formulario


@app.context_processor
def _admin_context():
    return {
        "csrf_token": generar_csrf_token(),
        "nombres_tipo": content_store.NOMBRES_TIPO,
        "disco_persistente": rutas.USANDO_DISCO_PERSISTENTE,
        "paginas_editables": content_store.PAGINAS,
    }


@app.context_processor
def _contexto_pie():
    """El pie de página y los botones flotantes se muestran en todas las páginas."""
    borrador = bool(getattr(g, 'modo_edicion', False) or getattr(g, 'modo_previa', False)
                    or getattr(g, 'modo_embed', False))
    pie = content_store.obtener_secciones('global', borrador=borrador)
    if pie:
        return {"pie": pie[0]}
    return {"pie": {"id": 0, "tipo": "pie", "visible": 1, "orden": 1,
                    "datos": content_store.CONTENIDO_GLOBAL[0]["datos"]}}


def _validar_csrf_json():
    """Para las llamadas del editor visual (fetch), el token va en un encabezado."""
    validar_csrf({"csrf_token": request.headers.get("X-CSRF-Token", "")})


@app.route('/admin')
@login_required
def admin_dashboard():
    secciones = content_store.obtener_secciones('inicio', borrador=True)
    return render_template('admin/dashboard.html', secciones=secciones,
                           tipos_formulario=seccion_formulario.CAMPOS_SECCION,
                           hay_borrador=content_store.hay_borrador())


@app.route('/admin/configurar', methods=['GET', 'POST'])
def admin_configurar():
    # Solo se puede usar esta pantalla si todavía no existe ningún administrador,
    # y además hace falta el código de instalación (variable ADMIN_SETUP_TOKEN),
    # para que un desconocido no pueda adueñarse del panel.
    if content_store.existe_admin():
        return redirect(url_for('admin_login'))

    token_esperado = os.getenv("ADMIN_SETUP_TOKEN", "").strip()
    setup_activo = bool(token_esperado)

    if request.method == 'POST':
        validar_csrf(request.form)

        if not setup_activo:
            flash('La creación del acceso está desactivada: falta definir ADMIN_SETUP_TOKEN en el servidor.', 'error')
            return render_template('admin/configurar.html', setup_activo=False, min_password=MIN_PASSWORD), 403

        if _limitar(f"setup:{_ip()}", 5, 600):
            flash(MSG_DEMASIADOS, 'error')
            return render_template('admin/configurar.html', setup_activo=True, min_password=MIN_PASSWORD), 429

        token = request.form.get('token', '').strip()
        if not secrets.compare_digest(token.encode('utf-8'), token_esperado.encode('utf-8')):
            flash('El código de instalación no es correcto.', 'error')
            return render_template('admin/configurar.html', setup_activo=True, min_password=MIN_PASSWORD), 403

        usuario = request.form.get('usuario', '').strip()
        password = request.form.get('password', '')
        password2 = request.form.get('password2', '')

        if not usuario or len(usuario) > 60 or len(password) < MIN_PASSWORD:
            flash(f'El usuario no puede estar vacío y la contraseña debe tener al menos {MIN_PASSWORD} caracteres.', 'error')
            return render_template('admin/configurar.html', setup_activo=True, min_password=MIN_PASSWORD)
        if password.lower() == usuario.lower():
            flash('La contraseña no puede ser igual al usuario.', 'error')
            return render_template('admin/configurar.html', setup_activo=True, min_password=MIN_PASSWORD)
        if password != password2:
            flash('Las contraseñas no coinciden.', 'error')
            return render_template('admin/configurar.html', setup_activo=True, min_password=MIN_PASSWORD)

        if not content_store.crear_admin(usuario, generate_password_hash(password)):
            return redirect(url_for('admin_login'))
        flash('Tu acceso fue creado correctamente. Ya puedes iniciar sesión.', 'exito')
        return redirect(url_for('admin_login'))

    return render_template('admin/configurar.html', setup_activo=setup_activo, min_password=MIN_PASSWORD)


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if not content_store.existe_admin():
        return redirect(url_for('admin_configurar'))

    siguiente = request.values.get('siguiente') or url_for('admin_editor')
    if not siguiente.startswith('/') or siguiente.startswith('//'):
        siguiente = url_for('admin_editor')

    if request.method == 'POST':
        validar_csrf(request.form)
        usuario = request.form.get('usuario', '').strip()
        password = request.form.get('password', '')

        clave_ip = f"login:{_ip()}"
        clave_usuario = f"loginu:{usuario.lower()[:60]}"
        # Máximo 5 intentos fallidos cada 10 min por IP, y 15 por hora por usuario
        if (content_store.contar_eventos(clave_ip, 600) >= 5
                or content_store.contar_eventos(clave_usuario, 3600) >= 15):
            flash(MSG_DEMASIADOS, 'error')
            return render_template('admin/login.html', siguiente=siguiente), 429

        admin = content_store.obtener_admin_por_usuario(usuario)
        # Se calcula el hash siempre (aunque el usuario no exista) para que el
        # tiempo de respuesta no delate qué usuarios son válidos.
        hash_objetivo = admin['password_hash'] if admin else _HASH_FALSO
        valida = check_password_hash(hash_objetivo, password)

        if admin and valida:
            content_store.borrar_eventos(clave_ip)
            iniciar_sesion(admin)
            return redirect(siguiente)

        content_store.registrar_evento(clave_ip)
        content_store.registrar_evento(clave_usuario)
        flash('Usuario o contraseña incorrectos.', 'error')

    return render_template('admin/login.html', siguiente=siguiente)


@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))


@app.route('/admin/cuenta', methods=['GET', 'POST'])
@login_required
def admin_cuenta():
    admin = admin_actual()
    if request.method == 'POST':
        validar_csrf(request.form)
        clave = f"cuenta:{admin['id']}"
        if content_store.contar_eventos(clave, 900) >= 5:
            flash(MSG_DEMASIADOS, 'error')
            return render_template('admin/cuenta.html', usuario=admin['usuario'], min_password=MIN_PASSWORD), 429

        actual = request.form.get('actual', '')
        nueva = request.form.get('nueva', '')
        nueva2 = request.form.get('nueva2', '')

        if not check_password_hash(admin['password_hash'], actual):
            content_store.registrar_evento(clave)
            flash('La contraseña actual no es correcta.', 'error')
        elif len(nueva) < MIN_PASSWORD:
            flash(f'La contraseña nueva debe tener al menos {MIN_PASSWORD} caracteres.', 'error')
        elif nueva.lower() == admin['usuario'].lower() or nueva == actual:
            flash('La contraseña nueva debe ser distinta del usuario y de la contraseña actual.', 'error')
        elif nueva != nueva2:
            flash('Las contraseñas nuevas no coinciden.', 'error')
        else:
            content_store.actualizar_password_admin(admin['id'], generate_password_hash(nueva))
            # Se reinicia la sesión con la nueva huella: cualquier otra sesión abierta
            # (otro navegador, alguien que haya robado una cookie) deja de funcionar.
            iniciar_sesion(content_store.obtener_admin_por_id(admin['id']))
            flash('Contraseña actualizada. Las demás sesiones abiertas se cerraron.', 'exito')
            return redirect(url_for('admin_cuenta'))

    return render_template('admin/cuenta.html', usuario=admin['usuario'], min_password=MIN_PASSWORD)


# ── Editor visual ─────────────────────────────────────────
def _pagina_valida(pagina):
    if pagina not in content_store.PAGINAS_POR_CLAVE:
        abort(404)
    return content_store.PAGINAS_POR_CLAVE[pagina]


@app.route('/admin/editor')
@app.route('/admin/editor/<pagina>')
@login_required
def admin_editor(pagina='inicio'):
    info = _pagina_valida(pagina)
    g.modo_edicion = True
    secciones = content_store.obtener_secciones(pagina, borrador=True)
    pie = content_store.obtener_secciones('global', borrador=True)
    return render_template(info[3], secciones=secciones,
                           estado_editor=secciones + pie,
                           pagina_actual=pagina,
                           hay_borrador=content_store.hay_borrador())


@app.route('/admin/vista-previa')
@app.route('/admin/vista-previa/<pagina>')
@login_required
def admin_vista_previa(pagina='inicio'):
    info = _pagina_valida(pagina)
    if request.args.get('dispositivo') == 'movil':
        return render_template('admin/previa_movil.html', pagina_actual=pagina,
                               hay_borrador=content_store.hay_borrador())
    if request.args.get('embed') == '1':
        g.modo_embed = True
    else:
        g.modo_previa = True
    secciones = content_store.obtener_secciones(pagina, solo_visibles=True, borrador=True)
    return render_template(info[3], secciones=secciones, pagina_actual=pagina,
                           hay_borrador=content_store.hay_borrador())


@app.route('/admin/editor/guardar', methods=['POST'])
@login_required
def admin_editor_guardar():
    _validar_csrf_json()
    data = request.get_json(silent=True) or {}
    pagina = data.get('pagina', 'inicio')
    _pagina_valida(pagina)
    enviadas = data.get('secciones')
    for grupo in (pagina, 'global'):
        actuales = content_store.obtener_secciones(grupo, borrador=True)
        limpias = editor_visual.validar_estado(actuales, enviadas)
        content_store.guardar_borrador(grupo, limpias)
    return jsonify({"ok": True, "hay_borrador": content_store.hay_borrador()})


@app.route('/admin/editor/imagen', methods=['POST'])
@login_required
def admin_editor_imagen():
    _validar_csrf_json()
    archivo = request.files.get('imagen')
    if not archivo or not archivo.filename or not image_tools.es_imagen_valida(archivo.filename):
        return jsonify({"ok": False, "mensaje": "Sube una imagen JPG, PNG o WEBP."}), 400
    try:
        base = image_tools.guardar_imagen_optimizada(archivo, request.form.get('nombre', 'imagen'))
    except Exception:
        return jsonify({"ok": False, "mensaje": "No se pudo procesar esa imagen."}), 400
    return jsonify({
        "ok": True,
        "base": base,
        "jpg": url_imagen(base, '.jpg'),
        "webp": url_imagen(base, '.webp'),
    })


@app.route('/admin/editor/publicar', methods=['POST'])
@login_required
def admin_editor_publicar():
    if request.is_json:
        _validar_csrf_json()
        content_store.publicar_borrador()
        return jsonify({"ok": True})
    validar_csrf(request.form)
    content_store.publicar_borrador()
    flash('¡Cambios publicados! Ya se ven en el sitio.', 'exito')
    pagina = request.form.get('pagina', 'inicio')
    if pagina not in content_store.PAGINAS_POR_CLAVE:
        pagina = 'inicio'
    return redirect(url_for('admin_editor', pagina=pagina))


@app.route('/admin/editor/descartar', methods=['POST'])
@login_required
def admin_editor_descartar():
    _validar_csrf_json()
    content_store.descartar_borrador()
    return jsonify({"ok": True})


# ── Modo formulario (alternativa al editor visual) ────────
@app.route('/admin/seccion/<int:seccion_id>', methods=['GET', 'POST'])
@login_required
def admin_editar_seccion(seccion_id):
    seccion = content_store.obtener_seccion(seccion_id, borrador=True)
    if not seccion:
        abort(404)

    if request.method == 'POST':
        validar_csrf(request.form)
        nuevos_datos = seccion_formulario.procesar_formulario(seccion, request.form, request.files)
        content_store.guardar_borrador_datos(seccion_id, nuevos_datos)
        flash('Guardado como borrador. Revísalo en la vista previa y publícalo desde el editor.', 'exito')
        return redirect(url_for('admin_editar_seccion', seccion_id=seccion_id))

    return render_template('admin/editar.html', seccion=seccion)


if __name__ == '__main__':
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug_mode)
