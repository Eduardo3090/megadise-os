"""
image_tools.py
─────────────────────────────────────────────────────────────
Cuando el cliente sube una imagen nueva desde el panel /admin,
esta función la redimensiona y comprime automáticamente (igual
que se hizo manualmente en la optimización de imágenes original),
y genera tanto un .jpg como un .webp para que el sitio siga
siendo rápido sin que el cliente tenga que preocuparse de nada.
"""
import os
import time
import re
from PIL import Image, ImageOps

AQUI = os.path.dirname(os.path.abspath(__file__))
CARPETA_UPLOADS = os.path.join(AQUI, 'static', 'uploads')
ANCHO_MAXIMO = 1600
CALIDAD_JPG = 82
CALIDAD_WEBP = 78

EXTENSIONES_PERMITIDAS = {'.jpg', '.jpeg', '.png', '.webp'}


def es_imagen_valida(nombre_archivo):
    ext = os.path.splitext(nombre_archivo)[1].lower()
    return ext in EXTENSIONES_PERMITIDAS


def _slug(texto):
    texto = texto.lower().strip()
    texto = re.sub(r'[^a-z0-9]+', '-', texto)
    return texto.strip('-') or 'imagen'


def guardar_imagen_optimizada(archivo_subido, nombre_referencia="seccion"):
    """
    Recibe un archivo subido (Flask FileStorage), lo optimiza y guarda
    como uploads/<slug>-<timestamp>.jpg y .webp.
    Devuelve el 'nombre base' (sin carpeta ni extensión) para guardar
    en la base de datos, ej: 'uploads/hero-1-1699999999'
    """
    os.makedirs(CARPETA_UPLOADS, exist_ok=True)

    base = f"{_slug(nombre_referencia)}-{int(time.time())}"
    ruta_jpg = os.path.join(CARPETA_UPLOADS, base + '.jpg')
    ruta_webp = os.path.join(CARPETA_UPLOADS, base + '.webp')

    imagen = Image.open(archivo_subido)
    imagen = ImageOps.exif_transpose(imagen)  # corrige orientación de fotos de celular
    if imagen.mode in ("RGBA", "P"):
        fondo = Image.new("RGB", imagen.size, (255, 255, 255))
        fondo.paste(imagen.convert("RGBA"), mask=imagen.convert("RGBA").split()[-1])
        imagen = fondo
    else:
        imagen = imagen.convert("RGB")

    if imagen.width > ANCHO_MAXIMO:
        nueva_altura = int(imagen.height * (ANCHO_MAXIMO / imagen.width))
        imagen = imagen.resize((ANCHO_MAXIMO, nueva_altura), Image.LANCZOS)

    imagen.save(ruta_jpg, "JPEG", quality=CALIDAD_JPG, optimize=True)
    imagen.save(ruta_webp, "WEBP", quality=CALIDAD_WEBP)

    return f"uploads/{base}"
