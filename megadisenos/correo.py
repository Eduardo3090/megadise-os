"""
correo.py
─────────────────────────────────────────────────────────────
Envío de correos del sitio (formulario de contacto y suscripción) y
respaldo de cada contacto en Google Sheets.

Igual que en el sitio de Sertains Labs, el correo sale por Resend (API por
HTTPS, funciona en Render sin abrir puertos SMTP) y cada contacto se guarda
además en una hoja de Google Sheets para no perder ninguna solicitud.

Variables de entorno (Render → Environment):
  RESEND_API_KEY     Clave de Resend (empieza con re_). Si falta, se intenta Gmail.
  CORREO_ENVIO       Remitente. Ej: Megadiseños <contacto@megadisenos.cl>
                     (el dominio debe estar verificado en Resend).
                     Por defecto: Megadiseños <onboarding@resend.dev>, que solo
                     puede enviar al correo dueño de la cuenta de Resend.
  CORREO_EMPRESA     Correo que recibe los mensajes (por defecto ventasmegadisenos@gmail.com).
  CONTRASENA_APP     (Opcional, respaldo) Contraseña de aplicación de Gmail.
  GOOGLE_CREDS_JSON  (Opcional) JSON de la cuenta de servicio de Google.
  GOOGLE_SHEET_ID    (Opcional) ID de la hoja donde se guardan los contactos.
"""
import json
import logging
import os
import smtplib
import urllib.error
import urllib.request
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from zoneinfo import ZoneInfo

log = logging.getLogger("megadisenos.correo")

TIEMPO_MAXIMO = 15  # segundos: nunca dejar el formulario colgado


def correo_empresa():
    return os.getenv("CORREO_EMPRESA", "ventasmegadisenos@gmail.com").strip()


def remitente():
    return os.getenv("CORREO_ENVIO", "Megadiseños <onboarding@resend.dev>").strip()


def hay_proveedor():
    return bool(os.getenv("RESEND_API_KEY") or os.getenv("CONTRASENA_APP"))


def _enviar_resend(destino, asunto, html_cuerpo, responder_a):
    carga = {
        "from": remitente(),
        "to": [destino],
        "subject": asunto,
        "html": html_cuerpo,
    }
    if responder_a:
        carga["reply_to"] = responder_a
    peticion = urllib.request.Request(
        "https://api.resend.com/emails",
        data=json.dumps(carga).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + os.environ["RESEND_API_KEY"].strip(),
            "Content-Type": "application/json",
            # Sin User-Agent propio, Cloudflare (que protege a Resend) rechaza la petición
            "User-Agent": "megadisenos-web/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(peticion, timeout=TIEMPO_MAXIMO) as resp:
            return 200 <= resp.status < 300, f"Resend {resp.status}"
    except urllib.error.HTTPError as e:
        detalle = e.read().decode("utf-8", "ignore")[:300]
        return False, f"Resend {e.code}: {detalle}"


def _enviar_gmail(destino, asunto, html_cuerpo, responder_a):
    origen = correo_empresa()
    msg = MIMEMultipart("alternative")
    msg["Subject"] = asunto
    msg["From"] = origen
    msg["To"] = destino
    if responder_a:
        msg["Reply-To"] = responder_a
    msg.attach(MIMEText(html_cuerpo, "html"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=TIEMPO_MAXIMO) as servidor:
        servidor.login(origen, os.environ["CONTRASENA_APP"])
        servidor.sendmail(origen, destino, msg.as_string())
    return True, "Gmail OK"


def enviar(destino, asunto, html_cuerpo, responder_a=None):
    """Envía un correo. Devuelve (ok, detalle). Nunca lanza excepciones."""
    try:
        if os.getenv("RESEND_API_KEY"):
            return _enviar_resend(destino, asunto, html_cuerpo, responder_a)
        if os.getenv("CONTRASENA_APP"):
            return _enviar_gmail(destino, asunto, html_cuerpo, responder_a)
        return False, "No hay proveedor de correo configurado (falta RESEND_API_KEY)"
    except Exception as e:  # red caída, timeout, credenciales malas…
        return False, f"{type(e).__name__}: {e}"


def guardar_en_sheets(nombre, telefono, email, mensaje):
    """Respaldo en Google Sheets (opcional). Devuelve True si se guardó."""
    if not (os.getenv("GOOGLE_CREDS_JSON") and os.getenv("GOOGLE_SHEET_ID")):
        return False
    try:
        import gspread  # se importa aquí para que el sitio funcione aunque falte la librería
        from google.oauth2.service_account import Credentials

        credenciales = Credentials.from_service_account_info(
            json.loads(os.environ["GOOGLE_CREDS_JSON"]),
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        hoja = gspread.authorize(credenciales).open_by_key(os.environ["GOOGLE_SHEET_ID"]).sheet1
        fecha = datetime.now(ZoneInfo("America/Santiago")).strftime("%Y-%m-%d %H:%M")
        # Evita que una celda se interprete como fórmula
        limpiar = lambda t: ("'" + t) if t[:1] in ("=", "+", "-", "@") else t
        hoja.append_row([fecha, limpiar(nombre), limpiar(telefono), limpiar(email), limpiar(mensaje)])
        return True
    except Exception:
        log.exception("No se pudo guardar el contacto en Google Sheets")
        return False
