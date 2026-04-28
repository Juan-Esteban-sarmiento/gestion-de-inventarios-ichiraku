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
import requests
import random

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY or SUPABASE_KEY)

# ==============================================================================
# HELPER WHATSAPP GRATIS (CallMeBot)
# ==============================================================================
def enviar_whatsapp_gratis(telefono, apikey, mensaje):
    """
    Envia un mensaje de WhatsApp usando la API gratuita de CallMeBot.
    El usuario debe haber activado el bot previamente.
    """
    try:
        # Limpiar telefono (prefijo 57 para Colombia)
        tel_limpio = re.sub(r"\D", "", str(telefono))
        if not tel_limpio.startswith("57") and len(tel_limpio) == 10:
            tel_limpio = "57" + tel_limpio
            
        # CANAL 1: CallMeBot
        url1 = "https://api.callmebot.com/whatsapp.php"
        params1 = {"phone": tel_limpio, "text": mensaje, "apikey": apikey}
        res1 = requests.get(url1, params=params1, timeout=8)
        
        # Si el Canal 1 funciona y no dice que esta lleno
        if res1.status_code == 200 and "full" not in res1.text.lower():
            return True, "Enviado por Canal 1"

        # CANAL 2: TextMeBot (Fallback)
        url2 = "https://api.textmebot.com/send.php"
        params2 = {"recipient": tel_limpio, "text": mensaje, "apikey": apikey}
        res2 = requests.get(url2, params=params2, timeout=8)
        
        if res2.status_code == 200:
            return True, "Enviado por Canal 2"
            
        return False, f"Falla en ambos canales. Canal 1: {res1.text[:50]} | Canal 2: {res2.text[:50]}"
    except Exception as e:
        return False, f"Error de conexion: {str(e)}"

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
# 2. UTILIDADES Y FILTROS
# ==============================================================================

@app.template_filter('format_fecha')
def format_fecha(value):
    if not value:
        return "Sin fecha"
    dt = datetime.fromisoformat(value.split('T')[0])
    return dt.strftime("%d/%m/%Y")

def login_requerido(rol=None):
    def decorador(f):
        @wraps(f)
        def decorado(*args, **kwargs):
            if not session.get('logged_in'):
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({"success": False, "msg": "Sesion expirada"}), 401
                return redirect(url_for('login'))
            if rol and session.get('role') != rol:
                return jsonify({"success": False, "msg": "Acceso denegado"}), 403
            return f(*args, **kwargs)
        return decorado
    return decorador

# ==============================================================================
# 3. SISTEMA DE NOTIFICACIONES (LOGICA)
# ==============================================================================
def generar_notificaciones_caducidad():
    try:
        hoy = datetime.now().date()
        limite = hoy + timedelta(days=3)
        
        test_connection = supabase.table("inventario").select("count", count="exact").execute()
        
        proximos = supabase.table("inventario") \
            .select("id_inventario, id_producto, cantidad, fecha_caducidad") \
            .gte("fecha_caducidad", hoy.isoformat()) \
            .lte("fecha_caducidad", limite.isoformat()) \
            .execute()

        if not proximos.data:
            return
            
        notificaciones_creadas = 0
        for item in proximos.data:
            producto = supabase.table("productos") \
                .select("nombre") \
                .eq("id_producto", item["id_producto"]) \
                .single() \
                .execute()
                
            nombre_producto = producto.data["nombre"] if producto.data else "Nombre no encontrado"

            noti_existente = supabase.table("notificaciones") \
                .eq("id_inventario", item["id_inventario"]) \
                .eq("tipo", "caducidad") \
                .execute()

            if not noti_existente.data:
                mensaje = f" El producto '{nombre_producto}' (ID: {item['id_producto']}) caduca el {item['fecha_caducidad']} | Cantidad: {item['cantidad']}"
                
                supabase.table("notificaciones").insert({
                    "id_inventario": item["id_inventario"],
                    "mensaje": mensaje,
                    "tipo": "caducidad",
                    "leido": False,
                    "fecha": datetime.now().isoformat()
                }).execute()
                notificaciones_creadas += 1

    except Exception as e:
        print("Error al generar notificaciones:", e)
        import traceback
        traceback.print_exc()

def generar_notificaciones_stock_bajo(target_local_id=None):
    try:
        # 1. Obtener todos los productos habilitados
        try:
            productos_res = supabase.table("productos").select("id_producto, nombre, unidad").eq("habilitado", True).execute()
            productos = productos_res.data or []
        except Exception as e:
            print("Error al consultar tabla productos:", e)
            return

        if not productos:
            return

        # 2. Filtrar locales: solo el objetivo o todos
        if target_local_id:
            locales_res = supabase.table("locales").select("id_local, nombre").eq("id_local", target_local_id).execute()
        else:
            locales_res = supabase.table("locales").select("id_local, nombre").execute()
        
        locales = locales_res.data or []
        
        for local in locales:
            id_l = local["id_local"]
            nombre_l = local["nombre"]
            
            # 2. Obtener todo el inventario de este local
            inv_res = supabase.table("inventario").select("id_producto, cantidad").eq("id_local", id_l).execute()
            inv_data = inv_res.data or []
            
            # 3. Consolidar stock actual por producto
            stock_actual_map = {}
            for item in inv_data:
                pid = item["id_producto"]
                stock_actual_map[pid] = stock_actual_map.get(pid, 0) + item["cantidad"]
            
            # 4. Comparar cada producto con su umbral
            for p in productos:
                pid = p["id_producto"]
                nombre_p = p["nombre"]
                unidad_p = p["unidad"]
                actual = stock_actual_map.get(pid, 0)
                if actual <= 50:
                    if actual == 0:
                        mensaje = f"🛑 AGOTADO: '{nombre_p}' en {nombre_l}. No queda stock disponible."
                        tipo_noti = "stock_agotado"
                    else:
                        mensaje = f"⚠️ STOCK BAJO: '{nombre_p}' en {nombre_l}. ACTUAL: {actual} {unidad_p} (Limite: 50)"
                        tipo_noti = "stock_bajo"
                    
                    # Evitar duplicados del mismo tipo para el mismo producto en el mismo local
                    existente = supabase.table("notificaciones")\
                        .select("id_notificaciones")\
                        .eq("tipo", tipo_noti)\
                        .ilike("mensaje", f"%{nombre_p}%{nombre_l}%")\
                        .execute()
                    
                    if not existente.data:
                        # Si existia la otra (ej: paso de bajo a agotado), borrar la vieja
                        otra_tipo = "stock_bajo" if tipo_noti == "stock_agotado" else "stock_agotado"
                        supabase.table("notificaciones").delete().eq("tipo", otra_tipo).ilike("mensaje", f"%{nombre_p}%{nombre_l}%").execute()

                        supabase.table("notificaciones").insert({
                            "mensaje": mensaje,
                            "tipo": tipo_noti,
                            "leido": False,
                            "fecha": datetime.now().isoformat()
                        }).execute()
                else:
                    # Limpiar notificaciones si el stock se recupero
                    supabase.table("notificaciones")\
                        .delete()\
                        .in_("tipo", ["stock_bajo", "stock_agotado"])\
                        .ilike("mensaje", f"%{nombre_p}%{nombre_l}%")\
                        .execute()

    except Exception as e:
        print("Error al generar notificaciones de stock bajo:", e)

def eliminar_notificaciones_caducadas():
    try:
        hoy = datetime.now().date()
        caducados = supabase.table("inventario") \
            .select("id_inventario, id_producto, fecha_caducidad") \
            .lte("fecha_caducidad", hoy.isoformat()) \
            .execute()

        if not caducados.data:
            return

        ids_caducados = [item["id_inventario"] for item in caducados.data]
        res_notif = supabase.table("notificaciones") \
            .delete() \
            .in_("id_inventario", ids_caducados) \
            .execute()
        res_inv = supabase.table("inventario") \
            .delete() \
            .in_("id_inventario", ids_caducados) \
            .execute()
    except Exception as e:
        print("Error al eliminar notificaciones o productos caducados:", e)

@app.route('/Ad_Pnotificaciones', methods=['GET'])
@login_requerido(rol='Administrador')
def Ad_Pnotificaciones():
    generar_notificaciones_caducidad()
    eliminar_notificaciones_caducadas()
    notificaciones = supabase.table("notificaciones") \
        .select("*") \
        .order("fecha", desc=True) \
        .execute()
    return render_template("Ad_templates/Ad_Pnotificaciones.html", notificaciones=notificaciones.data)

@app.route('/marcar_prioritaria/<int:id>', methods=['POST'])
@login_requerido(rol='Administrador')
def marcar_prioritaria(id):
    supabase.table("notificaciones").update({"tipo": "prioritaria"}).eq("id_notificaciones", id).execute()
    return jsonify({"success": True})


def insertar_informe(id_pedido):
    existente = supabase.table("informe").select("id_inf_pedido").eq("id_inf_pedido", id_pedido).execute().data
    if not existente:
        supabase.table("informe").insert({
            "id_inf_pedido": id_pedido,
            "fecha_creacion": datetime.now().isoformat()
        }).execute()
        return True
    return False

@app.route('/')
def index():
    return redirect(url_for('login'))

# ==============================================================================
# 4. AUTENTICACION Y PERFIL DE USUARIO
# ==============================================================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        usuario = data.get('id')
        password = data.get('password')
        branch = data.get('branch')

        if not usuario or not password:
            return jsonify({"success": False, "msg": "Por favor completa todos los campos (ID y contrasena)."}), 400

        if not str(usuario).isdigit():
            return jsonify({"success": False, "msg": "El ID debe ser numerico."}), 400

        try:
            # 1. Buscar primero en la tabla de administrador
            query_admin = supabase.table("administrador").select("*").eq("id", int(usuario)).execute()
            
            if hasattr(query_admin, 'data') and query_admin.data:
                admin_user = query_admin.data[0]
                
                if not check_password_hash(admin_user['contrasena'], password):
                    return jsonify({"success": False, "msg": "Contrasena incorrecta."}), 401
                
                session.permanent = True
                session['logged_in'] = True
                # Aseguramos el rol por la tabla
                session['role'] = 'Administrador'
                session['cedula'] = admin_user.get('id', usuario)
                session['nombre'] = admin_user.get('nombre', '')
                session['foto'] = admin_user.get('foto', '')
                session['session_token'] = assign_session_token(session['cedula'])
                
                # Sistema de Llave Maestra: Generar si no existe
                master_key = admin_user.get('master_key')
                if not master_key:
                    master_key = generate_master_key()
                    supabase.table("administrador").update({"master_key": master_key}).eq("id", admin_user['id']).execute()
                
                session['show_master_key'] = not admin_user.get('master_key_visto', False)
                session['master_key'] = master_key
                
                return jsonify({"success": True, "msg": f"Bienvenido, {admin_user.get('nombre', '')}", "redirect": url_for('Ad_Inicio')})
            
            # 2. Si no esta en administrador, buscamos en empleados
            query_emp = supabase.table("empleados").select("*").eq("cedula", int(usuario)).execute()
            
            if hasattr(query_emp, 'data') and query_emp.data:
                empleado = query_emp.data[0]
                
                if not empleado.get('habilitado', True):
                    return jsonify({"success": False, "msg": "Empleado deshabilitado. Contacta al administrador."}), 403
                
                if not check_password_hash(empleado['contrasena'], password):
                    return jsonify({"success": False, "msg": "Contrasena incorrecta."}), 401
                
                # Sabiendo que es empleado, verificamos si mando sucursal
                if not branch:
                    return jsonify({"success": False, "msg": "Por favor selecciona una sucursal."}), 400
                
                session.permanent = True
                session['logged_in'] = True
                # Aseguramos el rol por la tabla
                session['role'] = 'Empleado'
                session['cedula'] = empleado.get('cedula', usuario)
                session['nombre'] = empleado.get('nombre', '')
                session['foto'] = empleado.get('foto', '')
                session['branch'] = int(branch)
                session['session_token'] = assign_session_token(session['cedula'])

                # Sistema de Llave Maestra: Generar si no existe
                master_key = empleado.get('master_key')
                if not master_key:
                    master_key = generate_master_key()
                    supabase.table("empleados").update({"master_key": master_key}).eq("cedula", empleado['cedula']).execute()
                
                session['show_master_key'] = not empleado.get('master_key_visto', False)
                session['master_key'] = master_key

                # Obtener nombre de la sucursal
                try:
                    sucursal_query = supabase.table("locales").select("nombre").eq("id_local", int(branch)).single().execute()
                    if hasattr(sucursal_query, 'data') and sucursal_query.data:
                        session['branch_name'] = sucursal_query.data['nombre']
                    else:
                        session['branch_name'] = "Sucursal Indefinida"
                except Exception as e:
                    print("Error obteniendo nombre sucursal:", e)
                    session['branch_name'] = "Sucursal Indefinida"

                return jsonify({"success": True, "msg": f"Bienvenido, {empleado.get('nombre', '')}", "redirect": url_for('Em_Inicio')})

            # 3. Si no se encontro en ninguna tabla
            return jsonify({"success": False, "msg": "Usuario no encontrado."}), 404

        except Exception as e:
            print("Error durante el login:", e)
            return jsonify({"success": False, "msg": "Error en el servidor."}), 500
            
    return render_template("login.html")

@app.route("/get_locales", methods=["GET"])
def get_locales():
    try:
        response = supabase.table("locales").select("id_local, nombre").execute()
        locales = response.data
        return jsonify({"success": True, "locales": locales})
    except Exception as e:
        print("Error al obtener locales:", e)
        return jsonify({"success": False, "msg": "Error al obtener locales"})

@app.route('/logout')
def logout():
    user_id = session.get('cedula')
    if user_id:
        revoke_session_token(user_id)
    session.clear()
    timeout = request.args.get('timeout')
    target = url_for('login')
    if timeout:
        target += f"?timeout={timeout}"
    response = redirect(target)
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route("/Ad_Ceditar", methods=["GET", "POST"])
@login_requerido(rol='Administrador')
def Ad_Ceditar():
    cedula = session.get("cedula")
    try:
        response = supabase.table("administrador").select("*").eq("id", cedula).execute()
        admin = response.data[0] if response.data else None
        if not admin:
            return jsonify({"success": False, "msg": "Administrador no encontrado."}), 404

        if request.method == "GET":
            photo_url = admin.get("foto") if admin.get("foto") else url_for("static", filename="image/default.png")
            return render_template(
                "Ad_templates/Ad_Ceditar.html",
                user={
                    "Cedula": admin.get("id", ""),
                    "Nombre": admin.get("nombre", ""),
                    "telefono": admin.get("telefono", ""),
                    "wa_apikey": admin.get("wa_apikey", ""),
                    "photo_url": photo_url
                }
            )

        if request.method == "POST" and request.is_json:
            data = request.get_json()
            nombre = data.get("Nombre")
            telefono = data.get("telefono", "").strip()
            wa_apikey = data.get("wa_apikey", "").strip()
            
            if not nombre:
                return jsonify({"success": False, "msg": "El nombre es obligatorio."}), 400
            
            update_data = {"nombre": nombre}
            if telefono:
                update_data["telefono"] = telefono
            if wa_apikey:
                update_data["wa_apikey"] = wa_apikey
                
            update_response = supabase.table("administrador").update(update_data).eq("id", cedula).execute()
            if update_response.data:
                return jsonify({"success": True, "msg": "Usuario actualizado correctamente"}), 200
            else:
                return jsonify({"success": False, "msg": "No se pudo actualizar el usuario."}), 500
    except Exception as e:
        print("Error en Ad_Ceditar:", e)
        return jsonify({"success": False, "msg": "Error en el servidor"}), 500

@app.route('/Ad_Ceditar_foto', methods=['POST', 'DELETE'])
@login_requerido(rol='Administrador')
def Ad_Ceditar_foto():
    cedula = session.get('cedula')
    try:
        if request.method == 'POST':
            foto = request.files.get('foto')
            if not foto:
                return jsonify({"success": False, "msg": "No se envio ninguna foto"}), 400
            if not is_valid_image(foto):
                return jsonify({"success": False, "msg": "Formato de imagen no permitido."}), 400
            file_name = f"admin_{cedula}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
            file_bytes = foto.read()
            upload_response = supabase.storage.from_("fotos_admin").upload(file_name, file_bytes)
            if hasattr(upload_response, "error") and upload_response.error:
                return jsonify({"success": False, "msg": "Error al subir la foto a Supabase"}), 500
            photo_url = supabase.storage.from_("fotos_admin").get_public_url(file_name)
            update_response = supabase.table("administrador").update({"foto": photo_url}).eq("id", cedula).execute()
            if update_response.data:
                return jsonify({"success": True, "photo_url": photo_url}), 200
            else:
                return jsonify({"success": False, "msg": "No se pudo guardar la foto"}), 500

        elif request.method == 'DELETE':
            response = supabase.table("administrador").select("foto").eq("id", cedula).execute()
            if response.data and response.data[0].get("foto"):
                foto_url = response.data[0]["foto"]
                file_name = foto_url.split("/")[-1]
                supabase.storage.from_("fotos_admin").remove([file_name])
            supabase.table("administrador").update({"foto": None}).eq("id", cedula).execute()
            default_url = url_for("static", filename="image/default.png")
            return jsonify({"success": True, "photo_url": default_url}), 200
    except Exception as e:
        print("Error en Ad_Ceditar_foto:", e)
        return jsonify({"success": False, "msg": str(e)}), 500

