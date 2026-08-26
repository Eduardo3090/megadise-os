"""
admin_auth.py
─────────────────────────────────────────────────────────────
Login del panel /admin usando sesiones de Flask (cookie firmada,
nada de contraseñas en la URL). Incluye un token anti-CSRF simple
para los formularios del panel.
"""
import secrets
from functools import wraps
from flask import session, redirect, url_for, request, abort


def login_required(vista):
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if not session.get("admin_id"):
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
    if not token_sesion or not secrets.compare_digest(token_form, token_sesion):
        abort(400, description="Sesión expirada, por favor intenta de nuevo.")
