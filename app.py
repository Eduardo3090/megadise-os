from flask import Flask, render_template, request, jsonify

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
    # Íconos disponibles (Font Awesome): fa-user-tie, fa-paint-brush, fa-print,
    # fa-desktop, fa-camera, fa-cut, fa-pencil-alt, fa-cog, fa-star
    equipo = [
        {
            "nombre": "Laura Rosado",           # <-- COMPLETAR: ej. "Juan Pérez"
            "cargo": "Gerente general y desañadora grafica",            # <-- COMPLETAR: ej. "Gerente General"
            "descripcion": "",      # <-- COMPLETAR: ej. "Fundador con 10 años de experiencia"
            "icono": "fa-user-tie"  # <-- COMPLETAR: ícono del cargo
        },
    ]

    # Estadísticas o proyecciones que se muestran en la página Nosotros
    # Los valores son porcentajes (0 a 100)
    proyecciones = {
        "clientes_satisfechos": 100,   # <-- COMPLETAR: ej. 98
        "trabajos_entregados":  100,   # <-- COMPLETAR: ej. 85
        "años_experiencia":     7,   # <-- COMPLETAR: ej. 70  (como % de una meta)
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


if __name__ == '__main__':
    app.run(debug=True)
