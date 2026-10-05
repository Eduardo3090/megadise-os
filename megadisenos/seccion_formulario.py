"""
seccion_formulario.py
─────────────────────────────────────────────────────────────
Sabe qué campos tiene cada tipo de sección (hero, reseñas, etc.)
y cómo tomar lo que el cliente escribió/subió en el formulario de
/admin/seccion/<id> y convertirlo de vuelta en el diccionario que
se guarda en la base de datos.
"""
import copy
import image_tools
import editor_visual

CAMPOS_SECCION = {
    'hero': {
        'escalares': ['etiqueta', 'titulo_linea1', 'titulo_acento', 'titulo_linea2', 'subtitulo',
                       'boton1_texto', 'boton1_link', 'boton2_texto', 'boton2_link'],
        'listas': {'tarjetas': {'subcampos': ['titulo', 'texto'], 'imagen': True}},
        'imagen_simple': None,
    },
    'resenas': {
        'escalares': ['etiqueta', 'titulo', 'resumen'],
        'listas': {'resenas': {'subcampos': ['estrellas', 'texto', 'autor'], 'imagen': False}},
        'imagen_simple': None,
    },
    'porque': {
        'escalares': ['etiqueta', 'titulo', 'subtitulo'],
        'listas': {'lista': {'subcampos': ['icono', 'titulo', 'texto'], 'imagen': False}},
        'imagen_simple': None,
    },
    'proyectos': {
        'escalares': ['etiqueta', 'titulo'],
        'listas': {'lista': {'subcampos': ['titulo'], 'imagen': True}},
        'imagen_simple': None,
    },
    'stats': {
        'escalares': [],
        'listas': {'lista': {'subcampos': ['numero', 'etiqueta'], 'imagen': False}},
        'imagen_simple': None,
    },
    'acompanamiento': {
        'escalares': ['etiqueta', 'titulo', 'texto', 'boton_texto', 'boton_link'],
        'listas': {},
        'imagen_simple': 'imagen',
    },
    'cta': {
        'escalares': ['etiqueta', 'titulo_linea1', 'titulo_linea2', 'subtitulo', 'boton_texto', 'boton_link'],
        'listas': {},
        'imagen_simple': None,
    },
}


def procesar_formulario(seccion, form, archivos):
    tipo = seccion['tipo']
    cfg = CAMPOS_SECCION.get(tipo)
    if not cfg:
        return seccion['datos']

    datos = copy.deepcopy(seccion['datos'])

    for campo in cfg['escalares']:
        if campo in form:
            valor = form.get(campo, '').strip()[:editor_visual.LARGO_MAXIMO_TEXTO]
            if campo.endswith('link'):
                # Solo enlaces seguros (/, #, http(s), mailto, tel). Nada de javascript:
                valor = editor_visual._link_seguro(valor, datos.get(campo, ''))
            datos[campo] = valor

    for nombre_lista, conf in cfg['listas'].items():
        lista = datos.get(nombre_lista, [])
        for i, item in enumerate(lista):
            for sub in conf['subcampos']:
                clave = f"{nombre_lista}__{i}__{sub}"
                if clave in form:
                    valor = form.get(clave, '').strip()[:editor_visual.LARGO_MAXIMO_TEXTO]
                    if sub == 'estrellas':
                        try:
                            valor = max(1, min(5, int(valor)))
                        except ValueError:
                            valor = item.get('estrellas', 5)
                    item[sub] = valor
            if conf['imagen']:
                archivo = archivos.get(f"imagen__{nombre_lista}__{i}")
                if archivo and archivo.filename and image_tools.es_imagen_valida(archivo.filename):
                    try:
                        item['imagen'] = image_tools.guardar_imagen_optimizada(archivo, f"{tipo}-{nombre_lista}-{i}")
                    except Exception:
                        pass  # imagen inválida: se conserva la anterior

    if cfg['imagen_simple']:
        campo_img = cfg['imagen_simple']
        archivo = archivos.get(f"imagen__{campo_img}")
        if archivo and archivo.filename and image_tools.es_imagen_valida(archivo.filename):
            try:
                datos[campo_img] = image_tools.guardar_imagen_optimizada(archivo, f"{tipo}-{campo_img}")
            except Exception:
                pass  # imagen inválida: se conserva la anterior

    return datos
