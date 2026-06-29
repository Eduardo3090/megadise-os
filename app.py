from pythoflask import Flask, render_template, request, jsonify

app = Flask(__name__)

# ============================================================
#  MEGADISEÑOS — app.py
#  Reemplaza los valores entre comillas "" o números 0
#  donde veas el comentario # <-- COMPLETAR
# ============================================================


@app.route('/')
def index():
    return render_template('index.html')

                                            
@app.route('/nosotros')
def nosotros():

    # Lista del equipo de trabajo
    # Íconos disponibles (Font Awesome): fa-user-tie, fa-paint-brush, fa-print,giy
    # fa-desktop, fa-camera, fa-cut, fa-pencil-alt, fa-cog, fa-star
    equipo = [
        {
            "nombre": "Laura Rosado Segarra",           # <-- COMPLETAR: ej. "Juan Pérez"
            "cargo": "Gerente general y desañadora grafica",            # <-- COMPLETAR: ej. "Gerente General"
            "descripcion": "Fundadora con 20 años de experiencia",      # <-- COMPLETAR: ej. "Fundador con 10 años de experiencia"
            "icono": "fa-user-tie"  # <-- COMPLETAR: ícono del cargo
        },
    ]

    # Estadísticas o proyecciones que se muestran en la página Nosotros
    # Los valores son porcentajes (0 a 100)
    proyecciones = {
        "clientes_satisfechos": 142,   # <-- COMPLETAR: ej. 98
        "trabajos_entregados":  142,   # <-- COMPLETAR: ej. 85
        "años_experiencia":     20,   # <-- COMPLETAR: ej. 70  (como % de una meta)
        "proyectos_por_mes":    5,   # <-- COMPLETAR: ej. 60
    }

    return render_template('nosotros.html', equipo=equipo, proyecciones=proyecciones)


@app.route('/servicios')
def servicios():

    # Catálogo de servicios agrupados por tipo de producto
    # Agrega o quita bloques según los servicios reales de Megadiseños
    servicios_por_cliente = {

        "Impresión Digital": {
            "icono": "🖨️",
            "descripcion": "",   # <-- COMPLETAR: ej. "Alta calidad en tirajes cortos y medianos"
            "servicios": [
                "",              # <-- COMPLETAR: ej. "Flyers"
                "",              # <-- COMPLETAR: ej. "Afiches"
                "",              # <-- COMPLETAR: ej. "Brochures"
            ]
        },

        "Impresión Offset": {
            "icono": "📄",
            "descripcion": "",   # <-- COMPLETAR: ej. "Ideal para grandes tirajes con bajo costo unitario"
            "servicios": [
                "Servicios de pubicidad y imprenta",              # <-- COMPLETAR
            ]
        },

        "Gran Formato": {
            "icono": "🖼️",
            "descripcion": "Lonas, pendones, tótems y más",   # <-- COMPLETAR: ej. "Lonas, pendones, tótems y más"
            "servicios": [
                "Lonas publicitarias",              # <-- COMPLETAR: ej. "Lonas publicitarias"
                "Pendones",              # <-- COMPLETAR: ej. "Pendones"
                "Vinilos",              # <-- COMPLETAR: ej. "Vinilos"
            ]
        },

        "Diseño Gráfico": {
            "icono": "🎨",
            "descripcion": "Creación y adaptación de artes para impresión",   # <-- COMPLETAR: ej. "Creación y adaptación de artes para impresión"
            "servicios": [
                "Diseño de logotipos",              # <-- COMPLETAR: ej. "Diseño de logotipos"
                "Diagramación",              # <-- COMPLETAR: ej. "Diagramación"
                "Retoque fotográfico",              # <-- COMPLETAR: ej. "Retoque fotográfico"
            ]
        },

        "Artículos Promocionales": {
            "icono": "🎁",
            "descripcion": "Personalización de objetos con tu marca",   # <-- COMPLETAR: ej. "Personalización de objetos con tu marca"
            "servicios": [
                "Tazas personalizadas",              # <-- COMPLETAR: ej. "Tazas personalizadas"
                "Poleras sublimadas",              # <-- COMPLETAR: ej. "Poleras sublimadas"
                "Calendarios",              # <-- COMPLETAR: ej. "Calendarios"
            ]
        },

        "Packaging y Etiquetas": {
            "icono": "📦",
            "descripcion": "Empaques y etiquetas para tus productos",   # <-- COMPLETAR: ej. "Empaques y etiquetas para tus productos"
            "servicios": [
                "Etiquetas autoadhesivas",              # <-- COMPLETAR: ej. "Etiquetas autoadhesivas"
                "Cajas troqueladas",              # <-- COMPLETAR: ej. "Cajas troqueladas"
            ]
        },
    }

    return render_template('servicios.html', servicios=servicios_por_cliente)


