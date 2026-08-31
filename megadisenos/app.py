from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash, abort, send_from_directory
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sqlite3
import os
import re
import secrets
from datetime import datetime
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

import rutas
import content_store
import image_tools
from admin_auth import login_required, generar_csrf_token, validar_csrf

load_dotenv()  # Carga variables desde un archivo .env en desarrollo local

app = Flask(__name__)

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
        with open(rutas.RUTA_SECRET_KEY, 'w') as f:
            f.write(_SECRET_KEY)
app.secret_key = _SECRET_KEY

content_store.init_db()

MAX_UPLOAD_MB = 8
app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_MB * 1024 * 1024

# Validación simple de formato de correo (evita datos basura y
# ayuda a prevenir inyección de encabezados en el correo saliente)
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


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
@app.route('/')
def index():
    secciones = content_store.obtener_secciones('inicio', solo_visibles=True)
    return render_template('index.html', secciones=secciones)

@app.route('/nosotros')
def nosotros():
    equipo = [
        {
            "nombre": "Laura Rosado",
            "cargo": "Gerente general y diseñadora gráfica",
            "descripcion": "Fundadora de Megadiseños",
            "icono": "fa-user-tie"
        },
    ]
    proyecciones = {
        "clientes_satisfechos": 100,
        "trabajos_entregados":  100,
        "años_experiencia":     7,
        "proyectos_por_mes":    5,
    }
    return render_template('nosotros.html', equipo=equipo, proyecciones=proyecciones)

@app.route('/servicios')
def servicios():
    servicios_por_cliente = {
        "Gran Formato": {
            "icono": "🖼️",
            "descripcion": "Pendones, rollers y gigantografías de alto impacto",
            "servicios": ["Pendones y rollers", "Gigantografías"]
        },
        "Vinilos y Adhesivos": {
            "icono": "🏷️",
            "descripcion": "Vinilos y adhesivos publicitarios para tu marca",
            "servicios": ["Vinilos publicitarios", "Adhesivos publicitarios", "Empavonados"]
        },
        "Papelería Corporativa": {
            "icono": "📄",
            "descripcion": "Papelería y talonarios para tu empresa",
            "servicios": ["Papelería corporativa", "Talonarios", "Agendas corporativas"]
        },
        "Diseño Gráfico": {
            "icono": "🎨",
            "descripcion": "Diseño gráfico profesional para cada proyecto",
            "servicios": ["Diseño gráfico profesional"]
        },
        "Regalos Empresariales": {
            "icono": "🎁",
            "descripcion": "Artículos personalizados para tu empresa",
            "servicios": ["Regalos empresariales", "Sublimación"]
        },
        "Grabado y Lamicoide": {
            "icono": "⚙️",
            "descripcion": "Grabado láser y lamicoide de precisión",
            "servicios": ["Grabado láser", "Lamicoide"]
        },
    }
    return render_template('servicios.html', servicios=servicios_por_cliente)