@app.route("/recuperar_con_llave", methods=["POST"])
def recuperar_con_llave():
    try:
        data = request.get_json()
        usuario_id = data.get("id")
        llave = data.get("llave", "").strip().upper()
        nueva_clave = data.get("nueva_clave")

        if not (usuario_id and llave and nueva_clave):
            return jsonify({"success": False, "msg": "Todos los campos son obligatorios."}), 400

        # Intentar en administrador
        admin_res = supabase.table("administrador").select("*").eq("id", int(usuario_id)).eq("master_key", llave).execute()
        if admin_res.data:
            hashed = generate_password_hash(nueva_clave)
            supabase.table("administrador").update({"contrasena": hashed}).eq("id", int(usuario_id)).execute()
            return jsonify({"success": True, "msg": "Contrasena de Administrador actualizada correctamente."})

        # Intentar en empleados
        emp_res = supabase.table("empleados").select("*").eq("cedula", int(usuario_id)).eq("master_key", llave).execute()
        if emp_res.data:
            hashed = generate_password_hash(nueva_clave)
            supabase.table("empleados").update({"contrasena": hashed}).eq("cedula", int(usuario_id)).execute()
            return jsonify({"success": True, "msg": "Contrasena de Empleado actualizada correctamente."})

        return jsonify({"success": False, "msg": "El ID o la Llave Maestra no son correctos."}), 401
    except Exception as e:
        logger.exception("Error en recuperar_con_llave: %s", e)
        return jsonify({"success": False, "msg": "Error interno al procesar la recuperacion."}), 500

@app.route("/confirmar_llave_vista", methods=["POST"])
def confirmar_llave_vista():
    try:
        cedula = session.get('cedula')
        role = session.get('role')
        if not cedula:
            return jsonify({"success": False, "msg": "No hay sesion activa."}), 401
        
        if role == 'Administrador':
            supabase.table("administrador").update({"master_key_visto": True}).eq("id", int(cedula)).execute()
        else:
            supabase.table("empleados").update({"master_key_visto": True}).eq("cedula", int(cedula)).execute()
            
        session['show_master_key'] = False
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "msg": str(e)}), 500

@app.route("/admin/get_master_key/<int:cedula>", methods=["GET"])
@login_requerido(rol='Administrador')
def get_master_key_admin(cedula):
    try:
        res = supabase.table("empleados").select("master_key").eq("cedula", cedula).execute()
        if res.data:
            return jsonify({"success": True, "key": res.data[0]['master_key']})
        return jsonify({"success": False, "msg": "No se encontro el empleado."}), 404
    except Exception as e:
        return jsonify({"success": False, "msg": str(e)}), 500

    except Exception as e:
        logger.exception("Error en validar_token: %s", e)
        return jsonify({"success": False, "msg": "Error interno al validar el token."}), 500

@app.route("/Em_Ceditar", methods=["GET", "POST"])
@login_requerido(rol='Empleado')
def Em_Ceditar():
    cedula = session.get("cedula")
    try:
        response = supabase.table("empleados").select("*").eq("cedula", cedula).execute()
        empleado = response.data[0] if response.data else None
        if not empleado:
            return jsonify({"success": False, "msg": "Empleado no encontrado."}), 404

        if request.method == "GET":
            photo_url = empleado.get("foto") if empleado.get("foto") else url_for("static", filename="image/default.png")
            return render_template(
                "Em_templates/Em_Ceditar.html",
                user={
                    "Cedula": empleado.get("cedula", ""),
                    "Nombre": empleado.get("nombre", ""),
                    "telefono": empleado.get("telefono", ""),
                    "wa_apikey": empleado.get("wa_apikey", ""),
                    "photo_url": photo_url
                }
            )

        if request.method == "POST" and request.is_json:
            data = request.get_json()
            nombre = data.get("Nombre")
            wa_apikey = data.get("wa_apikey", "").strip()
            
            if not nombre:
                return jsonify({"success": False, "msg": "El nombre es obligatorio."}), 400
            
            update_data = {"nombre": nombre}
            if wa_apikey:
                update_data["wa_apikey"] = wa_apikey
                
            update_response = supabase.table("empleados").update(update_data).eq("cedula", cedula).execute()
            if update_response.data:
                return jsonify({"success": True, "msg": "Perfil actualizado correctamente"}), 200
            else:
                return jsonify({"success": False, "msg": "No se pudo actualizar el perfil."}), 500
    except Exception as e:
        print("Error en Em_Ceditar:", e)
        return jsonify({"success": False, "msg": "Error en el servidor"}), 500

@app.route('/Em_Ceditar_foto', methods=['POST', 'DELETE'])
@login_requerido(rol='Empleado')
def Em_Ceditar_foto():
    cedula = session.get('cedula')
    try:
        if request.method == 'POST':
            foto = request.files.get('foto')
            if not foto:
                return jsonify({"success": False, "msg": "No se envio ninguna foto"}), 400
            if not is_valid_image(foto):
                return jsonify({"success": False, "msg": "Formato de imagen no permitido."}), 400
            file_name = f"empleado_{cedula}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
            file_bytes = foto.read()
            upload_response = supabase.storage.from_("Fotos").upload(file_name, file_bytes)
            if hasattr(upload_response, "error") and upload_response.error:
                return jsonify({"success": False, "msg": "Error al subir la foto a Supabase"}), 500
            photo_url = supabase.storage.from_("Fotos").get_public_url(file_name)
            update_response = supabase.table("empleados").update({"foto": photo_url}).eq("cedula", cedula).execute()
            if update_response.data:
                return jsonify({"success": True, "photo_url": photo_url}), 200
            else:
                return jsonify({"success": False, "msg": "No se pudo guardar la foto"}), 500

        elif request.method == 'DELETE':
            response = supabase.table("empleados").select("foto").eq("cedula", cedula).execute()
            if response.data and response.data[0].get("foto"):
                foto_url = response.data[0]["foto"]
                file_name = foto_url.split("/")[-1]
                supabase.storage.from_("Fotos").remove([file_name])
            supabase.table("empleados").update({"foto": None}).eq("cedula", cedula).execute()
            default_url = url_for("static", filename="image/default.png")
            return jsonify({"success": True, "photo_url": default_url}), 200
    except Exception as e:
        print("Error en Em_Ceditar_foto:", e)
        return jsonify({"success": False, "msg": str(e)}), 500

@app.route("/Em_validar_token", methods=["POST"])
def Em_validar_token():
    # Esta ruta ya no se usa, redirige a la unificada
    return jsonify({"success": False, "msg": "Usa la nueva ruta de recuperacion con Llave Maestra."}), 410

@app.route("/Em_enviar_token_recuperacion", methods=["POST"])
def Em_enviar_token_recuperacion():
    # Esta ruta ya no se usa
    return jsonify({"success": False, "msg": "Usa la recuperacion con Llave Maestra."}), 410

# ==============================================================================
# 5. ADMINISTRACION - GESTION DE PRODUCTOS, EMPLEADOS E INVENTARIO
# ==============================================================================

# --- Gestion de Locales ---
@app.route('/Ad_Rlocales', methods=['GET', 'POST'])
@login_requerido(rol='Administrador')
def Ad_Rlocales():
    return render_template("Ad_templates/Ad_Rlocales.html")

@app.route('/registrar_local', methods=['POST'])
@login_requerido(rol='Administrador')
def registrar_local():
    nombre = request.form.get('nombre')
    direccion = request.form.get('direccion')
    id_local = request.form.get('id_local')
    foto = request.files.get('foto')

    if not (nombre and direccion and id_local):
        return jsonify({"success": False, "msg": "Todos los campos son obligatorios."})

    nombre_limpio = nombre.strip()
    if len(nombre_limpio) < 2 or len(nombre_limpio) > 100:
        return jsonify({"success": False, "msg": "El nombre del local debe tener entre 2 y 100 caracteres."})

    direccion_limpia = direccion.strip()
    if len(direccion_limpia) < 5 or len(direccion_limpia) > 200:
        return jsonify({"success": False, "msg": "La direccion debe tener entre 5 y 200 caracteres."})

    try:
        id_local_int = int(id_local)
        if id_local_int < 1:
            return jsonify({"success": False, "msg": "El ID del local debe ser un numero positivo."})
    except ValueError:
        return jsonify({"success": False, "msg": "El ID del local debe ser un numero valido."})

    try:
        existing = supabase.table("locales").select("*").eq("id_local", id_local).execute()
        if existing.data:
            return jsonify({"success": False, "msg": "Ya existe un local con ese ID."})
    except Exception as e:
        print("Error al verificar local:", e)
        return jsonify({"success": False, "msg": "Error al verificar duplicados."})

    foto_url = None
    if foto:
        if not is_valid_image(foto):
            return jsonify({"success": False, "msg": "Formato de imagen no permitido."}), 400
        try:
            filename = f"locales/{id_local}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
            upload_response = supabase.storage.from_("Fotos").upload(filename, foto.read())
            if hasattr(upload_response, "error") and upload_response.error:
                print("Error al subir imagen:", upload_response.error)
                return jsonify({"success": False, "msg": "Error al subir imagen."})
            foto_url = f"{SUPABASE_URL}/storage/v1/object/public/Fotos/{filename}"
        except Exception as e:
            print("Error al subir foto:", e)
            return jsonify({"success": False, "msg": "Error al procesar la foto."})

    try:
        data = {
            "id_local": id_local,
            "nombre": nombre,
            "direccion": direccion,
            "foto": foto_url
        }
        response = supabase.table("locales").insert(data).execute()
        if response.data:
            return jsonify({"success": True, "msg": "Local registrado correctamente."})
        else:
            return jsonify({"success": False, "msg": "Error al registrar local."})
    except Exception as e:
        print("Error inesperado al registrar local:", e)
        return jsonify({"success": False, "msg": "Error en el servidor."})

@app.route('/obtener_siguiente_id_local', methods=['GET'])
@login_requerido(rol='Administrador')
def obtener_siguiente_id_local():
    try:
        response = supabase.table("locales").select("id_local").order("id_local", desc=True).limit(1).execute()
        if response.data:
            ultimo_id = int(response.data[0]["id_local"])
            siguiente_id = ultimo_id + 1
        else:
            siguiente_id = 1
        return jsonify({"success": True, "siguiente_id": siguiente_id})
    except Exception as e:
        print("Error al obtener siguiente ID:", e)
        return jsonify({"success": False, "msg": "Error al calcular el ID."})

@app.route("/buscar_local", methods=["POST"])
@login_requerido(rol='Administrador')
def buscar_local():
    data = request.get_json()
    termino = data.get("termino", "").strip()
    try:
        query = supabase.table("locales").select("id_local, nombre, direccion, foto, habilitado")
        if termino.isdigit():
            query = query.eq("id_local", int(termino))
        else:
            query = query.or_(f"nombre.ilike.%{termino}%,direccion.ilike.%{termino}%")
        response = query.execute()
        locales = response.data or []
        if locales:
            return jsonify({"success": True, "locales": locales})
        else:
            return jsonify({"success": False, "msg": "No se encontraron locales."})
    except Exception as e:
        print("Error en busqueda de local:", e)
        return jsonify({"success": False, "msg": "Error en el servidor"})

@app.route("/editar_local/<int:id_local>", methods=["PUT"])
@login_requerido(rol='Administrador')
def editar_local(id_local):
    try:
        data = request.get_json()
        nombre = data.get("nombre")
        direccion = data.get("direccion")
        if not (nombre and direccion):
            return jsonify({"success": False, "msg": "Todos los campos son obligatorios."}), 400

        nombre_limpio = nombre.strip()
        if len(nombre_limpio) < 2 or len(nombre_limpio) > 100:
            return jsonify({"success": False, "msg": "El nombre del local debe tener entre 2 y 100 caracteres."}), 400

        direccion_limpia = direccion.strip()
        if len(direccion_limpia) < 5 or len(direccion_limpia) > 200:
            return jsonify({"success": False, "msg": "La direccion debe tener entre 5 y 200 caracteres."}), 400

        response = supabase.table("locales").update({
            "nombre": nombre_limpio,
            "direccion": direccion_limpia
        }).eq("id_local", id_local).execute()
        if response.data:
            return jsonify({"success": True, "msg": "Local actualizado correctamente."})
        else:
            return jsonify({"success": False, "msg": "No se pudo actualizar el local."})
    except Exception as e:
        print("Error al editar local:", e)
        return jsonify({"success": False, "msg": "Error en el servidor"})

@app.route("/cambiar_estado_local/<int:id_local>", methods=["POST"])
@login_requerido(rol='Administrador')
def cambiar_estado_local(id_local):
    try:
        data = request.get_json()
        habilitado = data.get("habilitado")
        if habilitado is None:
            return jsonify({"success": False, "msg": "Estado no especificado."}), 400
        response = supabase.table("locales").update({"habilitado": habilitado}).eq("id_local", id_local).execute()
        if hasattr(response, "data") and response.data:
            estado = "habilitado" if habilitado else "deshabilitado"
            return jsonify({"success": True, "msg": f"Local {estado} correctamente."})
        else:
            return jsonify({"success": False, "msg": "No se encontro el Local."}), 404
    except Exception as e:
        print("Error al cambiar estado del Local:", e)
        return jsonify({"success": False, "msg": f"Error en servidor: {e}"}), 500

# --- Gestion de Empleados ---
@app.route('/Ad_Rempleados', methods=['GET', 'POST'])
@login_requerido(rol='Administrador')
def Ad_Rempleados():
    return render_template("Ad_templates/Ad_Rempleados.html"), 200, {"Content-Type": "text/html; charset=utf-8"}

@app.route('/registrar_empleado', methods=['POST'])
@login_requerido(rol='Administrador')
def registrar_empleado():
    try:
        nombre = request.form.get('nombre')
        cedula = request.form.get('cedula')
        contrasena = request.form.get('contrasena')
        telefono = request.form.get('contacto')
        foto = request.files.get('foto')

        if not (nombre and cedula and contrasena and telefono):
            return jsonify({"success": False, "msg": "Todos los campos son obligatorios."})

        # Validar cedula
        cedula_str = cedula.strip()
        if not cedula_str.isdigit():
            return jsonify({"success": False, "msg": "El ID debe contener solo numeros."})
        if len(cedula_str) < 5 or len(cedula_str) > 10:
            return jsonify({"success": False, "msg": "El ID debe tener entre 5 y 10 digitos."})
        cedula_int = int(cedula_str)

        # Validar telefono
        try:
            telefono_int = int(telefono)
            if telefono_int < 1000000 or telefono_int > 999999999999999:
                return jsonify({"success": False, "msg": "El telefono debe tener entre 7 y 15 digitos."})
        except ValueError:
            return jsonify({"success": False, "msg": "El telefono debe contener solo numeros."})

        # Validar contrasena
        if not re.fullmatch(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,64}$", contrasena):
            return jsonify({"success": False, "msg": "La contrasena debe tener al menos 8 caracteres, incluir una minuscula, una mayuscula, un numero y un simbolo."})

        # VALIDAR Y NORMALIZAR DATOS
        if any(char.isdigit() for char in nombre):
            return jsonify({"success": False, "msg": "El nombre no puede contener numeros."})

        nombre_normalizado = re.sub(r"\s+", " ", nombre).strip().lower()
        telefono_str = str(telefono).strip()

        # VERIFICAR DUPLICADOS
        existente_cedula = supabase.table("empleados").select("cedula, nombre").eq("cedula", cedula_int).execute()
        if existente_cedula.data:
            empleado_existente = existente_cedula.data[0]
            return jsonify({"success": False, "msg": f"El ID {cedula} ya esta registrado a nombre de: {empleado_existente.get('nombre', 'N/A')}"})

        existente_nombre_exacto = supabase.table("empleados").select("cedula, nombre").ilike("nombre", nombre_normalizado).execute()
        if existente_nombre_exacto.data:
            empleado_existente = existente_nombre_exacto.data[0]
            return jsonify({"success": False, "msg": f"El nombre '{nombre_normalizado}' ya esta registrado con el ID: {empleado_existente.get('cedula', 'N/A')}"})

        existente_telefono = supabase.table("empleados").select("cedula, nombre, telefono").eq("telefono", telefono_str).execute()
        if existente_telefono.data:
            empleado_existente = existente_telefono.data[0]
            return jsonify({"success": False, "msg": f"El telefono {telefono_str} ya esta registrado a nombre de: {empleado_existente.get('nombre', 'N/A')} (ID: {empleado_existente.get('cedula', 'N/A')})"})

        contrasena_hash = generate_password_hash(contrasena)
        master_key = generate_master_key()
        foto_url = None

        if foto:
            if not is_valid_image(foto):
                return jsonify({"success": False, "msg": "Formato de imagen no permitido."}), 400
            try:
                filename = f"empleados/{cedula}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
                file_bytes = foto.read()
                upload_response = supabase.storage.from_("Fotos").upload(filename, file_bytes)
                if hasattr(upload_response, "error") and upload_response.error:
                    return jsonify({"success": False, "msg": "Error al subir la foto al servidor."})
                foto_url = f"{SUPABASE_URL}/storage/v1/object/public/Fotos/{filename}"
            except Exception as e:
                return jsonify({"success": False, "msg": "Error al procesar la imagen."})

        data = {
            "cedula": cedula_int,
            "nombre": nombre_normalizado,
            "telefono": telefono_str,
            "contrasena": contrasena_hash,
            "master_key": master_key,
            "master_key_visto": False,
            "foto": foto_url,
            "habilitado": True
        }

        response = supabase.table("empleados").insert(data).execute()
        if hasattr(response, "data") and response.data:
            return jsonify({"success": True, "msg": f"Empleado {nombre_normalizado} registrado correctamente."})
        else:
            return jsonify({"success": False, "msg": "No se pudo registrar el empleado. Verifica los datos."})
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "msg": "Error inesperado al registrar empleado."})

