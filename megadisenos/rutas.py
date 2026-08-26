"""
rutas.py
─────────────────────────────────────────────────────────────
Decide DÓNDE se guardan los archivos que cambian con el uso del
sitio (bases de datos, imágenes subidas, clave de sesión).

- Si existe la variable de entorno DATA_DIR (por ejemplo, la ruta
  de un disco persistente de Render como /var/data), todo se
  guarda ahí. Esos datos sobreviven a reinicios y despliegues.

- Si DATA_DIR no está configurada, se usa la carpeta del propio
  proyecto (el comportamiento de antes). Esto sigue funcionando
  en el plan gratuito o en tu computador, pero ahí los cambios
  SÍ se pierden cada vez que el servicio se reinicia.
"""
import os

AQUI = os.path.dirname(os.path.abspath(__file__))


def _obtener_data_dir():
    ruta = os.getenv("DATA_DIR", "").strip()
    if ruta:
        os.makedirs(ruta, exist_ok=True)
        return ruta
    return AQUI


DATA_DIR = _obtener_data_dir()
USANDO_DISCO_PERSISTENTE = bool(os.getenv("DATA_DIR", "").strip())

RUTA_CONTENIDO_DB = os.path.join(DATA_DIR, "contenido.db")
RUTA_SUSCRIPTORES_DB = os.path.join(DATA_DIR, "suscriptores.db")
RUTA_SECRET_KEY = os.path.join(DATA_DIR, ".secret_key")

CARPETA_MEDIA = os.path.join(DATA_DIR, "uploads")
os.makedirs(CARPETA_MEDIA, exist_ok=True)