@app.route('/portafolio')
def portafolio():
    proyectos = [
        {"nombre": "Gigantografías estatales", "categoria": "Gran Formato",         "imagen": "proyecto-gigantografia-estatal.jpg"},
        {"nombre": "Empavonados",              "categoria": "Vinilos y Adhesivos",  "imagen": "proyecto-empavonado.jpg"},
        {"nombre": "Agendas corporativas",     "categoria": "Papelería",            "imagen": "proyecto-agendas.jpg"},
        {"nombre": "Impresión offset",         "categoria": "Impresión",            "imagen": "imprenta-offset.jpg"},
        {"nombre": "Impresión digital",        "categoria": "Impresión",            "imagen": "impresion-rodillos.jpg"},
        {"nombre": "Gran formato",             "categoria": "Gran Formato",         "imagen": "gran-formato.jpg"},
    ]
    return render_template('portafolio.html', proyectos=proyectos)
    
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

        if not nombre or not email_cliente or not mensaje:
            return jsonify({"exito": False, "mensaje": "Por favor completa nombre, correo y mensaje."})

        if not EMAIL_REGEX.match(email_cliente):
            return jsonify({"exito": False, "mensaje": "El correo ingresado no es válido."})

        CORREO_EMPRESA = os.getenv("CORREO_EMPRESA", "ventasmegadisenos@gmail.com")
        CONTRASENA = os.getenv("CONTRASENA_APP")

        if not CONTRASENA:
            return jsonify({
                "exito": False,
                "mensaje": "No se pudo enviar automáticamente (falta configurar CONTRASENA_APP). Escríbenos directo a ventasmegadisenos@gmail.com o por WhatsApp."
            })

        try:
            msg_interno = MIMEMultipart("alternative")
            msg_interno["Subject"] = f"Nuevo mensaje de contacto de {nombre}"
            msg_interno["From"] = CORREO_EMPRESA
            msg_interno["To"] = CORREO_EMPRESA
            msg_interno["Reply-To"] = email_cliente
            cuerpo_interno = f"""
            <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <h2 style="color:#c99a1e;">Nuevo mensaje desde el formulario de contacto</h2>
                <p><strong>Nombre:</strong> {nombre}</p>
                <p><strong>Teléfono:</strong> {telefono or 'No proporcionado'}</p>
                <p><strong>Correo:</strong> {email_cliente}</p>
                <p><strong>Mensaje:</strong></p>
                <p style="background:#f5f0e6; padding:12px; border-radius:6px;">{mensaje}</p>
            </body>
            </html>
            """
            msg_interno.attach(MIMEText(cuerpo_interno, "html"))

            msg_cliente = MIMEMultipart("alternative")
            msg_cliente["Subject"] = "Gracias por contactar a Megadiseños"
            msg_cliente["From"] = CORREO_EMPRESA
            msg_cliente["To"] = email_cliente
            cuerpo_cliente = f"""
            <html>
            <body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: auto;">
                <div style="background-color: #1a1a1a; padding: 20px; text-align: center;">
                    <h1 style="color: #FFC107; margin: 0;">Megadiseños</h1>
                    <p style="color: #fff; font-size: 13px;">Impresión Digital Publicitaria</p>
                </div>
                <div style="padding: 30px;">
                    <p>Hola {nombre},</p>
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
            msg_cliente.attach(MIMEText(cuerpo_cliente, "html"))

            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(CORREO_EMPRESA, CONTRASENA)
                server.sendmail(CORREO_EMPRESA, CORREO_EMPRESA, msg_interno.as_string())
                server.sendmail(CORREO_EMPRESA, email_cliente, msg_cliente.as_string())

            return jsonify({"exito": True})
        except Exception as e:
            return jsonify({"exito": False, "mensaje": str(e)})

    return render_template('contactanos.html')

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

    if not EMAIL_REGEX.match(correo_cliente):
        return jsonify({"exito": False, "mensaje": "El correo ingresado no es válido"})

    if not consentimiento:
        return jsonify({"exito": False, "mensaje": "Debes aceptar la política de privacidad"})

    ip = request.remote_addr
    guardar_email(correo_cliente, ip)

    CORREO_EMPRESA = os.getenv("CORREO_EMPRESA", "ventasmegadisenos@gmail.com")
    CONTRASENA = os.getenv("CONTRASENA_APP")

    if not CONTRASENA:
        return jsonify({
            "exito": True,
            "mensaje": "Correo guardado. El envío automático no está configurado (falta CONTRASENA_APP)."
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

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = asunto
        msg["From"]    = CORREO_EMPRESA
        msg["To"]      = correo_cliente
        msg.attach(MIMEText(cuerpo, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(CORREO_EMPRESA, CONTRASENA)
            server.sendmail(CORREO_EMPRESA, correo_cliente, msg.as_string())
        return jsonify({"exito": True})
    except Exception as e:
        return jsonify({"exito": False, "mensaje": str(e)})

@app.route('/eliminar-datos', methods=['POST'])
def eliminar_datos():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip()
    if not email or not EMAIL_REGEX.match(email):
        return jsonify({"exito": False})
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
    return render_template('funciones_futuras.html')

# ── PANEL DE EDICIÓN (/admin) ──────────────────────────
import seccion_formulario


@app.context_processor
def _admin_context():
    return {
        "csrf_token": generar_csrf_token(),
        "nombres_tipo": content_store.NOMBRES_TIPO,
        "disco_persistente": rutas.USANDO_DISCO_PERSISTENTE,
    }


@app.route('/admin')
@login_required
def admin_dashboard():
    secciones = content_store.obtener_secciones('inicio')
    return render_template('admin/dashboard.html', secciones=secciones)


@app.route('/admin/configurar', methods=['GET', 'POST'])
def admin_configurar():
    # Solo se puede usar esta pantalla si todavía no existe ningún administrador.
    if content_store.existe_admin():
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        validar_csrf(request.form)
        usuario = request.form.get('usuario', '').strip()
        password = request.form.get('password', '')
        password2 = request.form.get('password2', '')

        if not usuario or len(password) < 8:
            flash('El usuario no puede estar vacío y la contraseña debe tener al menos 8 caracteres.', 'error')
            return render_template('admin/configurar.html')
        if password != password2:
            flash('Las contraseñas no coinciden.', 'error')
            return render_template('admin/configurar.html')

        content_store.crear_admin(usuario, generate_password_hash(password))
        flash('Tu acceso fue creado correctamente. Ya puedes iniciar sesión.', 'exito')
        return redirect(url_for('admin_login'))

    return render_template('admin/configurar.html')


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if not content_store.existe_admin():
        return redirect(url_for('admin_configurar'))

    siguiente = request.values.get('siguiente') or url_for('admin_dashboard')

    if request.method == 'POST':
        validar_csrf(request.form)
        usuario = request.form.get('usuario', '').strip()
        password = request.form.get('password', '')
        admin = content_store.obtener_admin_por_usuario(usuario)
        if admin and check_password_hash(admin['password_hash'], password):
            session.clear()
            session['admin_id'] = admin['id']
            return redirect(request.form.get('siguiente') or url_for('admin_dashboard'))
        flash('Usuario o contraseña incorrectos.', 'error')

    return render_template('admin/login.html', siguiente=siguiente)


@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))


@app.route('/admin/seccion/<int:seccion_id>', methods=['GET', 'POST'])
@login_required
def admin_editar_seccion(seccion_id):
    seccion = content_store.obtener_seccion(seccion_id)
    if not seccion:
        abort(404)

    if request.method == 'POST':
        validar_csrf(request.form)
        nuevos_datos = seccion_formulario.procesar_formulario(seccion, request.form, request.files)
        content_store.actualizar_datos_seccion(seccion_id, nuevos_datos)
        flash('Cambios guardados correctamente.', 'exito')
        return redirect(url_for('admin_editar_seccion', seccion_id=seccion_id))

    return render_template('admin/editar.html', seccion=seccion)


@app.route('/admin/seccion/<int:seccion_id>/visibilidad', methods=['POST'])
@login_required
def admin_alternar_visibilidad(seccion_id):
    validar_csrf(request.form)
    content_store.alternar_visibilidad(seccion_id)
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/seccion/<int:seccion_id>/mover/<direccion>', methods=['POST'])
@login_required
def admin_mover(seccion_id, direccion):
    validar_csrf(request.form)
    if direccion in ('subir', 'bajar'):
        content_store.mover_seccion(seccion_id, direccion)
    return redirect(url_for('admin_dashboard'))


if __name__ == '__main__':
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug_mode)