@app.route("/buscar_empleado", methods=["POST"])
@login_requerido(rol='Administrador')
def buscar_empleado():
    try:
        data = request.get_json()
        termino = data.get("termino", "").strip()
        if termino:
            response = supabase.table("empleados").select("*").ilike("nombre", f"%{termino}%").execute()
            if not response.data:
                response = supabase.table("empleados").select("*").ilike("cedula", f"%{termino}%").execute()
        else:
            response = supabase.table("empleados").select("*").execute()
        return jsonify({"success": True, "empleados": response.data or []})
    except Exception as e:
        print("Error en busqueda de empleado:", e)
        return jsonify({"success": False, "msg": "Error en el servidor"})

@app.route("/editar_empleado/<int:cedula>", methods=["PUT"])
@login_requerido(rol='Administrador')
def editar_empleado(cedula):
    try:
        data = request.get_json()
        nombre = data.get("nombre")
        
        if not nombre:
            return jsonify({"success": False, "msg": "El nombre es obligatorio."}), 400

        if any(char.isdigit() for char in nombre):
            return jsonify({"success": False, "msg": "El nombre no puede contener numeros."}), 400

        nombre_limpio = re.sub(r"\s+", " ", nombre).strip().lower()
        if len(nombre_limpio) < 2 or len(nombre_limpio) > 100:
            return jsonify({"success": False, "msg": "El nombre debe tener entre 2 y 100 caracteres."}), 400
        
        response = supabase.table("empleados").update({
            "nombre": nombre_limpio
        }).eq("cedula", cedula).execute()
        
        if response.data:
            return jsonify({"success": True, "msg": "Empleado actualizado correctamente."}), 200
        else:
            return jsonify({"success": False, "msg": "No se pudo actualizar el empleado."}), 500
            
    except Exception as e:
        print("Error al editar empleado:", e)
        return jsonify({"success": False, "msg": "Error interno del servidor."}), 500

@app.route("/cambiar_estado_empleado/<int:cedula>", methods=["POST"])
@login_requerido(rol='Administrador')
def cambiar_estado_empleado(cedula):
    try:
        data = request.get_json()
        habilitado = data.get("habilitado")
        if habilitado is None:
            return jsonify({"success": False, "msg": "Estado no especificado."}), 400
        response = supabase.table("empleados").update({"habilitado": habilitado}).eq("cedula", cedula).execute()
        if hasattr(response, "data") and response.data:
            estado = "habilitado" if habilitado else "deshabilitado"
            return jsonify({"success": True, "msg": f"Empleado {estado} correctamente."})
        else:
            return jsonify({"success": False, "msg": "No se encontro el empleado."}), 404
    except Exception as e:
        print("Error al cambiar estado del empleado:", e)
        return jsonify({"success": False, "msg": f"Error en servidor: {e}"}), 500


@app.route('/Ad_Rproductos', methods=['GET', 'POST'])
@login_requerido(rol='Administrador')
def Ad_Rproductos():
    return render_template("Ad_templates/Ad_Rproductos.html")

@app.route('/registrar_producto', methods=['POST'])
@login_requerido(rol='Administrador')
def registrar_producto():
    nombre = request.form.get('nombre')
    categoria = request.form.get('categoria')
    unidad = request.form.get('unidad')
    foto = request.files.get('foto')

    if not (nombre and categoria and unidad):
        return jsonify({"success": False, "msg": "Todos los campos son obligatorios."})

    nombre_limpio = nombre.strip()
    if len(nombre_limpio) < 2 or len(nombre_limpio) > 100:
        return jsonify({"success": False, "msg": "El nombre del producto debe tener entre 2 y 100 caracteres."})
    if re.search(r"\s{2,}", nombre_limpio):
        return jsonify({"success": False, "msg": "El nombre no debe tener espacios dobles."})
    if re.search(r"\d", nombre_limpio):
        return jsonify({"success": False, "msg": "El nombre no debe contener numeros."})
    if not re.fullmatch(r"^[A-Za-zAEIOUaeiouNn ()\-'/&.,%+]+$", nombre_limpio):
        return jsonify({"success": False, "msg": "El nombre contiene caracteres no permitidos."})
    nombre_colapsado = re.sub(r"\s+", " ", nombre_limpio).strip()
    nombre_normalizado = nombre_colapsado.lower()

    categoria_limpia = categoria.strip()
    if len(categoria_limpia) < 1 or len(categoria_limpia) > 50:
        return jsonify({"success": False, "msg": "La categoria debe tener entre 1 y 50 caracteres."})

    unidad_limpia = unidad.strip()
    if len(unidad_limpia) < 1 or len(unidad_limpia) > 20:
        return jsonify({"success": False, "msg": "La unidad debe tener entre 1 y 20 caracteres."})

    try:
        data = {
            "nombre": nombre_normalizado,
            "categoria": categoria_limpia,
            "unidad": unidad_limpia,
            "habilitado": True,
            "foto": None
        }
        response = supabase.table("productos").insert(data).execute()
        if not (hasattr(response, "data") and response.data):
            return jsonify({"success": False, "msg": "Error al registrar producto."})
        producto_id = response.data[0]["id_producto"]
    except Exception as e:
        print("Error al insertar producto:", e)
        return jsonify({"success": False, "msg": f"Error en servidor: {e}"})

    foto_url = None
    if foto:
        if not is_valid_image(foto):
            return jsonify({"success": False, "msg": "Formato de imagen no permitido."}), 400
        try:
            filename = f"productos/{producto_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
            upload_response = supabase.storage.from_("Fotos").upload(filename, foto.read())
            if hasattr(upload_response, "error") and upload_response.error:
                print("Error al subir imagen:", upload_response.error)
                return jsonify({"success": False, "msg": "Error al subir imagen."})
            foto_url = f"{SUPABASE_URL}/storage/v1/object/public/Fotos/{filename}"
            supabase.table("productos").update({"foto": foto_url}).eq("id_producto", producto_id).execute()
        except Exception as e:
            print("Error al subir foto:", e)
            return jsonify({"success": False, "msg": "Error al subir foto."})

    return jsonify({
        "success": True,
        "msg": f"Producto registrado correctamente con el serial #{producto_id}.",
        "id_generado": producto_id,
        "foto_url": foto_url
    })

@app.route("/buscar_producto", methods=["POST"])
@login_requerido(rol='Administrador')
def buscar_producto():
    try:
        data = request.get_json()
        termino = data.get("termino", "").strip()
        if not termino:
            response = supabase.table("productos").select("*").execute()
            return jsonify({"success": True, "productos": response.data})
        response = supabase.table("productos").select("*").execute()
        productos = response.data if hasattr(response, "data") else []
        termino_lower = termino.lower()
        productos_filtrados = [
            p for p in productos
            if termino_lower in str(p.get("id_producto", "")).lower()
            or termino_lower in str(p.get("nombre","")).lower()
            or termino_lower in str(p.get("categoria","")).lower()
        ]
        if not productos_filtrados:
            return jsonify({"success": False, "msg": "No se encontraron productos", "productos": []})
        return jsonify({"success": True, "productos": productos_filtrados})
    except Exception as e:
        print("Error en busqueda de producto:", e)
        return jsonify({"success": False, "msg": "Error en servidor"}), 500

@app.route("/obtener_proximo_id",methods=["GET"])
@login_requerido(rol='Administrador')
def obtener_proximo_id():
    try:
        response = supabase.table("productos").select("id_producto").order("id_producto", desc=True).limit(1).execute()
        if hasattr(response, "data") and response.data:
            ultimo_id = response.data[0]["id_producto"]
            proximo_id = ultimo_id + 1
        else:
            proximo_id = 1
        return jsonify({"success": True, "proximo_id": proximo_id})
    except Exception as e:
        print("Error al obtener proximo ID de producto:", e)
        return jsonify({"success": False, "msg": "Error en servidor"}), 500

@app.route("/editar_producto/<int:id_producto>", methods=["POST"])  # Cambiado a POST para soportar archivos
@login_requerido(rol='Administrador')
def editar_producto(id_producto):
    try:
        # 📨 Recibir datos como FORMDATA (no JSON)
        nombre = request.form.get('nombre')
        categoria = request.form.get('categoria')
        unidad = request.form.get('unidad')
        foto = request.files.get('foto')

        update_data = {
            "nombre": nombre,
            "categoria": categoria,
            "unidad": unidad
        }
        
        if not (nombre and categoria and unidad):
            return jsonify({"success": False, "msg": "Todos los campos son obligatorios."}), 400

        nombre_limpio = nombre.strip()
        if len(nombre_limpio) < 2 or len(nombre_limpio) > 100:
            return jsonify({"success": False, "msg": "El nombre del producto debe tener entre 2 y 100 caracteres."}), 400
        
        if re.search(r"\d", nombre_limpio):
            return jsonify({"success": False, "msg": "El nombre no debe contener numeros."}), 400
        
        # Validaciones extra igual que en registro...
        nombre_normalizado = re.sub(r"\s+", " ", nombre_limpio).strip().lower()

        data_update = {
            "nombre": nombre_normalizado,
            "categoria": categoria.strip(),
            "unidad": unidad.strip()
        }

        # 📸 Si hay foto nueva, subirla
        if foto:
            if not is_valid_image(foto):
                return jsonify({"success": False, "msg": "Formato de imagen no permitido."}), 400
            try:
                # Nombre unico para evitar cache
                filename = f"productos/{id_producto}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
                upload_response = supabase.storage.from_("Fotos").upload(filename, foto.read())
                
                if hasattr(upload_response, "error") and upload_response.error:
                    print("Error subiendo foto:", upload_response.error)
                else:
                    foto_url = f"{SUPABASE_URL}/storage/v1/object/public/Fotos/{filename}"
                    data_update["foto"] = foto_url
            except Exception as e:
                print("Excepcion al subir foto en edicion:", e)

        response = supabase.table("productos").update(data_update).eq("id_producto", id_producto).execute()
        
        if hasattr(response, "data") and response.data:
            return jsonify({"success": True, "msg": "Producto actualizado correctamente."})
        else:
            return jsonify({"success": False, "msg": "No se pudo actualizar el producto."}), 500
    except Exception as e:
        print("Error al editar producto:", e)
        return jsonify({"success": False, "msg": f"Error en servidor: {e}"}), 500

@app.route("/cambiar_estado_producto/<int:id_producto>", methods=["POST"])
@login_requerido(rol='Administrador')
def cambiar_estado_producto(id_producto):
    try:
        data = request.get_json()
        habilitado = data.get("habilitado")
        if habilitado is None:
            return jsonify({"success": False, "msg": "Estado no especificado."}), 400
        response = supabase.table("productos").update({"habilitado": habilitado}).eq("id_producto", id_producto).execute()
        if hasattr(response, "data") and response.data:
            estado = "habilitado" if habilitado else "deshabilitado"
            return jsonify({"success": True, "msg": f"Producto {estado} correctamente."})
        else:
            return jsonify({"success": False, "msg": "No se encontro el producto."}), 404
    except Exception as e:
        print("Error al cambiar estado del producto:", e)
        return jsonify({"success": False, "msg": f"Error en servidor: {e}"}), 500

@app.route('/Ad_Recetarios', methods=['GET'])
@login_requerido(rol='Administrador')
def Ad_Recetarios():
    try:
        response = supabase.table("recetarios").select("*").order("created_at", desc=True).execute()
        recetas = response.data or []
        return render_template("Ad_templates/Ad_Recetarios.html", recetas=recetas)
    except Exception as e:
        print("Error en Ad_Recetarios:", e)
        return render_template("Ad_templates/Ad_Recetarios.html", recetas=[])

@app.route('/get_productos_receta', methods=['GET'])
@login_requerido(rol='Administrador')
def get_productos_receta():
    try:
        response = supabase.table("productos").select("id_producto, nombre, unidad").eq("habilitado", True).execute()
        return jsonify({"success": True, "productos": response.data or []})
    except Exception as e:
        print("Error en get_productos_receta:", e)
        return jsonify({"success": False, "msg": str(e)})

@app.route('/registrar_receta', methods=['POST'])
@login_requerido(rol='Administrador')
def registrar_receta():
    try:
        nombre = request.form.get('nombre')
        descripcion = request.form.get('descripcion')
        foto = request.files.get('foto')
        ingredientes_json = request.form.get('ingredientes')

        if not (nombre and ingredientes_json):
            return jsonify({"success": False, "msg": "Nombre e ingredientes son obligatorios."})

        # Validar que el nombre no contenga numeros
        import re
        if re.search(r'\d', nombre):
            return jsonify({"success": False, "msg": "El nombre de la receta no puede contener numeros."})

        import json
        try:
            ingredientes = json.loads(ingredientes_json)
        except Exception as json_err:
            print("Error decodificando ingredientes JSON:", json_err)
            return jsonify({"success": False, "msg": "Error en el formato de ingredientes."})

        if not ingredientes or not isinstance(ingredientes, list):
            return jsonify({"success": False, "msg": "Debe agregar al menos un ingrediente valido."})

        # 1. Insertar en recetarios
        receta_data = {
            "nombre": nombre,
            "descripcion": descripcion,
            "habilitado": True
        }
        
        insert_res = supabase.table("recetarios").insert(receta_data).execute()
        
        if not (hasattr(insert_res, "data") and insert_res.data):
            error_msg = getattr(insert_res, "error", "Error desconocido al insertar receta")
            print("Error Supabase (recetarios):", error_msg)
            return jsonify({"success": False, "msg": "No se pudo crear la base de la receta."})
        
        id_receta = insert_res.data[0]["id_receta"]

        # 2. Subir foto si existe
        foto_url = None
        if foto and is_valid_image(foto):
            try:
                filename = f"recetas/{id_receta}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
                foto.seek(0) # Asegurar lectura desde el inicio
                supabase.storage.from_("Fotos").upload(filename, foto.read())
                foto_url = f"{SUPABASE_URL}/storage/v1/object/public/Fotos/{filename}"
                supabase.table("recetarios").update({"foto": foto_url}).eq("id_receta", id_receta).execute()
            except Exception as upload_err:
                print(f"Error subiendo foto de receta {id_receta}:", upload_err)
                # No retornamos error aqui para permitir que la receta se guarde sin foto si falla el upload

        # 3. Insertar detalles
        errores_detalles = []
        for ing in ingredientes:
            try:
                detalle_data = {
                    "id_receta": id_receta,
                    "id_producto": int(ing["id_producto"]),
                    "cantidad": float(ing["cantidad"]),
                    "unidad": ing.get("unidad", "und")
                }
                det_res = supabase.table("receta_detalle").insert(detalle_data).execute()
                if not (hasattr(det_res, "data") and det_res.data):
                    errores_detalles.append(f"Producto {ing['id_producto']}")
            except Exception as det_err:
                print(f"Error insertando detalle para producto {ing.get('id_producto')}:", det_err)
                errores_detalles.append(str(ing.get('id_producto')))

        if errores_detalles:
            return jsonify({
                "success": True, 
                "msg": f"Receta creada, pero hubo problemas con algunos ingredientes: {', '.join(errores_detalles)}"
            })

        return jsonify({"success": True, "msg": "Receta creada exitosamente."})

    except Exception as e:
        print("Error critico en registrar_receta:", e)
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "msg": f"Error interno: {str(e)}"})

@app.route('/cambiar_estado_receta/<int:id_receta>', methods=['POST'])
@login_requerido(rol='Administrador')
def cambiar_estado_receta(id_receta):
    try:
        data = request.get_json()
        habilitado = data.get("habilitado")
        supabase.table("recetarios").update({"habilitado": habilitado}).eq("id_receta", id_receta).execute()
        return jsonify({"success": True, "msg": "Estado de receta actualizado."})
    except Exception as e:
        return jsonify({"success": False, "msg": str(e)})

@app.route('/Ad_Inventario')
@login_requerido(rol='Administrador')
def Ad_Inventario():
    try:
        locales = supabase.table("locales").select("*").execute().data or []
        return render_template("Ad_templates/Ad_Inventario.html", locales=locales)
    except Exception as e:
        print("Error en Ad_Inventario:", e)
        return render_template("Ad_templates/Ad_Inventario.html", locales=[])

@app.route('/Em_Inventario')
@login_requerido(rol='Empleado')
def Em_Inventario():
    return render_template("Em_templates/Em_Inventario.html")

@app.route('/get_inventario_data', methods=['POST'])
@login_requerido()
def get_inventario_data():
    try:
        data = request.get_json()
        id_local = data.get('id_local')
        if session.get('role') == 'Empleado':
            id_local = session.get('branch')
        
        if not id_local:
            return jsonify({"success": False, "msg": "Local no especificado."})

        # Query consolidada: agrupar por producto y sumar cantidades
        # Nota: PostgREST no agrupa facilmente, lo hacemos en python o con una vista en DB.
        # Por ahora lo hacemos en python para mayor control.
        res = supabase.table("inventario").select("cantidad, stock_minimo, productos(id_producto, nombre, unidad, categoria)")\
            .eq("id_local", id_local).execute()
        
        # Agrupar
        inventario_agrupado = {}
        for item in (res.data or []):
            prod = item.get("productos")
            if not prod: continue
            pid = prod["id_producto"]
            if pid not in inventario_agrupado:
                inventario_agrupado[pid] = {
                    "id_producto": pid,
                    "nombre": prod["nombre"],
                    "unidad": prod["unidad"],
                    "categoria": prod["categoria"],
                    "stock": 0,
                    "minimo": item.get("stock_minimo", 0)
                }
            inventario_agrupado[pid]["stock"] += item["cantidad"]
            # Tomamos el minimo mas alto de los lotes como referencia (o el primero)
            inventario_agrupado[pid]["minimo"] = max(inventario_agrupado[pid]["minimo"], item.get("stock_minimo", 0))
            
        return jsonify({"success": True, "inventario": list(inventario_agrupado.values())})
    except Exception as e:
        return jsonify({"success": False, "msg": str(e)})




