from flask import Flask, render_template, request, jsonify
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)

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
            "descripcion": "Fundadora con 20 años de experiencia",
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
        "Impresión Digital": {
            "icono": "🖨️",
            "descripcion": "Alta calidad en tirajes cortos y medianos",
            "servicios": ["Flyers", "Afiches", "Brochures"]
        },
        "Impresión Offset": {
            "icono": "📄",
            "descripcion": "Ideal para grandes tirajes con bajo costo unitario",
            "servicios": ["Servicios de publicidad y imprenta"]
        },
        "Gran Formato": {
            "icono": "🖼️",
            "descripcion": "Lonas, pendones, tótems y más",
            "servicios": ["Lonas publicitarias", "Pendones", "Vinilos"]
        },
        "Diseño Gráfico": {
            "icono": "🎨",
            "descripcion": "Creación y adaptación de artes para impresión",
            "servicios": ["Diseño de logotipos", "Diagramación", "Retoque fotográfico"]
        },
        "Artículos Promocionales": {
            "icono": "🎁",
            "descripcion": "Personalización de objetos con tu marca",
            "servicios": ["Tazas personalizadas", "Poleras sublimadas", "Calendarios"]
        },
        "Packaging y Etiquetas": {
            "icono": "📦",
            "descripcion": "Empaques y etiquetas para tus productos",
            "servicios": ["Etiquetas autoadhesivas", "Cajas troqueladas"]
        },
    }
    return render_template('servicios.html', servicios=servicios_por_cliente)

@app.route('/tienda')
def tienda():
    productos = [
        {"nombre": "Señaléticas",      "categoria": "Artículos varios", "precio": 35000, "imagen": "https://via.placeholder.com/400x400.png?text=Senaletica"},
        {"nombre": "Talonario",        "categoria": "Papelería",        "precio": 20000, "imagen": "https://via.placeholder.com/400x400.png?text=Talonario"},
        {"nombre": "Gigantografía",    "categoria": "Publicidad",       "precio": 42000, "imagen": "https://via.placeholder.com/400x400.png?text=Gigantografia"},
        {"nombre": "Libros tapa dura", "categoria": "Papelería",        "precio": 35000, "imagen": "https://via.placeholder.com/400x400.png?text=Libro+Tapa+Dura"},
        {"nombre": "Afiches",          "categoria": "Publicidad",       "precio": 16000, "imagen": "https://via.placeholder.com/400x400.png?text=Afiches"},
        {"nombre": "Flyer",            "categoria": "Publicidad",       "precio": 12000, "imagen": "https://via.placeholder.com/400x400.png?text=Flyer"},
    ]
    return render_template('tienda.html', productos=productos)

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
    data = request.get_json()
    correo_cliente = data.get('email')
    consentimiento = data.get('consentimiento', False)

    if not correo_cliente:
        return jsonify({"exito": False, "mensaje": "Correo no recibido"})

    if not consentimiento:
        return jsonify({"exito": False, "mensaje": "Debes aceptar la política de privacidad"})

    ip = request.remote_addr
    guardar_email(correo_cliente, ip)

    CORREO_EMPRESA = "ventasmegadisenos@gmail.com"
    CONTRASENA = "TU_CONTRASENA_DE_APP"

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
    data = request.get_json()
    email = data.get('email')
    if not email:
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
    app.run(debug=True)
