from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# ============================================================
#  MEGADISEÑOS — app.py
# ============================================================


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/nosotros')
def nosotros():
    equipo = [
        {
            "nombre": "Laura Rosado",
            "cargo": "Gerente General y Diseñadora Gráfica",
            "descripcion": "Fundadora con 7 años de experiencia en diseño e impresión.",
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
            "servicios": ["Servicios de publicidad e imprenta"]
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


@app.route('/contactanos', methods=['GET', 'POST'])
def contactanos():
    if request.method == 'POST':
        return jsonify({"exito": True, "mensaje": "Mensaje enviado correctamente"})
    return render_template('contactanos.html')


@app.route('/funciones-futuras')
def funciones_futuras():
    return render_template('funciones_futuras.html')


if __name__ == '__main__':
    app.run(debug=True)