# ==============================================================================
# 6. ADMINISTRACION - DASHBOARD E INFORMES
# ==============================================================================

@app.route('/Ad_Inicio', methods=['GET', 'POST'])
@login_requerido(rol='Administrador')
def Ad_Inicio():
    try:
        generar_notificaciones_caducidad()
        generar_notificaciones_stock_bajo()
        eliminar_notificaciones_caducadas()
        
        try:
            todas_response = supabase.table("notificaciones").select("*").order("fecha", desc=True).execute()
            todas = todas_response.data if todas_response.data else []
        except Exception as db_error:
            print(f"Error al consultar notificaciones: {db_error}")
            todas = []

        todas_filtradas = []
        for n in todas:
            mensaje = n.get("mensaje", "")
            if mensaje is not None and str(mensaje).strip() != "":
                todas_filtradas.append(n)

        if not todas_filtradas:
            notificacion_prueba = {
                "mensaje": "NOTIFICACION DE PRUEBA - Sistema funcionando",
                "fecha_formateada": datetime.now().strftime("%d de %B de %Y, %I:%M %p"),
                "leido": False
            }
            todas_filtradas.append(notificacion_prueba)

        try:
            locale.setlocale(locale.LC_TIME, "es_ES.utf8")
        except:
            try:
                locale.setlocale(locale.LC_TIME, "es_CO.utf8")
            except:
                pass

        for noti in todas_filtradas:
            if noti.get("fecha") and not noti.get("fecha_formateada"):
                try:
                    fecha_str = noti["fecha"]
                    if 'T' in fecha_str:
                        fecha_obj = datetime.fromisoformat(fecha_str.replace('Z', '+00:00'))
                    else:
                        fecha_obj = datetime.strptime(fecha_str, "%Y-%m-%d %H:%M:%S")
                    
                    noti["fecha_formateada"] = fecha_obj.strftime("%d de %B de %Y, %I:%M %p").capitalize()
                except Exception as date_error:
                    print(f"Error al formatear fecha {noti['fecha']}: {date_error}")
                    noti["fecha_formateada"] = noti["fecha"]

        notificaciones = todas_filtradas[:3]
        total_notificaciones = len(todas_filtradas)
        restantes = max(0, total_notificaciones - 3)

        http_response = make_response(render_template(
            "Ad_templates/Ad_Inicio.html",
            notificaciones=notificaciones,
            restantes=restantes,
            total_notificaciones=total_notificaciones
        ))
        http_response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        http_response.headers['Pragma'] = 'no-cache'
        http_response.headers['Expires'] = '-1'
        return http_response
        
    except Exception as e:
        print(f"Error critico al cargar pagina de inicio: {e}")
        import traceback
        traceback.print_exc()
        return render_template("Ad_templates/Ad_Inicio.html", 
                             notificaciones=[], 
                             restantes=0, 
                             total_notificaciones=0), 500


def obtener_rango_fecha(periodo, fecha_str):
    try:
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d")
        if periodo == "diario":
            inicio = fecha.replace(hour=0, minute=0, second=0)
            fin = fecha.replace(hour=23, minute=59, second=59)
        elif periodo == "semanal":
            inicio = fecha - timedelta(days=fecha.weekday())
            inicio = inicio.replace(hour=0, minute=0, second=0)
            fin = inicio + timedelta(days=6, hours=23, minutes=59, seconds=59)
        elif periodo == "mensual":
            inicio = fecha.replace(day=1, hour=0, minute=0, second=0)
            if fecha.month == 12:
                proximo_mes = fecha.replace(year=fecha.year + 1, month=1, day=1)
            else:
                proximo_mes = fecha.replace(month=fecha.month + 1, day=1)
            fin = proximo_mes - timedelta(seconds=1)
        elif periodo == "anual":
            inicio = fecha.replace(month=1, day=1, hour=0, minute=0, second=0)
            fin = fecha.replace(month=12, day=31, hour=23, minute=59, second=59)
        else:
            inicio = fin = fecha
        return inicio.isoformat(), fin.isoformat()
    except:
        return fecha_str, fecha_str

def to_num(val):
    try: return round(float(val), 2)
    except: return 0

# --- HELPER DISENO C: MODERN HYBRID ---
def dibujar_sidebar_premium(canvas, doc):
    """Dibuja la barra lateral negra y el branding vertical del Diseno C"""
    canvas.saveState()
    # 1. Barra lateral negra (#111)
    canvas.setFillColor(colors.HexColor("#111111"))
    canvas.rect(0, 0, 50, letter[1], fill=1, stroke=0)
    
    # 2. Branding Vertical
    canvas.rotate(90)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 14)
    # Posicionamiento vertical (recordar que rotamos 90 grados)
    canvas.drawString(100, -32, "ICHIRAKU RAMEN")
    
    canvas.setFillColor(colors.HexColor("#E63900"))
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawString(240, -32, "| SISTEMA DE GESTION")
    
    canvas.restoreState()

@app.route('/generar_reporte_personalizado', methods=['POST'])
@login_requerido(rol='Administrador')
def generar_reporte_personalizado():
    try:
        id_l = request.form.get('id_local')
        periodo = request.form.get('periodo', 'diario')
        fecha_base = request.form.get('fecha', datetime.now().strftime("%Y-%m-%d"))
        
        if not id_l: return jsonify({"success": False, "msg": "Debes seleccionar un local para generar el reporte."}), 400
        
        f_ini, f_fin = obtener_rango_fecha(periodo, fecha_base)
        
        # 1. Obtener datos del local
        local_info = supabase.table("locales").select("nombre").eq("id_local", id_l).execute()
        nombre_local = local_info.data[0]["nombre"] if local_info.data else "Desconocido"

        # 2. Obtener Consumo del periodo con detalles
        cons_res = supabase.table("consumo").select("*, consumo_detalle(*, productos(nombre, unidad))")\
            .eq("id_local", id_l).gte("fecha", f_ini).lte("fecha", f_fin).execute()
        consumos = cons_res.data or []

        # 3. Procesar y categorizar: Ventas vs Merma
        resumen_productos = {} # {id_prod: {nombre, unidad, venta: 0, merma: 0}}
        total_ventas_count = 0
        total_merma_items = 0

        for c in consumos:
            is_merma = "[MERMA]" in (c.get("observacion") or "")
            if is_merma:
                total_merma_items += 1
            else:
                total_ventas_count += c.get("cantidad_platos", 0)

            for det in c.get("consumo_detalle", []):
                p = det.get("productos")
                if not p: continue
                pid = det["id_producto"]
                if pid not in resumen_productos:
                    resumen_productos[pid] = {
                        "nombre": p["nombre"],
                        "unidad": p["unidad"],
                        "venta": 0,
                        "merma": 0
                    }
                
                cant = float(det["cantidad_consumida"])
                if is_merma:
                    resumen_productos[pid]["merma"] += cant
                else:
                    resumen_productos[pid]["venta"] += cant

        # Generar PDF con ReportLab - DISENO C
        buffer = io.BytesIO()
        # Margen izquierdo amplio para el sidebar (50 sidebar + 20 espacio)
        doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=70, topMargin=50, bottomMargin=50)
        styles = getSampleStyleSheet()
        
        # Estilos personalizados para Diseno C
        style_title = styles['Title']
        style_title.alignment = 0 # Izquierda
        style_title.fontName = "Helvetica-Bold"
        style_title.fontSize = 22
        style_title.textColor = colors.HexColor("#111111")
        
        style_h2 = styles['Heading2']
        style_h2.textColor = colors.HexColor("#E63900")
        style_h2.fontSize = 14
        style_h2.borderPadding = 5
        
        elements = []
        
        # Titulo y Encabezado
        elements.append(Paragraph(f"INFORME TECNICO DE INVENTARIO", style_title))
        elements.append(Spacer(1, 5))
        
        # Barra de acento rojo bajo el titulo
        elements.append(Table([[""]], colWidths=[480], style=[('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#E63900"))]))
        elements.append(Spacer(1, 15))

        elements.append(Paragraph(f"<b>Sede:</b> {nombre_local.upper()} | <b>Periodo:</b> {periodo.upper()}", styles['Normal']))
        elements.append(Paragraph(f"<b>Rango:</b> {f_ini[:10]} - {f_fin[:10]}", styles['Normal']))
        elements.append(Spacer(1, 25))

        # Resumen Ejecutivo (Con diseno de tarjetas minimalistas)
        elements.append(Paragraph("1. Resumen Ejecutivo (Metricas Clave)", style_h2))
        elements.append(Spacer(1, 10))
        
        resumen_data = [
            ["PLANTILLAS VENDIDAS", "MERMA / ERROR", "ESTADO OPERATIVO"],
            [f"{total_ventas_count}", f"{total_merma_items}", "Auditado"]
        ]
        t_res = Table(resumen_data, colWidths=[160, 160, 160])
        t_res.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.grey),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, 1), 16),
            ('TEXTCOLOR', (0, 1), (0, 1), colors.black),
            ('TEXTCOLOR', (1, 1), (1, 1), colors.HexColor("#E63900")),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(t_res)
        elements.append(Spacer(1, 30))

        # Detalle por Producto
        elements.append(Paragraph("2. Consumo Detallado por Insumo", style_h2))
        elements.append(Spacer(1, 12))
        
        data_prod = [["INSUMO", "UNIDAD", "VENTAS", "MERMA", "TOTAL"]]
        
        sorted_products = sorted(resumen_productos.values(), key=lambda x: x['nombre'])
        for p in sorted_products:
            total = p['venta'] + p['merma']
            data_prod.append([
                p['nombre'].upper(), 
                p['unidad'], 
                int(p['venta']), 
                int(p['merma']), 
                int(total)
            ])

        t_prod = Table(data_prod, colWidths=[180, 70, 70, 70, 90])
        t_prod.setStyle(TableStyle([
            # Minimal header con subrayado rojo
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor("#E63900")),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            
            # Body clean
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor("#333333")),
            ('ALIGN', (2, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 1), (-1, -1), 0.25, colors.lightgrey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9F9F9")]),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ]))
        elements.append(t_prod)
        
        elements.append(Spacer(1, 40))
        elements.append(Paragraph(f"<i>Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')} - Sistema Ichiraku</i>", styles['Italic']))

        # Build con Sidebar
        doc.build(elements, onFirstPage=dibujar_sidebar_premium, onLaterPages=dibujar_sidebar_premium)
        buffer.seek(0)
        
        filename = f"Informe_{nombre_local}_{fecha_base}_{periodo}.pdf"
        
        # 5. Persistencia en la base de datos para el historial
        try:
            nuevo_informe = {
                "fecha_creacion": datetime.now().isoformat(),
                "tipo": "inventario_premium",
                "fecha_inicio": f_ini[:10],
                "fecha_fin": f_fin[:10],
                "pedidos_ids": {
                    "id_local": id_l,
                    "nombre_local": nombre_local,
                    "periodo": periodo,
                    "fecha_base": fecha_base
                }
            }
            supabase.table("informe").insert(nuevo_informe).execute()
        except Exception as db_e:
            print(f"Error al persistir informe premium: {db_e}")

        response = make_response(buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename={filename}'
        return response
        
    except Exception as e:
        return jsonify({"success": False, "msg": f"Error generando reporte: {str(e)}"}), 500

@app.route('/Ad_Dinformes', methods=['GET'])
@login_requerido(rol='Administrador')
def Ad_Dinformes():
    try:
        ultimo_informe = None
        informes = supabase.table("informe").select("*").order("id_informe", desc=True).limit(1).execute()
        
        if informes.data:
            ultimo_informe = informes.data[0]
        
        locales = supabase.table("locales").select("*").execute().data or []
        today = datetime.now().strftime("%Y-%m-%d")
        
        return render_template("Ad_templates/Ad_Dinformes.html", 
                               ultimo_informe=ultimo_informe, 
                               locales=locales,
                               today=today)
    except Exception as e:
        print("Error al cargar pagina de informes:", e)
        return render_template("Ad_templates/Ad_Dinformes.html", ultimo_informe=None, locales=[], today="")

def crear_informe_consolidado(pedidos, fecha):
    try:
        fecha_inicio = f"{fecha}T00:00:00"
        fecha_fin = f"{fecha}T23:59:59"
        
        informe_existente = supabase.table("informe").select("*") \
            .gte("fecha_creacion", fecha_inicio) \
            .lte("fecha_creacion", fecha_fin) \
            .execute().data
        
        if informe_existente:
            return False
        
        nuevo_informe = {
            "fecha_creacion": datetime.now().isoformat(),
            "tipo": "diario_consolidado",
            "total_pedidos": len(pedidos)
        }
        
        result = supabase.table("informe").insert(nuevo_informe).execute()
        
        if result.data:
            return True
        return False
        
    except Exception as e:
        print("Error al crear informe consolidado:", e)
        return False


def generar_pdf_consolidado(informe_id, pedidos):
    try:
        buffer = io.BytesIO()
        # Margen izquierdo amplio para el sidebar
        doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=75, rightMargin=40, topMargin=50, bottomMargin=50)
        styles = getSampleStyleSheet()
        
        # Estilos personalizados para Diseno C
        style_title = styles['Title']
        style_title.alignment = 0 
        style_title.fontName = "Helvetica-Bold"
        style_title.fontSize = 20
        style_title.textColor = colors.HexColor("#111111")
        
        style_h2 = styles['Heading2']
        style_h2.textColor = colors.HexColor("#E63900")
        style_h2.fontSize = 14
        
        elements = []

        # Titulo principal
        elements.append(Paragraph(f"INFORME DIARIO CONSOLIDADO", style_title))
        elements.append(Spacer(1, 5))
        
        # Barra de acento rojo
        elements.append(Table([[""]], colWidths=[480], style=[('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#E63900"))]))
        elements.append(Spacer(1, 15))
        
        # Informacion del informe
        fecha_actual = datetime.now().strftime('%d de %B, %Y')
        info_data = [
            [Paragraph(f"<b>ID INFORME:</b> #{informe_id}", styles['Normal']),
             Paragraph(f"<b>FECHA GENERACION:</b> {fecha_actual}", styles['Normal'])]
        ]
        info_table = Table(info_data, colWidths=[240, 240])
        info_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 20))

        # ========================
        # PROCESAR DATOS
        # ========================
        total_productos = 0
        categorias_totales = {}
        locales_participantes = set()
        productos_detallados = []
        horas_pedidos = []

        if not isinstance(pedidos, list):
            pedidos = []

        for pedido in pedidos:
            try:
                if not isinstance(pedido, dict):
                    continue
                    
                pedido_id = pedido.get('id_pedido')
                if pedido_id is None:
                    continue

                # Obtener detalles del pedido
                try:
                    detalles = supabase.table("detalle_pedido").select("id_producto, cantidad")\
                        .eq("id_pedido", pedido_id).execute().data or []
                except Exception as e:
                    detalles = []

                # Obtener informacion del local
                inventario_id = pedido.get("id_inventario")
                local_nombre = "No especificado"
                
                if inventario_id:
                    try:
                        inventario_result = supabase.table("inventario").select("id_local")\
                            .eq("id_inventario", inventario_id).execute()
                        
                        if inventario_result.data:
                            local_id = inventario_result.data[0].get("id_local")
                            if local_id:
                                local_result = supabase.table("locales").select("nombre")\
                                    .eq("id_local", local_id).execute()
                                if local_result.data:
                                    local_nombre = local_result.data[0].get('nombre', 'No especificado')
                                    locales_participantes.add(local_nombre)
                    except Exception as e:
                        pass

                # Obtener fecha y hora
                fecha_pedido_raw = pedido.get("fecha_pedido")
                fecha_pedido_str = fecha_pedido_raw if isinstance(fecha_pedido_raw, str) else datetime.now().isoformat()
                
                try:
                    hora = datetime.fromisoformat(fecha_pedido_str).strftime("%H:%M")
                    horas_pedidos.append(hora)
                except Exception:
                    hora = "N/A"

                # Procesar productos del pedido
                for detalle in detalles:
                    if not isinstance(detalle, dict):
                        continue
                        
                    cantidad_detalle = detalle.get('cantidad', 0)
                    id_producto = detalle.get('id_producto')
                    
                    if not id_producto:
                        continue

                    total_productos += int(cantidad_detalle)
                    
                    try:
                        producto_result = supabase.table("productos").select("nombre, categoria, unidad")\
                            .eq("id_producto", id_producto).execute()
                        
                        if producto_result.data:
                            producto_info = producto_result.data[0]
                            cat = producto_info.get('categoria', 'Sin categoria')
                            categorias_totales[cat] = categorias_totales.get(cat, 0) + cantidad_detalle
                            
                            producto_detalle = {
                                'pedido_id': int(pedido_id) if pedido_id else 0,
                                'local': str(local_nombre),
                                'producto': str(producto_info.get('nombre', 'Desconocido')),
                                'categoria': str(cat),
                                'cantidad': int(cantidad_detalle),
                                'unidad': str(producto_info.get('unidad', 'und')),
                                'hora': str(hora)
                            }
                            productos_detallados.append(producto_detalle)
                    except Exception as e:
                        continue
                        
            except Exception as e:
                continue

        # Calcular metricas
        hora_primero = min(horas_pedidos) if horas_pedidos else "N/A"
        hora_ultimo = max(horas_pedidos) if horas_pedidos else "N/A"

        # ========================
        # RESUMEN EJECUTIVO (MODERN CARDS)
        # ========================
        elements.append(Paragraph("1. Resumen Ejecutivo de Operacion", style_h2))
        elements.append(Spacer(1, 12))
        
        res_data = [
            ["TOTAL PEDIDOS", "PRODUCTOS", "OPERACION", "LOCALES"],
            [f"{len(pedidos)}", f"{total_productos}", f"{hora_primero}-{hora_ultimo}", f"{len(locales_participantes)}"]
        ]
        t_res = Table(res_data, colWidths=[120, 120, 120, 120])
        t_res.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.grey),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, 1), 14),
            ('TEXTCOLOR', (0, 1), (-1, 1), colors.black),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(t_res)
        elements.append(Spacer(1, 25))
        
        if locales_participantes:
            locs = ", ".join(sorted(locales_participantes))
            elements.append(Paragraph(f"<b>Locales impactados:</b> {locs}", styles['Normal']))
            elements.append(Spacer(1, 20))

        elements.append(Spacer(1, 30))

        # ========================
        # DISTRIBUCION POR CATEGORIAS (CLEAN TABLE)
        # ========================
        if categorias_totales:
            elements.append(Paragraph("2. Distribucion General por Categorias", style_h2))
            elements.append(Spacer(1, 12))
            
            categorias_data = [["CATEGORIA", "CANTIDAD", "PORCENTAJE"]]
            total_categorias = sum(categorias_totales.values())
            
            for cat, cant in sorted(categorias_totales.items(), key=lambda x: x[1], reverse=True):
                porc = (cant / total_categorias) * 100 if total_categorias > 0 else 0
                categorias_data.append([cat.upper(), f"{cant} und", f"{porc:.1f}%"])
            
            t_cat = Table(categorias_data, colWidths=[200, 140, 140])
            t_cat.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('LINEBELOW', (0, 0), (-1, 0), 1.5, colors.HexColor("#E63900")),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9F9F9")]),
                ('TOPPADDING', (0, 1), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            ]))
            elements.append(t_cat)
            elements.append(Spacer(1, 30))

        # ========================
        # DETALLE DE PEDIDOS - DISENO LIMPIO
        # ========================
        if productos_detallados:
            elements.append(Paragraph(
                "<font size=14 color='#000000'><b>DETALLE DE PEDIDOS</b></font>", 
                styles['Heading2']
            ))
            elements.append(Spacer(1, 15))

            # Agrupar por pedido
            pedidos_agrupados = {}
            for producto in productos_detallados:
                if not isinstance(producto, dict):
                    continue
                    
                pedido_id = producto.get('pedido_id')
                if pedido_id is None:
                    continue
                    
                if pedido_id not in pedidos_agrupados:
                    pedidos_agrupados[pedido_id] = {
                        'local': producto.get('local', 'No especificado'),
                        'hora': producto.get('hora', 'N/A'),
                        'productos': [],
                        'total_cantidad': 0
                    }
                
                pedidos_agrupados[pedido_id]['productos'].append(producto)
                pedidos_agrupados[pedido_id]['total_cantidad'] += producto.get('cantidad', 0)

            for pedido_id, info in sorted(pedidos_agrupados.items()):
                if not info.get('productos'):
                    continue
                
                # Header del pedido minimalista
                elements.append(Paragraph(f"<b>PEDIDO #{pedido_id}</b> | {info['local']} [{info['hora']}]", styles['Normal']))
                elements.append(Spacer(1, 5))
                
                # Tabla de productos minimalista
                table_data = [["PRODUCTO", "CANTIDAD"]]
                for p in info['productos']:
                    table_data.append([p['producto'].upper(), f"{p['cantidad']} {p['unidad']}"])
                
                pedido_table = Table(table_data, colWidths=[340, 140])
                pedido_table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 8),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#666666")),
                    ('LINEBELOW', (0, 0), (-1, 0), 1, colors.lightgrey),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('GRID', (0, 1), (-1, -1), 0.1, colors.lightgrey),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#FDFDFD")]),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                ]))
                elements.append(pedido_table)
                elements.append(Spacer(1, 15))

        # Pie de pagina footer
        elements.append(Spacer(1, 30))
        elements.append(Paragraph(f"<i>Informe Consolidado Ichiraku Ramen - Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}</i>", styles['Italic']))

        # Construir PDF con Sidebar
        doc.build(elements, onFirstPage=dibujar_sidebar_premium, onLaterPages=dibujar_sidebar_premium)
        buffer.seek(0)
        return buffer
        
    except Exception as e:
        print("Error al generar PDF consolidado:", e)
        import traceback
        traceback.print_exc()
        return None

