# ==============================================================================
# 1. CONFIGURACION E IMPORTACIONES
# ==============================================================================
import os
import io
import locale

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from flask import Flask, jsonify, render_template, request, redirect, url_for, session, make_response
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime, timedelta, date
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import logging
import re
import random

# Cargar variables de entorno desde la ubicacion absoluta del proyecto.
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_BASE_DIR, '.env'))

# Conexion con Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL:
    print("\n" + "!"*60)
    print(" ADVERTENCIA: SUPABASE_URL no configurada en el archivo .env")
    print(" La aplicacion no podra conectar con la base de datos.")
    print(" " + "!"*60 + "\n")

# Intentamos crear el cliente. Si falla, al menos no detiene todo el proceso de carga.
try:
    supabase = create_client(SUPABASE_URL or "https://placeholder.supabase.co", SUPABASE_SERVICE_KEY or SUPABASE_KEY or "placeholder")
except Exception as e:
    print(f" Error al inicializar Supabase: {e}")
    supabase = None

# Extensiones de imagen permitidas para subidas
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY') or os.urandom(32)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=(os.getenv('SESSION_COOKIE_SECURE', 'False').lower() == 'true'),
    PERMANENT_SESSION_LIFETIME=timedelta(minutes=30)  # ⏳ Sesion expira en 30 minutos
)

import uuid
import json
import string

def generate_master_key(length=12):
    """Genera una llave maestra aleatoria y segura."""
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

ACTIVE_SESSIONS_FILE = 'active_sessions.json'

def load_sessions():
    if os.path.exists(ACTIVE_SESSIONS_FILE):
        try:
            with open(ACTIVE_SESSIONS_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_sessions(sessions):
    with open(ACTIVE_SESSIONS_FILE, 'w') as f:
        json.dump(sessions, f)

def assign_session_token(user_id):
    sessions = load_sessions()
    token = str(uuid.uuid4())
    sessions[str(user_id)] = token
    save_sessions(sessions)
    return token

def revoke_session_token(user_id):
    sessions = load_sessions()
    str_id = str(user_id)
    if str_id in sessions:
        del sessions[str_id]
        save_sessions(sessions)

def is_valid_session(user_id, token):
    if not token: return False
    sessions = load_sessions()
    return sessions.get(str(user_id)) == token

@app.before_request
def check_single_session_and_status():
    if not session.get('logged_in'):
        return

    # Evitamos bloquear los assets/estaticos o logout/login
    if request.path.startswith('/static/') or request.path in ['/login', '/logout', '/get_locales']:
        return
        
    user_id = session.get('cedula')
    session_token = session.get('session_token')
    role = session.get('role')
    
    if not user_id or not session_token:
        return
        
    if not is_valid_session(user_id, session_token):
        return cerrar_sesion_forzada("Sesion iniciada en otro dispositivo.")

    if role == 'Empleado':
        query_emp = supabase.table("empleados").select("habilitado").eq("cedula", int(user_id)).execute()
        if hasattr(query_emp, 'data') and query_emp.data:
            if not query_emp.data[0].get('habilitado', True):
                revoke_session_token(user_id)
                return cerrar_sesion_forzada("Tu cuenta ha sido deshabilitada.")
        else:
            revoke_session_token(user_id)
            return cerrar_sesion_forzada("Cuenta no encontrada.")

def cerrar_sesion_forzada(msg):
    session.clear()
    if request.headers.get('Content-Type') == 'application/json' or request.headers.get('Accept') == 'application/json':
        return jsonify({"success": False, "msg": msg, "redirect": url_for('login', timeout=1, reason=msg)}), 401
    else:
        return redirect(url_for('login', timeout=1, reason=msg))

@app.after_request
def add_header(response):
    # Prevenir cache en rutas protegidas para evitar retroceso despues de logout
    if not request.path.startswith('/static'):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

@app.route('/api/check_session')
def api_check_session():
    if not session.get('logged_in'):
        return jsonify({"success": False, "redirect": url_for('login', timeout=1)}), 401
    return jsonify({"success": True})

# ==============================================================================
# 2. AYUDANTES, FILTROS Y DECORADORES
# ==============================================================================
def to_num(val):
    """Centralized utility to format numbers for display (Removes unnecessary decimals)."""
    if isinstance(val, (int, float)):
        return int(val) if float(val).is_integer() else float(val)
    return val

def is_valid_image(file):
    if not file:
        return False
    return file.mimetype in ('image/jpeg', 'image/png', 'image/webp')


# ==============================================================================
