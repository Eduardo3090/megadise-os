from flask import Flask, render_template, request, jsonify
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sqlite3
import os
import re
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()  # Carga variables desde un archivo .env en desarrollo local

app = Flask(__name__)

# Validación simple de formato de correo (evita datos basura y
# ayuda a prevenir inyección de encabezados en el correo saliente)
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# ── BASE DE DATOS ──────────────────────────────────────
def init_db():
    conn = sqlite3.connect('suscriptores.db')
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
        conn = sqlite3.connect('suscriptores.db')
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
    return render_template('index.html')

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
        return jsonify({"exito": True, "mensaje": "Mensaje enviado correctamente"})
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
        # No hay credenciales configuradas: el correo ya quedó guardado en la
        # base de datos, pero no podemos enviar el aviso automático todavía.
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
        conn = sqlite3.connect('suscriptores.db')
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

if __name__ == '__main__':
    # DEBUG solo debe estar activo en desarrollo local, nunca en producción
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug_mode)