def descargar_informe_consolidado_individual(id_informe):
    try:
        informe_result = supabase.table("informe").select("*").eq("id_informe", id_informe).execute()
        if not informe_result.data:
            return jsonify({"success": False, "msg": "Informe consolidado no encontrado"}), 404
        
        informe = informe_result.data[0]
        fecha_creacion = datetime.fromisoformat(informe["fecha_creacion"])
        fecha = fecha_creacion.date()
        
        # OBTENER PEDIDOS DE ESA FECHA
        todos_pedidos = supabase.table("pedido").select("*").execute().data or []
        
        # FILTRAR PEDIDOS POR FECHA
        pedidos_hoy = []
        for p in todos_pedidos:
            try:
                if isinstance(p, dict) and p.get("fecha_pedido"):
                    fecha_pedido = datetime.fromisoformat(p["fecha_pedido"]).date()
                    if fecha_pedido == fecha:
                        pedidos_hoy.append(p)
            except Exception as e:
                print(f"Error procesando pedido {p}: {e}")
                continue
        
        if not pedidos_hoy:
            return jsonify({"success": False, "msg": "No hay pedidos para esta fecha."})
        
        buffer = generar_pdf_consolidado(id_informe, pedidos_hoy)
        if not buffer:
            return jsonify({"success": False, "msg": "Error al generar el PDF consolidado."})
        
        response = make_response(buffer.read())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=informe_diario_consolidado_{fecha}.pdf'
        return response
        
    except Exception as e:
        print(f"Error al descargar informe consolidado individual {id_informe}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "msg": f"Error: {e}"})


@app.route('/generar_informe_diario', methods=['POST'])
@login_requerido(rol='Administrador')
def generar_informe_diario():
    try:
        hoy = datetime.now().date()
        
        todos_pedidos = supabase.table("pedido").select("*").execute()
        
        if not todos_pedidos.data:
            return jsonify({"success": False, "msg": "No hay pedidos registrados en el sistema."})
        
        pedidos_hoy = [p for p in todos_pedidos.data 
                      if datetime.fromisoformat(p["fecha_pedido"]).date() == hoy]
        
        if not pedidos_hoy:
            return jsonify({"success": False, "msg": "No hay pedidos registrados para hoy."})
        
        fecha_inicio = f"{hoy}T00:00:00"
        fecha_fin = f"{hoy}T23:59:59"
        
        informe_existente = supabase.table("informe").select("*") \
            .gte("fecha_creacion", fecha_inicio) \
            .lte("fecha_creacion", fecha_fin) \
            .eq("tipo", "diario_consolidado") \
            .execute()
        
        # Eliminamos la restriccion de un solo informe por dia para permitir el historial solicitado por el usuario
        
        nuevo_informe = {
            "fecha_creacion": datetime.now().isoformat(),
            "tipo": "diario_consolidado",
            "total_pedidos": len(pedidos_hoy),
            "id_inf_pedido": None
        }
        
        result = supabase.table("informe").insert(nuevo_informe).execute()
        
        if result.data:
            informe_id = result.data[0]['id_informe']
            
            return jsonify({
                "success": True, 
                "msg": f"Informe diario generado exitosamente con {len(pedidos_hoy)} pedidos.",
                "informe_id": informe_id
            })
        else:
            return jsonify({"success": False, "msg": "No se pudo guardar el informe en la base de datos."})
            
    except Exception as e:
        print(f"Error al generar informe diario: {e}")
        return jsonify({"success": False, "msg": f"Error: {str(e)}"})

@app.route('/obtener_ultimo_informe', methods=['GET'])
@login_requerido(rol='Administrador')
def obtener_ultimo_informe():
    try:
        informes = supabase.table("informe").select("*").order("id_informe", desc=True).limit(1).execute()
        
        if informes.data:
            return jsonify({"success": True, "informe": informes.data[0]})
        else:
            return jsonify({"success": False, "msg": "No hay informes generados."})
            
    except Exception as e:
        print("Error al obtener ultimo informe:", e)
        return jsonify({"success": False, "msg": f"Error: {e}"})

@app.route('/buscar_informe', methods=['POST'])
@login_requerido(rol='Administrador')
def buscar_informe():
    try:
        data = request.get_json()
        id_informe, fecha = data.get("id_informe"), data.get("fecha")
        if id_informe:
            informes = supabase.table("informe").select("*").eq("id_informe", id_informe).execute().data
        elif fecha:
            informes = supabase.table("informe").select("*") \
                .gte("fecha_creacion", f"{fecha}T00:00:00") \
                .lte("fecha_creacion", f"{fecha}T23:59:59") \
                .execute().data
        else:
            return jsonify({"success": False, "msg": "Debes ingresar un ID o una fecha."})
        return jsonify({"success": True, "informes": informes}) if informes else jsonify({"success": False, "msg": "No se encontraron informes."})
    except Exception as e:
        print("Error al buscar informe:", e)
        return jsonify({"success": False, "msg": f"Error: {e}"})
    
@app.route('/descargar_informe_diario_consolidado', methods=['GET'])
@login_requerido(rol='Administrador')
def descargar_informe_diario_consolidado():
    try:
        hoy = datetime.now().date()
        
        fecha_inicio = f"{hoy}T00:00:00"
        fecha_fin = f"{hoy}T23:59:59"
        
        informe = supabase.table("informe").select("*") \
            .gte("fecha_creacion", fecha_inicio) \
            .lte("fecha_creacion", fecha_fin) \
            .eq("tipo", "diario_consolidado") \
            .single().execute().data
        
        if not informe:
            return jsonify({"success": False, "msg": "No hay informe diario generado para hoy."})
        
        pedidos_hoy = supabase.table("pedido").select("*").execute().data
        pedidos_hoy = [p for p in pedidos_hoy if datetime.fromisoformat(p["fecha_pedido"]).date() == hoy]
        
        buffer = generar_pdf_consolidado(informe['id_informe'], pedidos_hoy)
        if not buffer:
            return jsonify({"success": False, "msg": "Error al generar el PDF."})
        
        response = make_response(buffer.read())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=informe_diario_{hoy}.pdf'
        return response
        
    except Exception as e:
        print("Error al descargar informe diario:", e)
        return jsonify({"success": False, "msg": f"Error: {e}"})


def re_generar_reporte_premium(id_l, periodo, fecha_base):
    # Esta funcion replica la logica de generar_reporte_personalizado sin persistir de nuevo
    try:
        f_ini, f_fin = obtener_rango_fecha(periodo, fecha_base)
        local_info = supabase.table("locales").select("nombre").eq("id_local", id_l).execute()
        nombre_local = local_info.data[0]["nombre"] if local_info.data else "Desconocido"
        cons_res = supabase.table("consumo").select("*, consumo_detalle(*, productos(nombre, unidad))")\
            .eq("id_local", id_l).gte("fecha", f_ini).lte("fecha", f_fin).execute()
        consumos = cons_res.data or []
        resumen_productos = {}
        total_ventas_count = 0
        total_merma_items = 0
        for c in consumos:
            is_merma = "[MERMA]" in (c.get("observacion") or "")
            if is_merma: total_merma_items += 1
            else: total_ventas_count += c.get("cantidad_platos", 0)
            for det in c.get("consumo_detalle", []):
                p = det.get("productos")
                if not p: continue
                pid = det["id_producto"]
                if pid not in resumen_productos:
                    resumen_productos[pid] = {"nombre": p["nombre"], "unidad": p["unidad"], "venta": 0, "merma": 0}
                cant = float(det["cantidad_consumida"])
                if is_merma: resumen_productos[pid]["merma"] += cant
                else: resumen_productos[pid]["venta"] += cant
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=70, topMargin=50, bottomMargin=50)
        styles = getSampleStyleSheet()
        style_title = styles['Title']
        style_title.alignment = 0
        style_title.fontName = "Helvetica-Bold"
        style_title.fontSize = 22
        style_title.textColor = colors.HexColor("#111111")
        style_h2 = styles['Heading2']
        style_h2.textColor = colors.HexColor("#E63900")
        style_h2.fontSize = 14
        elements = []
        elements.append(Paragraph(f"INFORME TECNICO DE INVENTARIO", style_title))
        elements.append(Spacer(1, 5))
        elements.append(Table([[""]], colWidths=[480], style=[('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#E63900"))]))
        elements.append(Spacer(1, 15))
        elements.append(Paragraph(f"<b>Sede:</b> {nombre_local.upper()} | <b>Periodo:</b> {periodo.upper()}", styles['Normal']))
        elements.append(Paragraph(f"<b>Rango:</b> {f_ini[:10]} - {f_fin[:10]}", styles['Normal']))
        elements.append(Spacer(1, 25))
        elements.append(Paragraph("1. Resumen Ejecutivo (Metricas Clave)", style_h2))
        elements.append(Spacer(1, 10))
        resumen_data = [["PLANTILLAS VENDIDAS", "MERMA / ERROR", "ESTADO OPERATIVO"], [f"{total_ventas_count}", f"{total_merma_items}", "Auditado (H)"]]
        t_res = Table(resumen_data, colWidths=[160, 160, 160])
        t_res.setStyle(TableStyle([('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'), ('FONTSIZE', (0, 0), (-1, 0), 9), ('TEXTCOLOR', (0, 0), (-1, 0), colors.grey), ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('BOTTOMPADDING', (0, 0), (-1, 0), 10), ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'), ('FONTSIZE', (0, 1), (-1, 1), 16), ('TEXTCOLOR', (0, 1), (0, 1), colors.black), ('TEXTCOLOR', (1, 1), (1, 1), colors.HexColor("#E63900")), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
        elements.append(t_res)
        elements.append(Spacer(1, 30))
        elements.append(Paragraph("2. Consumo Detallado por Insumo", style_h2))
        elements.append(Spacer(1, 12))
        data_prod = [["INSUMO", "UNIDAD", "VENTAS", "MERMA", "TOTAL"]]
        sorted_products = sorted(resumen_productos.values(), key=lambda x: x['nombre'])
        for p in sorted_products:
            total = p['venta'] + p['merma']
            data_prod.append([p['nombre'].upper(), p['unidad'], int(p['venta']), int(p['merma']), int(total)])
        t_prod = Table(data_prod, colWidths=[180, 70, 70, 70, 90])
        t_prod.setStyle(TableStyle([('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'), ('FONTSIZE', (0, 0), (-1, 0), 9), ('TEXTCOLOR', (0, 0), (-1, 0), colors.black), ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor("#E63900")), ('BOTTOMPADDING', (0, 0), (-1, 0), 8), ('FONTSIZE', (0, 1), (-1, -1), 9), ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor("#333333")), ('ALIGN', (2, 0), (-1, -1), 'CENTER'), ('GRID', (0, 1), (-1, -1), 0.25, colors.lightgrey), ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9F9F9")]), ('TOPPADDING', (0, 1), (-1, -1), 6), ('BOTTOMPADDING', (0, 1), (-1, -1), 6)]))
        elements.append(t_prod)
        elements.append(Spacer(1, 40))
        elements.append(Paragraph(f"<i>Re-generado el {datetime.now().strftime('%d/%m/%Y %H:%M')} - Historial Ichiraku</i>", styles['Italic']))
        doc.build(elements, onFirstPage=dibujar_sidebar_premium, onLaterPages=dibujar_sidebar_premium)
        buffer.seek(0)
        response = make_response(buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=Informe_Historial_{fecha_base}.pdf'
        return response
    except Exception as e:
        return jsonify({"success": False, "msg": f"Error re-generando: {str(e)}"}), 500

def re_generar_reporte_rango(tipo, fecha_inicio, fecha_fin):
    try:
        informes = supabase.table("informe").select("*").gte("fecha_creacion", fecha_inicio).lte("fecha_creacion", fecha_fin).order("fecha_creacion", desc=True).execute()
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=40, rightMargin=40, topMargin=80, bottomMargin=50)
        styles = getSampleStyleSheet()
        elements = []
        titulo = f"INFORME {tipo.upper()} CONSOLIDADO (HISTORIAL)"
        elements.append(Paragraph(f"<font size=18 color='#000000'><b>{titulo}</b></font>", styles['Normal']))
        elements.append(Spacer(1, 20))
        elements.append(Paragraph(f"Periodo: {fecha_inicio} al {fecha_fin}", styles['Normal']))
        elements.append(Paragraph(f"Total informes base: {len(informes.data)}", styles['Normal']))
        # Aqui podriamos agregar mas detalle si fuera necesario, similar a descargar_informes_rango
        doc.build(elements)
        buffer.seek(0)
        response = make_response(buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=Informe_Consolidado_H.pdf'
        return response
    except Exception as e:
        return jsonify({"success": False, "msg": f"Error re-generando rango: {str(e)}"}), 500

@app.route('/descargar_informe/<int:id_informe>', methods=['GET'])
@login_requerido(rol='Administrador')
def descargar_informe(id_informe):
    try:
        informe_result = supabase.table("informe").select("*").eq("id_informe", id_informe).execute()
        if not informe_result.data:
            return jsonify({"success": False, "msg": "Informe no encontrado"}), 404
        
        informe = informe_result.data[0]
        tipo = informe.get("tipo", "")
        
        if tipo == "diario_consolidado":
            return descargar_informe_consolidado_individual(id_informe)
        
        if tipo == "inventario_premium":
            # Extraer parametros del metadata (pedidos_ids)
            metadata = informe.get("pedidos_ids")
            if not metadata:
                return jsonify({"success": False, "msg": "Metadata del informe no encontrada"}), 404
            
            # Simulamos un request.form para reutilizar la logica o simplemente llamamos a la logica core
            # Para mayor seguridad, reconstruimos el reporte con los datos guardados
            id_l = metadata.get("id_local")
            periodo = metadata.get("periodo", "diario")
            fecha_base = metadata.get("fecha_base", datetime.now().strftime("%Y-%m-%d"))
            
            # Llamamos a una funcion interna para generar el PDF (debemos extraerla de generar_reporte_personalizado)
            # O simplemente replicamos la logica aqui brevemente
            return re_generar_reporte_premium(id_l, periodo, fecha_base)

        if tipo.startswith("consolidado_"):
            subtipo = tipo.replace("consolidado_", "")
            f_ini = informe.get("fecha_inicio")
            f_fin = informe.get("fecha_fin")
            return re_generar_reporte_rango(subtipo, f_ini, f_fin)

        if not informe.get("id_inf_pedido"):
            return jsonify({"success": False, "msg": "Este informe no tiene un tipo valido asociado"}), 404
        
        pedido_result = supabase.table("pedido").select("*").eq("id_pedido", informe["id_inf_pedido"]).execute()
        if not pedido_result.data:
            return jsonify({"success": False, "msg": "Pedido no encontrado"}), 404
        
        pedido = pedido_result.data[0]
        
        inventario_result = supabase.table("inventario").select("id_local").eq("id_inventario", pedido["id_inventario"]).execute()
        if not inventario_result.data:
            return jsonify({"success": False, "msg": "Inventario no encontrado"}), 404
        
        inventario = inventario_result.data[0]
        
        local_result = supabase.table("locales").select("nombre, direccion").eq("id_local", inventario["id_local"]).execute()
        if not local_result.data:
            return jsonify({"success": False, "msg": "Local no encontrado"}), 404
        
        local = local_result.data[0]
        
        detalles = supabase.table("detalle_pedido").select("id_producto, cantidad").eq("id_pedido", pedido["id_pedido"]).execute().data
        productos = supabase.table("productos").select("id_producto, nombre, unidad, categoria").execute().data
        mapa_productos = {p["id_producto"]: p for p in productos}

        data_productos = []
        categorias_count = {}
        for d in detalles:
            prod = mapa_productos.get(d["id_producto"], {})
            data_productos.append([
                d["id_producto"],
                prod.get("nombre", "Desconocido"),
                d["cantidad"],
                prod.get("unidad", "-")
            ])
            cat = prod.get("categoria", "Sin categoria")
            categorias_count[cat] = categorias_count.get(cat, 0) + d["cantidad"]

        buffer = io.BytesIO()
        # Margen izquierdo amplio para el sidebar
        doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=75, rightMargin=40, topMargin=50, bottomMargin=50)
        styles = getSampleStyleSheet()
        
        # Estilos Diseno C
        style_title = styles['Title']
        style_title.alignment = 0
        style_title.fontSize = 20
        style_title.textColor = colors.HexColor("#111111")
        
        style_h2 = styles['Heading2']
        style_h2.textColor = colors.HexColor("#E63900")
        style_h2.fontSize = 14
        
        elements = []

        # Titulo y acento rojo
        elements.append(Paragraph(f"INFORME DE PEDIDO", style_title))
        elements.append(Spacer(1, 4))
        elements.append(Table([[""]], colWidths=[480], style=[('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#E63900"))]))
        elements.append(Spacer(1, 15))

        try:
            fecha_formateada = datetime.fromisoformat(informe["fecha_creacion"]).strftime("%d/%m/%Y - %I:%M %p")
        except:
            fecha_formateada = informe.get("fecha_creacion", "Sin fecha")

        info_table_data = [
            [Paragraph(f"<b>ID INFORME:</b> #{informe['id_informe']}", styles['Normal']),
             Paragraph(f"<b>FECHA:</b> {fecha_formateada}", styles['Normal'])],
            [Paragraph(f"<b>LOCAL:</b> {local['nombre'].upper()}", styles['Normal']),
             Paragraph(f"<b>REF PEDIDO:</b> #{informe['id_inf_pedido']}", styles['Normal'])]
        ]
        t = Table(info_table_data, colWidths=[240, 240])
        t.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 20))

        if data_productos:
            elements.append(Paragraph("1. Productos del Pedido", style_h2))
            elements.append(Spacer(1, 10))
            
            table_data = [["ID PROD", "NOMBRE", "CANTIDAD", "UNIDAD"]] + data_productos
            dt = Table(table_data, colWidths=[80, 200, 100, 100])
            dt.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("LINEBELOW", (0, 0), (-1, 0), 1.5, colors.HexColor("#E63900")),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("GRID", (0, 1), (-1, -1), 0.1, colors.grey),
                ("ALIGN", (2, 0), (-1, -1), "CENTER"),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9F9F9")]),
            ]))
            elements.append(dt)
            elements.append(Spacer(1, 25))

        if categorias_count:
            elements.append(Paragraph("2. Distribucion por Categoria", style_h2))
            elements.append(Spacer(1, 10))
            drawing = Drawing(300, 200)
            pie = Pie()
            pie.x = 65
            pie.y = 15
            pie.width = 170
            pie.height = 170
            pie.data = list(categorias_count.values())
            pie.labels = list(categorias_count.keys())
            pie.slices.strokeWidth = 0.5
            drawing.add(pie)
            elements.append(drawing)

        # Footer
        elements.append(Spacer(1, 30))
        elements.append(Paragraph(f"<i>Informe de Pedido Ichiraku Ramen - Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}</i>", styles['Italic']))

        # Build con Sidebar
        doc.build(elements, onFirstPage=dibujar_sidebar_premium, onLaterPages=dibujar_sidebar_premium)
        buffer.seek(0)
        response = make_response(buffer.read())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=informe_{id_informe}.pdf'
        return response
        
    except Exception as e:
        print(f"Error al generar PDF para informe {id_informe}: {e}")
        return jsonify({"success": False, "msg": f"Error al generar informe PDF: {e}"})

@app.route('/descargar_informes_rango', methods=['POST'])
@login_requerido(rol='Administrador')
def descargar_informes_rango():
    try:
        data = request.get_json()
        tipo = data.get("tipo")
        fecha_inicio = data.get("fecha_inicio")
        fecha_fin = data.get("fecha_fin")
        
        if not tipo:
            return jsonify({"success": False, "msg": "Tipo de informe no especificado."})
        
        if not fecha_inicio or not fecha_fin:
            return jsonify({"success": False, "msg": "Fechas de rango no especificadas."})

        informes = supabase.table("informe") \
            .select("*") \
            .gte("fecha_creacion", fecha_inicio) \
            .lte("fecha_creacion", fecha_fin) \
            .order("fecha_creacion", desc=True) \
            .execute()

        if not informes.data:
            return jsonify({"success": False, "msg": "No se encontraron informes en el rango especificado."})

        # Persistencia en la base de datos para el historial
        try:
            nuevo_rango = {
                "fecha_creacion": datetime.now().isoformat(),
                "tipo": f"consolidado_{tipo}",
                "fecha_inicio": fecha_inicio[:10],
                "fecha_fin": fecha_fin[:10],
                "total_pedidos": len(informes.data),
                "pedidos_ids": {"subtipo": tipo}
            }
            supabase.table("informe").insert(nuevo_rango).execute()
        except Exception as db_e:
            print(f"Error al persistir informe de rango: {db_e}")

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=letter,
            leftMargin=40, 
            rightMargin=40, 
            topMargin=80,
            bottomMargin=50
        )
        styles = getSampleStyleSheet()
        elements = []

        # ========================
        # ENCABEZADO CON LOGO Y MARCA
        # ========================
        try:
            logo_path = os.path.join(app.root_path, "static", "image", "logo.png")
            if not os.path.exists(logo_path):
                logo_path = os.path.abspath(os.path.join("static", "image", "logo.png"))
            logo = Image(logo_path, width=80, height=60)
            logo_table = Table([[logo]], colWidths=[80])
            logo_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
        except:
            logo_table = Table([[
                Paragraph("<font size=16 color='#FF0000'><b>ICHIRAKU</b></font><br/><font size=8 color='#000000'>RAMEN</font>", styles['Normal'])
            ]], colWidths=[120])
            logo_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOX', (0, 0), (-1, -1), 1, colors.black),
                ('PADDING', (0, 0), (-1, -1), 10),
            ]))

        # Definir titulo segun el tipo
        if tipo == "semana":
            titulo = "INFORME SEMANAL CONSOLIDADO"
        elif tipo == "mes":
            titulo = "INFORME MENSUAL CONSOLIDADO"
        elif tipo == "anio":
            titulo = "INFORME ANUAL CONSOLIDADO"
        else:
            titulo = "INFORME CONSOLIDADO"

        header_data = [
            [logo_table, Paragraph(f"<font size=18 color='#000000'><b>{titulo}</b></font>", styles['Normal'])]
        ]
        
        header_table = Table(header_data, colWidths=[140, 360])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'CENTER'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 20),
        ]))
        elements.append(header_table)
        
        # Informacion del periodo
        fecha_inicio_obj = datetime.fromisoformat(fecha_inicio.replace('T', ' '))
        fecha_fin_obj = datetime.fromisoformat(fecha_fin.replace('T', ' '))
        
        periodo_header = Table([
            [Paragraph(f"<font size=11 color='#000000'><b>PERIODO:</b> {fecha_inicio_obj.strftime('%d/%m/%Y')} - {fecha_fin_obj.strftime('%d/%m/%Y')}</font>", styles['Normal']),
             Paragraph(f"<font size=11 color='#000000'><b>TOTAL INFORMES:</b> {len(informes.data)}</font>", styles['Normal'])]
        ], colWidths=[250, 250])
        
        periodo_header.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
        ]))
        elements.append(periodo_header)
        
        # Linea divisoria en rojo
        elements.append(Spacer(1, 10))
        line_table = Table([[""]], colWidths=[500])
        line_table.setStyle(TableStyle([
            ('LINEABOVE', (0, 0), (-1, 0), 3, colors.HexColor("#FF0000")),
        ]))
        elements.append(line_table)
        elements.append(Spacer(1, 25))

        # ========================
        # PROCESAR DATOS
        # ========================
        total_pedidos = 0
        total_productos = 0
        categorias_totales = {}
        locales_participantes = set()
        todos_productos_detallados = []
        fechas_pedidos = set()

        for inf in informes.data:
            try:
                if inf.get("tipo") == "diario_consolidado":
                    fecha_inf = datetime.fromisoformat(inf["fecha_creacion"]).date()
                    fechas_pedidos.add(fecha_inf)
                    
                    pedidos_dia = supabase.table("pedido").select("*").execute().data
                    pedidos_dia = [p for p in pedidos_dia if datetime.fromisoformat(p["fecha_pedido"]).date() == fecha_inf]
                    
                    total_pedidos += len(pedidos_dia)
                    
                    for pedido in pedidos_dia:
                        detalles = supabase.table("detalle_pedido").select("id_producto, cantidad")\
                            .eq("id_pedido", pedido["id_pedido"]).execute().data or []
                        
                        inventario_result = supabase.table("inventario").select("id_local")\
                            .eq("id_inventario", pedido["id_inventario"]).execute()
                        
                        local_nombre = "No especificado"
                        if inventario_result.data:
                            local_id = inventario_result.data[0].get("id_local")
                            if local_id:
                                local_result = supabase.table("locales").select("nombre")\
                                    .eq("id_local", local_id).execute()
                                if local_result.data:
                                    local_nombre = local_result.data[0].get('nombre', 'No especificado')
                                    locales_participantes.add(local_nombre)
                        
                        for detalle in detalles:
                            if not isinstance(detalle, dict):
                                continue
                                
                            cantidad_detalle = detalle.get('cantidad', 0)
                            id_producto = detalle.get('id_producto')
                            
                            if not id_producto:
                                continue

                            total_productos += int(cantidad_detalle)
                            
                            producto_result = supabase.table("productos").select("nombre, categoria, unidad")\
                                .eq("id_producto", id_producto).execute()
                            
                            if producto_result.data:
                                producto = producto_result.data[0]
                                cat = producto.get('categoria', 'Sin categoria')
                                categorias_totales[cat] = categorias_totales.get(cat, 0) + cantidad_detalle
                                
                                todos_productos_detallados.append({
                                    'fecha': fecha_inf.strftime("%d/%m/%Y"),
                                    'informe_id': inf['id_informe'],
                                    'pedido_id': pedido['id_pedido'],
                                    'local': local_nombre,
                                    'producto': producto.get('nombre', 'Desconocido'),
                                    'categoria': cat,
                                    'cantidad': cantidad_detalle,
                                    'unidad': producto.get('unidad', 'und'),
                                    'hora': datetime.fromisoformat(pedido["fecha_pedido"]).strftime("%H:%M")
                                })
                
                elif inf.get("id_inf_pedido"):
                    total_pedidos += 1
                    fecha_inf = datetime.fromisoformat(inf["fecha_creacion"]).date()
                    fechas_pedidos.add(fecha_inf)
                    
                    pedido_result = supabase.table("pedido").select("*").eq("id_pedido", inf["id_inf_pedido"]).execute()
                    if pedido_result.data:
                        pedido = pedido_result.data[0]
                        
                        detalles = supabase.table("detalle_pedido").select("id_producto, cantidad")\
                            .eq("id_pedido", pedido["id_pedido"]).execute().data or []
                        
                        inventario_result = supabase.table("inventario").select("id_local")\
                            .eq("id_inventario", pedido["id_inventario"]).execute()
                        
                        local_nombre = "No especificado"
                        if inventario_result.data:
                            local_id = inventario_result.data[0].get("id_local")
                            if local_id:
                                local_result = supabase.table("locales").select("nombre")\
                                    .eq("id_local", local_id).execute()
                                if local_result.data:
                                    local_nombre = local_result.data[0].get('nombre', 'No especificado')
                                    locales_participantes.add(local_nombre)
                        
                        for detalle in detalles:
                            if not isinstance(detalle, dict):
                                continue
                                
                            cantidad_detalle = detalle.get('cantidad', 0)
                            id_producto = detalle.get('id_producto')
                            
                            if not id_producto:
                                continue

                            total_productos += cantidad_detalle
                            
                            producto_result = supabase.table("productos").select("nombre, categoria, unidad")\
                                .eq("id_producto", id_producto).execute()
                            
                            if producto_result.data:
                                producto = producto_result.data[0]
                                cat = producto.get('categoria', 'Sin categoria')
                                categorias_totales[cat] = categorias_totales.get(cat, 0) + cantidad_detalle
                                
                                todos_productos_detallados.append({
                                    'fecha': fecha_inf.strftime("%d/%m/%Y"),
                                    'informe_id': inf['id_informe'],
                                    'pedido_id': pedido['id_pedido'],
                                    'local': local_nombre,
                                    'producto': producto.get('nombre', 'Desconocido'),
                                    'categoria': cat,
                                    'cantidad': cantidad_detalle,
                                    'unidad': producto.get('unidad', 'und'),
                                    'hora': datetime.fromisoformat(pedido["fecha_pedido"]).strftime("%H:%M")
                                })
                                
            except Exception as e:
                print(f"Error procesando informe {inf.get('id_informe')}: {e}")
                continue

        # ========================
        # RESUMEN EJECUTIVO
        # ========================
        elements.append(Paragraph(
            "<font size=14 color='#000000'><b>RESUMEN EJECUTIVO</b></font>", 
            styles['Heading2']
        ))
        elements.append(Spacer(1, 15))

        resumen_data = [
            ["PERIODO ANALIZADO", f"{fecha_inicio_obj.strftime('%d/%m/%Y')} - {fecha_fin_obj.strftime('%d/%m/%Y')}"],
            ["TOTAL DE PEDIDOS", f"{total_pedidos}"],
            ["TOTAL DE PRODUCTOS", f"{total_productos}"],
            ["TOTAL DE INFORMES", f"{len(informes.data)}"],
            ["DIAS CON ACTIVIDAD", f"{len(fechas_pedidos)}"],
            ["LOCALES ACTIVOS", f"{len(locales_participantes)}"],
        ]
        
        resumen_table = Table(resumen_data, colWidths=[300, 200])
        resumen_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f8f8f8")),
            ("BACKGROUND", (1, 0), (1, -1), colors.white),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 11),
            ("ALIGN", (0, 0), (0, -1), "LEFT"),
            ("ALIGN", (1, 0), (1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ]))
        elements.append(resumen_table)
        
        # Locales participantes
        if locales_participantes:
            elements.append(Spacer(1, 10))
            locales_text = ", ".join(sorted(locales_participantes))
            elements.append(Paragraph(
                f"<font size=10 color='#000000'><b>Locales participantes:</b> {locales_text}</font>",
                styles['Normal']
            ))

        elements.append(Spacer(1, 30))

        # ========================
        # DISTRIBUCION POR CATEGORIAS
        # ========================
        if categorias_totales:
            elements.append(Paragraph(
                "<font size=14 color='#000000'><b>DISTRIBUCION POR CATEGORIAS</b></font>", 
                styles['Heading2']
            ))
            elements.append(Spacer(1, 12))
            
            categorias_data = [["CATEGORIA", "CANTIDAD", "PORCENTAJE"]]
            total_categorias = sum(categorias_totales.values())
            
            for categoria, cantidad in sorted(categorias_totales.items(), key=lambda x: x[1], reverse=True):
                porcentaje = (cantidad / total_categorias) * 100 if total_categorias > 0 else 0
                categorias_data.append([
                    categoria,
                    f"{cantidad} unid",
                    f"{porcentaje:.1f}%"
                ])
            
            categorias_table = Table(categorias_data, colWidths=[300, 100, 100])
            categorias_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.black),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                
                ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                ("TEXTCOLOR", (0, 1), (-1, -1), colors.black),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
                ("ALIGN", (0, 1), (0, -1), "LEFT"),
                ("ALIGN", (1, 1), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            elements.append(categorias_table)
            elements.append(Spacer(1, 30))

        # ========================
        # DETALLE POR DIA
        # ========================
        if todos_productos_detallados:
            elements.append(Paragraph(
                "<font size=14 color='#000000'><b>DETALLE POR DIA</b></font>", 
                styles['Heading2']
            ))
            elements.append(Spacer(1, 15))

            # Agrupar por fecha
            productos_por_fecha = {}
            for prod in todos_productos_detallados:
                fecha = prod['fecha']
                if fecha not in productos_por_fecha:
                    productos_por_fecha[fecha] = []
                productos_por_fecha[fecha].append(prod)
            
            # Procesar cada fecha
            for fecha in sorted(productos_por_fecha.keys(), reverse=True):
                # Header de fecha
                elements.append(Paragraph(
                    f"<font size=11 color='#FF0000'><b>{fecha}</b></font>",
                    styles['Normal']
                ))
                elements.append(Spacer(1, 8))
                
                # Agrupar por pedido en esta fecha
                pedidos_fecha = {}
                for prod in productos_por_fecha[fecha]:
                    pedido_id = prod['pedido_id']
                    if pedido_id not in pedidos_fecha:
                        pedidos_fecha[pedido_id] = {
                            'local': prod['local'],
                            'hora': prod['hora'],
                            'productos': [],
                            'total_unidades': 0
                        }
                    pedidos_fecha[pedido_id]['productos'].append(prod)
                    pedidos_fecha[pedido_id]['total_unidades'] += prod['cantidad']
                
                # Procesar cada pedido de esta fecha
                for pedido_id, info in pedidos_fecha.items():
                    # Header del pedido
                    header_text = f"PEDIDO #{pedido_id} | {info['local']} | {info['hora']} | {info['total_unidades']} UNIDADES"
                    elements.append(Paragraph(
                        f"<font size=10 color='#000000'><b>{header_text}</b></font>",
                        styles['Normal']
                    ))
                    elements.append(Spacer(1, 5))
                    
                    # Tabla de productos del pedido
                    table_data = [["PRODUCTO", "CATEGORIA", "CANTIDAD"]]
                    for prod in info['productos']:
                        table_data.append([
                            prod['producto'],
                            prod['categoria'],
                            f"{prod['cantidad']} {prod['unidad']}"
                        ])
                    
                    if len(table_data) > 1:
                        pedido_table = Table(table_data, colWidths=[250, 140, 110])
                        pedido_table.setStyle(TableStyle([
                            ("BACKGROUND", (0, 0), (-1, 0), colors.black),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("FONTSIZE", (0, 0), (-1, 0), 9),
                            ("ALIGN", (0, 0), (-1, 0), "LEFT"),
                            
                            ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                            ("TEXTCOLOR", (0, 1), (-1, -1), colors.black),
                            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                            ("FONTSIZE", (0, 1), (-1, -1), 8),
                            ("ALIGN", (0, 1), (1, -1), "LEFT"),
                            ("ALIGN", (2, 1), (2, -1), "CENTER"),
                            ("GRID", (0, 0), (-1, -1), 1, colors.black),
                            ("LEFTPADDING", (0, 0), (-1, -1), 6),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                            ("TOPPADDING", (0, 0), (-1, -1), 4),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                        ]))
                        elements.append(pedido_table)
                        elements.append(Spacer(1, 15))
                
                elements.append(Spacer(1, 20))

        # ========================
        # PIE DE PAGINA
        # ========================
        elements.append(Spacer(1, 30))
        
        # Linea divisoria roja
        footer_line = Table([[""]], colWidths=[500])
        footer_line.setStyle(TableStyle([
            ('LINEABOVE', (0, 0), (-1, 0), 2, colors.HexColor("#FF0000")),
        ]))
        elements.append(footer_line)
        elements.append(Spacer(1, 15))
        
        # Informacion del pie de pagina
        footer_text = f"""
        <para alignment='center'>
        <font size=9 color='#000000'>
        <b>ICHIRAKU RAMEN - SISTEMA DE GESTION</b><br/>
        {titulo} generado automaticamente el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}<br/>
        Periodo: {fecha_inicio_obj.strftime('%d/%m/%Y')} - {fecha_fin_obj.strftime('%d/%m/%Y')}<br/>
        <i>Documento confidencial - Uso interno exclusivo</i>
        </font>
        </para>
        """
        elements.append(Paragraph(footer_text, styles['Normal']))

        # Construir PDF
        doc.build(elements)
        buffer.seek(0)

        response = make_response(buffer.read())
        response.headers["Content-Type"] = "application/pdf"
        response.headers["Content-Disposition"] = f"attachment; filename=informe_{tipo}_{datetime.now().strftime('%Y%m%d')}.pdf"
        return response
        
    except Exception as e:
        print(f"Error al generar informe: {e}")
        return jsonify({"success": False, "msg": str(e)})




# ==============================================================================
# 7. OPERACIONES DE EMPLEADOS
# ==============================================================================


# ==============================================================================
# 7. OPERACIONES DE EMPLEADOS
# ==============================================================================

@app.route('/registrar_consumo', methods=['POST'])
@login_requerido(rol='Empleado')
def registrar_consumo():
    try:
        data = request.get_json()
        id_producto = data.get('id_producto')
        cantidad = data.get('cantidad')
        
        if not (id_producto and cantidad):
            return jsonify({"success": False, "msg": "Datos incompletos."}), 400
            
        try:
            cantidad_val = float(cantidad)
            if cantidad_val <= 0:
                raise ValueError
        except:
            return jsonify({"success": False, "msg": "Cantidad invalida."}), 400

        id_sucursal = session.get('branch')
        if not id_sucursal:
            return jsonify({"success": False, "msg": "Error de sesion: Sucursal no definida."}), 403

        producto_info = supabase.table("productos").select("nombre, unidad").eq("id_producto", id_producto).execute()
        nombre_producto = producto_info.data[0].get("nombre", "Desconocido") if producto_info.data else "Desconocido"

        # Filtrar solo lotes con stock disponible
        inventario = supabase.table("inventario").select("*")\
            .eq("id_producto", id_producto)\
            .eq("id_local", id_sucursal)\
            .gt("cantidad", 0)\
            .order("fecha_caducidad")\
            .execute()
        
        if not inventario.data:
            return jsonify({"success": False, "msg": "No hay stock disponible."}), 400
        
        # Validacion atomica antes de hacer descuentos
        disponible_total = sum(float(l['cantidad']) for l in inventario.data)
        if disponible_total < float(cantidad_val):
             return jsonify({"success": False, "msg": f"Stock insuficiente. Solo hay {to_num(disponible_total)} {producto_info.data[0].get('unidad', '')}."}), 400

        restante = float(cantidad_val)
        detalles_afectados = []
        
        for lote in inventario.data:
            cant_lote = float(lote['cantidad'])
            id_inv = lote['id_inventario']
            
            if cant_lote >= restante:
                detalles_afectados.append({
                    "id_producto": int(id_producto),
                    "id_inventario": id_inv,
                    "cantidad_consumida": to_num(restante),
                    "fecha": datetime.now().isoformat()
                })
                restante = 0
                break
            else:
                detalles_afectados.append({
                    "id_producto": int(id_producto),
                    "id_inventario": id_inv,
                    "cantidad_consumida": to_num(cant_lote),
                    "fecha": datetime.now().isoformat()
                })
                restante -= cant_lote

        # Historial
        try:
            cons_res = supabase.table("consumo").insert({
                "fecha": datetime.now().isoformat(),
                "cantidad_platos": 1,
                "observacion": f"Consumo manual: {nombre_producto} (Cant: {cantidad_val})"
            }).execute()
            
            if cons_res.data:
                id_c = cons_res.data[0]["id_consumo"]
                for det in detalles_afectados:
                    det["id_consumo"] = id_c
                    supabase.table("consumo_detalle").insert(det).execute()
        except: pass

        # Generar alertas inmediatas (optimizado por local)
        generar_notificaciones_stock_bajo(session.get('branch'))

        return jsonify({"success": True, "msg": "Consumo registrado correctamente."})
    except Exception as e:
        return jsonify({"success": False, "msg": str(e)})

@app.route('/registrar_merma', methods=['POST'])
@login_requerido(rol='Empleado')
def registrar_merma():
    try:
        data = request.get_json()
        id_producto = data.get('id_producto')
        cantidad_val = data.get('cantidad')
        motivo = data.get('motivo', 'No especificado')
        id_l = session.get('branch')

        if not id_producto or not cantidad_val:
            return jsonify({"success": False, "msg": "Datos incompletos."}), 400

        # Obtener info basica del producto
        producto_info = supabase.table("productos").select("nombre, unidad").eq("id_producto", id_producto).execute()
        if not producto_info.data:
            return jsonify({"success": False, "msg": "Producto no encontrado."}), 404
        
        nombre_producto = producto_info.data[0]['nombre']

        # Validar stock (FIFO)
        inventario = supabase.table("inventario").select("*").eq("id_producto", id_producto).eq("id_local", id_l).gt("cantidad", 0).order("fecha_caducidad").execute()
        
        if not inventario.data:
             return jsonify({"success": False, "msg": f"Stock insuficiente para '{nombre_producto}'. No hay existencias."}), 400

        disponible_total = sum(float(l['cantidad']) for l in inventario.data)
        if disponible_total < float(cantidad_val):
             return jsonify({"success": False, "msg": f"Stock insuficiente. Solo hay {to_num(disponible_total)} {producto_info.data[0].get('unidad', '')}."}), 400

        restante = float(cantidad_val)
        detalles_afectados = []
        
        for lote in inventario.data:
            cant_lote = float(lote['cantidad'])
            id_inv = lote['id_inventario']
            
            if cant_lote >= restante:
                detalles_afectados.append({
                    "id_producto": int(id_producto),
                    "id_inventario": id_inv,
                    "cantidad_consumida": to_num(restante),
                    "fecha": datetime.now().isoformat()
                })
                restante = 0
                break
            else:
                detalles_afectados.append({
                    "id_producto": int(id_producto),
                    "id_inventario": id_inv,
                    "cantidad_consumida": to_num(cant_lote),
                    "fecha": datetime.now().isoformat()
                })
                restante -= cant_lote

        # Registrar historial bajo categoria MERMA
        try:
            cons_res = supabase.table("consumo").insert({
                "fecha": datetime.now().isoformat(),
                "cantidad_platos": 0, # No es un plato vendido
                "id_local": id_l,
                "observacion": f"[MERMA] {motivo} | Prod: {nombre_producto} (Cant: {cantidad_val})"
            }).execute()
            
            if cons_res.data:
                id_c = cons_res.data[0]["id_consumo"]
                for det in detalles_afectados:
                    det["id_consumo"] = id_c
                    # La insercion activa el Trigger de DB para descontar
                    supabase.table("consumo_detalle").insert(det).execute()
        except Exception as e:
            print("Error en insert merma:", e)
            return jsonify({"success": False, "msg": "Error al registrar merma en base de datos."}), 500

        # Generar alertas inmediatas
        generar_notificaciones_stock_bajo(id_l)

        return jsonify({"success": True, "msg": "Merma registrada correctamente."})
    except Exception as e:
        print("Error en /registrar_merma:", e)
        return jsonify({"success": False, "msg": str(e)})

@app.route('/get_recetas_empleado', methods=['POST'])
@login_requerido(rol='Empleado')
def get_recetas_empleado():
    try:
        data = request.get_json() or {}
        termino = data.get("termino", "").strip()
        query = supabase.table("recetarios").select("*").eq("habilitado", True)
        if termino:
            query = query.ilike("nombre", f"%{termino}%")
        res = query.order("nombre").execute()
        return jsonify({"success": True, "recetas": res.data or []})
    except Exception as e:
        return jsonify({"success": False, "msg": str(e)})

@app.route('/registrar_consumo_receta', methods=['POST'])
@login_requerido(rol='Empleado')
def registrar_consumo_receta():
    try:
        data = request.get_json()
        id_r = data.get('id_receta')
        cant_p = int(data.get('cantidad', 1))
        id_l = session.get('branch')
        
        receta = supabase.table("recetarios").select("nombre").eq("id_receta", id_r).execute()
        if not receta.data:
            return jsonify({"success": False, "msg": "Receta no existe"}), 404
            
        detalles = supabase.table("receta_detalle").select("*, productos(nombre, unidad)").eq("id_receta", id_r).execute()
        if not detalles.data:
            return jsonify({"success": False, "msg": "La receta no tiene ingredientes."}), 400

        # FASE 0: Agregar ingredientes por ID de producto (evita doble descuento si hay duplicados en la receta)
        ingredientes_agregados = {}
        for ing in detalles.data:
            pid = ing["id_producto"]
            cant_ing = float(ing["cantidad"])
            if pid not in ingredientes_agregados:
                ingredientes_agregados[pid] = {
                    "id_producto": pid,
                    "cantidad": 0,
                    "productos": ing.get("productos")
                }
            ingredientes_agregados[pid]["cantidad"] += cant_ing

        # FASE 1: Validar stock de todos los ingredientes
        inventario_necesario = []
        for ing in ingredientes_agregados.values():
            p_name = ing['productos']['nombre'] if ing.get('productos') else ing['id_producto']
            p_unit = ing['productos']['unidad'] if ing.get('productos') else ""
            requerido = round(float(ing["cantidad"]) * cant_p, 4)
            
            lotes = supabase.table("inventario").select("*").eq("id_producto", ing["id_producto"]).eq("id_local", id_l).gt("cantidad", 0).order("fecha_caducidad").execute()
            
            if not lotes.data:
                return jsonify({"success": False, "msg": f"Stock insuficiente para '{p_name}'. Sin stock (Requerido: {to_num(requerido)} {p_unit})"}), 400
                
            disponible = round(sum(float(l['cantidad']) for l in lotes.data), 4)
            if disponible < requerido:
                return jsonify({"success": False, "msg": f"Stock insuficiente para '{p_name}'. Solo hay {to_num(disponible)} {p_unit} (Requerido: {to_num(requerido)} {p_unit})"}), 400
                
            inventario_necesario.append({
                "id_producto": ing["id_producto"],
                "requerido": requerido,
                "lotes": lotes.data
            })

        # FASE 2: Descontar stock (sin transacciones, pero con validacion previa exitosa)
        afectados_total = []
        for item in inventario_necesario:
            restante = float(item["requerido"])
            for lote in item["lotes"]:
                if restante <= 0: break
                id_inv = lote['id_inventario']
                cant_lote = float(lote['cantidad'])
                
                if cant_lote >= restante:
                    afectados_total.append({"id_prod": item["id_producto"], "id_inv": id_inv, "cant": to_num(restante)})
                    restante = 0
                else:
                    afectados_total.append({"id_prod": item["id_producto"], "id_inv": id_inv, "cant": to_num(cant_lote)})
                    restante -= cant_lote

        # Registrar consumo e historial
        c_res = supabase.table("consumo").insert({
            "fecha": datetime.now().isoformat(),
            "cantidad_platos": cant_p,
            "id_receta": id_r,
            "id_local": id_l,
            "observacion": f"Venta: {cant_p} platos de {receta.data[0]['nombre']}"
        }).execute()
        
        if c_res.data:
            idc = c_res.data[0]["id_consumo"]
            for a in afectados_total:
                supabase.table("consumo_detalle").insert({
                    "id_consumo": idc,
                    "id_producto": a["id_prod"],
                    "id_inventario": a["id_inv"],
                    "cantidad_consumida": a["cant"],
                    "fecha": datetime.now().isoformat()
                }).execute()
                
        # Generar alertas inmediatas (optimizado por local)
        generar_notificaciones_stock_bajo(id_l)
        
        return jsonify({"success": True, "msg": "Venta registrada exitosamente!"})
    except Exception as e:
        print("Error en registrar_consumo_receta:", e)
        return jsonify({"success": False, "msg": "Verifique que todos los productos esten en el inventario. Error: "+str(e)}), 400


@app.route('/historial_consumo_hoy', methods=['GET'])
@login_requerido(rol='Empleado')
def historial_consumo_hoy():
    try:
        id_sucursal = session.get('branch')
        if not id_sucursal:
            return jsonify({"success": False, "msg": "Sucursal no definida."}), 403

        hoy = datetime.now().strftime("%Y-%m-%d")

        # Query joins: consumo_detalle -> consumo and consumo_detalle -> productos
        # the Supabase python client supports joining via select strings
        consumos = supabase.table("consumo_detalle") \
            .select("*, productos(nombre, unidad), consumo(*), inventario(id_local)") \
            .gte("fecha", f"{hoy}T00:00:00") \
            .lte("fecha", f"{hoy}T23:59:59") \
            .execute()

        registros = []
        if consumos.data:
            for item in consumos.data:
                # Filtrar por sucursal si el inventario esta disponible
                if item.get("inventario") and item["inventario"].get("id_local") == id_sucursal:
                    registros.append({
                        "id_producto": item["id_producto"],
                        "nombre_producto": item["productos"]["nombre"] if item.get("productos") else "Desconocido",
                        "cantidad": item["cantidad_consumida"],
                        "unidad": item["productos"]["unidad"] if item.get("productos") else "",
                        "fecha": item["fecha"]
                    })

        return jsonify({"success": True, "consumos": registros})

    except Exception as e:
        print("Error en historial_consumo_hoy:", e)
        import traceback
        return jsonify({"success": False, "msg": f"Error al obtener historial: {str(e)}\n{traceback.format_exc()}"}), 500

@app.route('/get_receta_breakdown', methods=['POST'])
@login_requerido(rol='Empleado')
def get_receta_breakdown():
    try:
        data = request.get_json()
        id_receta = data.get('id_receta')
        
        if not id_receta:
            return jsonify({"success": False, "msg": "ID de receta no proporcionado."}), 400
            
        detalles = supabase.table("receta_detalle") \
            .select("*, productos(nombre, unidad)") \
            .eq("id_receta", id_receta) \
            .execute()
            
        if not detalles.data:
            return jsonify({"success": True, "breakdown": []})
            
        breakdown = []
        for d in detalles.data:
            breakdown.append({
                "nombre": d['productos']['nombre'] if d.get('productos') else "Desconocido",
                "cantidad": d['cantidad'],
                "unidad": d['productos']['unidad'] if d.get('productos') else ""
            })
            
        return jsonify({"success": True, "breakdown": breakdown})
    except Exception as e:
        return jsonify({"success": False, "msg": str(e)}), 500

@app.route('/get_consumo_comparative', methods=['GET'])
@login_requerido(rol='Empleado')
def get_consumo_comparative():
    try:
        id_local = session.get('branch')
        if not id_local:
            return jsonify({"success": False, "msg": "Sucursal no definida."}), 403

        hoy = datetime.now().strftime("%Y-%m-%d")
        
        # 1. Obtener consumos de hoy para el local
        consumos_hoy = supabase.table("consumo_detalle") \
            .select("id_producto, cantidad_consumida, productos(nombre, unidad), inventario(id_local)") \
            .gte("fecha", f"{hoy}T00:00:00") \
            .lte("fecha", f"{hoy}T23:59:59") \
            .execute()

        agregado_consumo = {}
        if consumos_hoy.data:
            for c in consumos_hoy.data:
                # Filtrar por local
                if c.get('inventario') and c['inventario'].get('id_local') == id_local:
                    pid = c['id_producto']
                    if pid not in agregado_consumo:
                        agregado_consumo[pid] = {
                            "nombre": c['productos']['nombre'],
                            "unidad": c['productos']['unidad'],
                            "total_consumido": 0
                        }
                    agregado_consumo[pid]["total_consumido"] += c['cantidad_consumida']

        # 2. Obtener stock actual para el local
        inventario = supabase.table("inventario") \
            .select("id_producto, cantidad") \
            .eq("id_local", id_local) \
            .execute()
            
        stock_actual = {}
        if inventario.data:
            for inv in inventario.data:
                pid = inv['id_producto']
                stock_actual[pid] = stock_actual.get(pid, 0) + inv['cantidad']

        # 3. Combinar datos
        comparativa = []
        # Asegurar incluir productos que tengan stock pero no consumo hoy, o viceversa
        todos_pids = set(agregado_consumo.keys()) | set(stock_actual.keys())
        
        # Necesitamos nombres para los que solo tienen stock
        if stock_actual:
            productos_info = supabase.table("productos").select("id_producto, nombre, unidad").in_("id_producto", list(todos_pids)).execute()
            p_map = {p['id_producto']: p for p in productos_info.data}
        else:
            p_map = {}

        for pid in todos_pids:
            consumo_data = agregado_consumo.get(pid, {})
            nombre = consumo_data.get("nombre") or (p_map.get(pid, {}).get("nombre", "Desconocido"))
            unidad = consumo_data.get("unidad") or (p_map.get(pid, {}).get("unidad", ""))
            
            comparativa.append({
                "id_producto": pid,
                "nombre": nombre,
                "unidad": unidad,
                "consumido": agregado_consumo.get(pid, {}).get("total_consumido", 0),
                "stock": max(0, stock_actual.get(pid, 0))
            })

        return jsonify({"success": True, "comparativa": comparativa})
    except Exception as e:
        print("Error en get_consumo_comparative:", e)
        import traceback
        return jsonify({"success": False, "msg": f"Error: {str(e)}\n{traceback.format_exc()}"}), 500


@app.route('/stock_producto_sucursal', methods=['POST'])
@login_requerido(rol='Empleado')
def stock_producto_sucursal():
    """Retorna el stock disponible de un producto en la sucursal del empleado."""
    try:
        data = request.get_json()
        id_producto = data.get('id_producto')
        id_sucursal = session.get('branch')

        if not (id_producto and id_sucursal):
            return jsonify({"success": False, "stock": 0})

        inv = supabase.table("inventario") \
            .select("cantidad") \
            .eq("id_producto", id_producto) \
            .eq("id_local", id_sucursal) \
            .execute()

        total = sum(lote.get("cantidad", 0) for lote in (inv.data or []))
        return jsonify({"success": True, "stock": total})

    except Exception as e:
        print("Error en stock_producto_sucursal:", e)
        return jsonify({"success": False, "stock": 0})

@app.route('/Em_Inicio', methods=['GET', 'POST'])
@login_requerido(rol='Empleado')
def Em_Inicio():
    try:
        generar_notificaciones_caducidad()
        generar_notificaciones_stock_bajo()
        eliminar_notificaciones_caducadas()
        
        try:
            todas_response = supabase.table("notificaciones").select("*").order("fecha", desc=True).execute()
            todas = todas_response.data if todas_response.data else []
        except Exception as db_error:
            print(f"Error al consultar notificaciones: {db_error}")
            todas = []

        todas_filtradas = []
        for n in todas:
            mensaje = n.get("mensaje", "")
            if mensaje is not None and str(mensaje).strip() != "":
                todas_filtradas.append(n)

        if not todas_filtradas:
            notificacion_prueba = {
                "mensaje": "BIENVENIDO/AL SISTEMA - Notificaciones apareceran aqui",
                "fecha_formateada": datetime.now().strftime("%d de %B de %Y, %I:%M %p"),
                "leido": False
            }
            todas_filtradas.append(notificacion_prueba)

        try:
            locale.setlocale(locale.LC_TIME, "es_ES.utf8")
        except:
            try:
                locale.setlocale(locale.LC_TIME, "es_CO.utf8")
            except:
                pass

        for noti in todas_filtradas:
            if noti.get("fecha") and not noti.get("fecha_formateada"):
                try:
                    fecha_str = noti["fecha"]
                    if 'T' in fecha_str:
                        fecha_obj = datetime.fromisoformat(fecha_str.replace('Z', '+00:00'))
                    else:
                        fecha_obj = datetime.strptime(fecha_str, "%Y-%m-%d %H:%M:%S")
                    
                    noti["fecha_formateada"] = fecha_obj.strftime("%d de %B de %Y, %I:%M %p").capitalize()
                except Exception as date_error:
                    print(f"Error al formatear fecha {noti['fecha']}: {date_error}")
                    noti["fecha_formateada"] = noti["fecha"]

        notificaciones = todas_filtradas[:3]
        total_notificaciones = len(todas_filtradas)
        restantes = max(0, total_notificaciones - 3)

        http_response = make_response(render_template(
            "Em_templates/Em_Inicio.html",
            notificaciones=notificaciones,
            restantes=restantes,
            total_notificaciones=total_notificaciones
        ))
        http_response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        http_response.headers['Pragma'] = 'no-cache'
        http_response.headers['Expires'] = '-1'
        return http_response
        
    except Exception as e:
        print(f"Error critico al cargar pagina de inicio del empleado: {e}")
        import traceback
        traceback.print_exc()
        return render_template("Em_templates/Em_Inicio.html", 
                             notificaciones=[], 
                             restantes=0, 
                             total_notificaciones=0), 500

@app.route('/Em_Consumo')
@login_requerido(rol='Empleado')
def Em_Consumo():
    return render_template('Em_templates/Em_Consumo.html')

@app.route('/Em_Rpedido', methods=['GET', 'POST'])
@login_requerido(rol='Empleado')
def Em_Rpedido():
    return render_template("Em_templates/Em_Rpedido.html")

@app.route("/registrar_pedido", methods=["POST"])
@login_requerido(rol='Empleado')
def registrar_pedido():
    if not session.get("logged_in") or session.get("role") != "Empleado":
        return jsonify({"success": False, "msg": "No autorizado"}), 401

    try:
        data = request.get_json()
        id_local = session.get("branch")
        productos = data.get("Productos")

        if not (id_local and productos and isinstance(productos, list) and len(productos) > 0):
            return jsonify({"success": False, "msg": "Datos invalidos"}), 400

        # Corregido: Ya no se inserta en 'inventario' aqui. 
        # El stock se incrementara solo cuando se RECIBE el pedido en Em_Rordenes.

        # 1. Crear el pedido principal
        pedido_res = supabase.table("pedido").insert({
            "cedula": session.get("cedula"),
            "estado": "Pendiente",
            "fecha_pedido": datetime.now().isoformat()
        }).execute()

        if not (pedido_res.data and len(pedido_res.data) > 0):
            return jsonify({"success": False, "msg": "No se pudo registrar el pedido"}), 500

        id_pedido = pedido_res.data[0]["id_pedido"]

        # 2. Registrar los detalles del pedido
        for prod in productos:
            id_producto = prod.get("Id_Producto")
            cantidad = prod.get("Cantidad")

            if not (id_producto and cantidad):
                continue

            try:
                id_producto = int(id_producto)
                cantidad = int(cantidad)
            except (ValueError, TypeError):
                continue

            if cantidad < 1 or cantidad > 500:
                return jsonify({"success": False, "msg": f"Cantidad invalida para {prod.get('Nombre', 'producto')}. Maximo 500."}), 400

            supabase.table("detalle_pedido").insert({
                "id_pedido": id_pedido,
                "id_producto": id_producto,
                "cantidad": cantidad,
                "fecha_pedido": datetime.now().isoformat()
            }).execute()

        return jsonify({
            "success": True,
            "msg": f"Pedido #{id_pedido} registrado con exito. Queda en estado 'Pendiente' hasta su recepcion."
        })
    except Exception as e:
        print("Error al registrar pedido:", e)
        return jsonify({"success": False, "msg": f"Error en el servidor: {str(e)}"}), 500

@app.route("/buscar_producto_empleado", methods=["POST"])
@login_requerido(rol='Empleado')
def buscar_producto_empleado():
    try:
        data = request.get_json()
        termino = data.get("termino", "").strip()
        query = supabase.table("productos").select("id_producto, nombre, categoria, unidad, foto").eq("habilitado", True)

        if termino:
            query = query.or_(f"nombre.ilike.%{termino}%,categoria.ilike.%{termino}%")

        result = query.order("nombre").execute()
        productos = result.data or []

        for prod in productos:
            if not prod.get("foto"):
                prod["foto"] = "/static/image/default.png"

        return jsonify({"success": True, "productos": productos})
    except Exception as e:
        print("Error en busqueda de producto (empleado):", e)
        return jsonify({"success": False, "msg": "Error al obtener productos"}), 500

@app.route('/Em_Rordenes', methods=['GET', 'POST'])
@login_requerido(rol='Empleado')
def Em_Rordenes():
    try:
        if request.method == 'POST':
            data = request.get_json()
            if not data:
                return jsonify({"success": False, "msg": "No se recibieron datos."}), 400

            id_pedido = data.get("id_pedido")
            id_producto = data.get("id_producto")
            cantidad = data.get("cantidad")
            fecha_caducidad = data.get("fecha_caducidad")

            if not all([id_pedido, id_producto, cantidad, fecha_caducidad]):
                return jsonify({"success": False, "msg": "Completa todos los campos."}), 400

            try:
                id_producto = int(id_producto)
                cantidad = int(cantidad)
                fecha_cad_dt = datetime.fromisoformat(fecha_caducidad).date()
            except Exception as e:
                return jsonify({"success": False, "msg": f"Error de tipo: {e}"}), 400

            if cantidad < 1 or cantidad > 1000:
                return jsonify({"success": False, "msg": "La cantidad debe estar entre 1 y 1000."}), 400

            hoy = date.today()
            if fecha_cad_dt <= hoy:
                return jsonify({"success": False, "msg": "La fecha de caducidad debe ser posterior a hoy."}), 400

            inv_res = supabase.table("inventario")\
                .select("*")\
                .eq("id_local", session.get("branch"))\
                .eq("id_producto", id_producto)\
                .execute()

            inventarios = inv_res.data or []
            
            try:
                # Al recibir, SIEMPRE creamos un nuevo registro (lote) en el inventario
                # para manejar correctamente las fechas de caducidad (FIFO).
                supabase.table("inventario").insert({
                    "id_local": session.get("branch"),
                    "id_producto": id_producto,
                    "cantidad": cantidad,
                    "fecha_ingreso": hoy.isoformat(),
                    "fecha_caducidad": fecha_cad_dt.isoformat(),
                    "stock_minimo": 0
                }).execute()
                
                # Opcional: Podriamos marcar el detalle como 'Recibido' si tuvieramos esa columna en detalle_pedido.
                # Por ahora, simplemente confirmamos la recepcion.
                
            except Exception as e:
                return jsonify({"success": False, "msg": f"Error al gestionar inventario: {e}"}), 500

            return jsonify({"success": True, "msg": "Producto recibido y sumado al inventario con exito."})

        pedidos = supabase.table("pedido")\
            .select("id_pedido, estado, fecha_pedido")\
            .order("id_pedido", desc=True)\
            .execute().data or []

        detalles = supabase.table("detalle_pedido")\
            .select("id_pedido, id_producto, cantidad, productos(nombre, categoria, unidad, foto)")\
            .execute().data or []

        pedidos_dict = {p["id_pedido"]: {"info": p, "productos": []} for p in pedidos}
        for d in detalles:
            if d["id_pedido"] in pedidos_dict:
                pedidos_dict[d["id_pedido"]]["productos"].append(d)

        return render_template("Em_templates/Em_Rordenes.html", pedidos=pedidos_dict)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "msg": str(e)}), 500

