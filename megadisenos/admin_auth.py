"""
admin_auth.py
─────────────────────────────────────────────────────────────
Login del panel /admin usando sesiones de Flask (cookie firmada,
nada de contraseñas en la URL). Incluye un token anti-CSRF simple
para los formularios del panel.

Seguridad extra: la sesión guarda una "huella" de la contraseña
vigente. Si la contraseña cambia, todas las sesiones abiertas
antes del cambio dejan de valer automáticamente.
"""
import hashlib
import hmac
import secrets
from functools import wraps
from flask import session, redirect, url_for, request, abort, g
import content_store


def huella(password_hash):
    return hashlib.sha256(password_hash.encode("utf-8")).hexdigest()[:24]


def iniciar_sesion(admin):
    """Abre una sesión nueva y limpia para este administrador."""
    session.clear()
    session["admin_id"] = admin["id"]
    session["huella"] = huella(admin["password_hash"])
    session.permanent = True  # dura PERMANENT_SESSION_LIFETIME (se renueva con el uso)


def admin_actual():
    """Devuelve el administrador de la sesión actual, o None si no es válida."""
    if hasattr(g, "_admin_cache"):
        return g._admin_cache
    admin = None
    admin_id = session.get("admin_id")
    if admin_id:
        fila = content_store.obtener_admin_por_id(admin_id)
        if fila and hmac.compare_digest(str(session.get("huella", "")),
                                        huella(fila["password_hash"])):
            admin = fila
    g._admin_cache = admin
    return admin


def login_required(vista):
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if not admin_actual():
            session.pop("admin_id", None)
            session.pop("huella", None)
            return redirect(url_for("admin_login", siguiente=request.path))
        return vista(*args, **kwargs)
    return envoltura


def generar_csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(16)
    return session["csrf_token"]


def validar_csrf(form):
    token_form = form.get("csrf_token", "")
    token_sesion = session.get("csrf_token", "")
    if not token_sesion or not secrets.compare_digest(token_form.encode(), token_sesion.encode()):
        abort(400, description="Sesión expirada, por favor intenta de nuevo.")