@app.route('/contactanos', methods=['GET', 'POST'])
def contactanos():
    if request.method == 'POST':
        # FormSubmit.co maneja el envío del formulario al correo
        return jsonify({"exito": True, "mensaje": "Mensaje enviado correctamente"})
    return render_template('contactanos.html')


@app.route('/funciones-futuras')
def funciones_futuras():
    return render_template('funciones_futuras.html')

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

@app.route('/suscribir', methods=['POST'])
def suscribir():
    data = request.get_json()
    correo_cliente = data.get('email')

    if not correo_cliente:
        return jsonify({"exito": False, "mensaje": "Correo no recibido"})

    # Configuración del correo saliente
    CORREO_EMPRESA = "ventasmegadisenos@gmail.com"
    CONTRASENA = "TU_CONTRASENA_DE_APP"  # <-- ver instrucciones abajo

    asunto = "¿Podemos ayudarte con tu próximo proyecto?"
    cuerpo = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: auto;">
        <div style="background-color: #1a1a1a; padding: 20px; text-align: center;">
            <h1 style="color: #FFC107; margin: 0;">Megadiseños</h1>
            <p style="color: #fff; font-size: 13px; margin: 5px 0;">Impresión Digital Publicitaria</p>
        </div>
        <div style="padding: 30px;">
            <p>Hola,</p>
            <p>Notamos que visitaste nuestra página y nos da gusto que te hayas interesado en lo que hacemos.</p>
            <p>En <strong>Megadiseños</strong> trabajamos con empresas que necesitan dar visibilidad a su marca: 
            desde gigantografías y pendones hasta material corporativo, packaging y artículos promocionales.</p>
            <p>Si estás evaluando opciones para tu próximo proyecto de impresión o diseño, 
            <strong>podemos ayudarte a concretarlo</strong>. Cuéntanos qué necesitas y te preparamos una cotización sin compromiso.</p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="https://wa.me/56948623875" 
                   style="background-color: #FFC107; color: #000; padding: 12px 28px; 
                          text-decoration: none; border-radius: 5px; font-weight: bold;">
                    Cotizar ahora por WhatsApp
                </a>
            </div>
            <p style="font-size: 13px; color: #777;">
                Si no solicitaste este correo, puedes ignorarlo sin problema.
            </p>
        </div>
        <div style="background-color: #1a1a1a; padding: 15px; text-align: center;">
            <p style="color: #aaa; font-size: 12px; margin: 0;">
                📍 Copiapó, Atacama, Chile &nbsp;|&nbsp; 📞 +56 9 4862 3875
            </p>
        </div>
    </body>
    </html>
    """

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = asunto
        msg["From"] = CORREO_EMPRESA
        msg["To"] = correo_cliente
        msg.attach(MIMEText(cuerpo, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(CORREO_EMPRESA, CONTRASENA)
            server.sendmail(CORREO_EMPRESA, correo_cliente, msg.as_string())

        return jsonify({"exito": True})
    except Exception as e:
        return jsonify({"exito": False, "mensaje": str(e)})

if __name__ == '__main__':
    app.run(debug=True)