@app.route('/actualizar_estado', methods=['POST'])
@login_requerido(rol='Empleado')
def actualizar_estado():
    try:
        data = request.get_json()
        if not data or 'id_pedido' not in data:
            return jsonify({"success": False, "msg": "No se recibio id_pedido"}), 400

        try:
            id_pedido = int(data['id_pedido'])
        except (ValueError, TypeError):
            return jsonify({"success": False, "msg": "id_pedido invalido"}), 400

        supabase.table("pedido").update({"estado": "Recibido"})\
            .eq("id_pedido", id_pedido).execute()

        return jsonify({"success": True, "msg": "Pedido actualizado correctamente."})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "msg": str(e)}), 500

@app.route('/Em_Hordenes', methods=['GET'])
@login_requerido(rol='Empleado')
def Em_Hordenes():
    try:
        filtros = {
            "fecha": request.args.get("fecha", ""),
            "categoria": request.args.get("categoria", ""),
            "producto": request.args.get("producto", ""),
            "cantidad": request.args.get("cantidad", ""),
            "unidad": request.args.get("unidad", "")
        }

        id_pedido = request.args.get("id_pedido", "")
        fecha = request.args.get("fecha", "")

        query = supabase.table("pedido") \
            .select("id_pedido, estado, fecha_pedido, detalle_pedido(id_producto, cantidad, productos(nombre, categoria, unidad))") \
            .eq("estado", "Recibido") \
            .order("fecha_pedido", desc=True)

        pedidos = query.execute().data or []

        if id_pedido:
            pedidos = [p for p in pedidos if str(p["id_pedido"]) == str(id_pedido)]
        if fecha:
            pedidos = [p for p in pedidos if (p["fecha_pedido"] or "").split("T")[0] == fecha]

        return render_template("Em_templates/Em_Hordenes.html", pedidos=pedidos)
    except Exception as e:
        print("Error al cargar historial de ordenes:", e)
        return render_template("Em_templates/Em_Hordenes.html", pedidos=[])


if __name__ == '__main__':
    app.run(
        debug=(os.getenv('FLASK_DEBUG', 'False').lower() == 'true'),
        host=os.getenv('HOST', '127.0.0.1'),
        port=int(os.getenv('PORT', '5000'))
    )