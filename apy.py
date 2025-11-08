import os
import base64
import csv
import calendar
import io
import random
import string
import locale
from urllib import response
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from io import StringIO
from flask import Flask, flash, jsonify, render_template, request, redirect, url_for, session, make_response
from db import add_empleado, get_db_connection
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime , timedelta, date
from functools import wraps
from flask import session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from twilio.rest import Client
import logging
from twilio.base.exceptions import TwilioRestException
import requests
import json

# ==============================================================================
# CONFIGURACIÓN INICIAL Y VARIABLES DE ENTORNO
# ==============================================================================

load_dotenv()

TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE = os.getenv("TWILIO_PHONE_NUMBER")
VERIFY_SID = os.getenv("VERIFY_SERVICE_SID")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

twilio_client = Client(TWILIO_SID, TWILIO_AUTH)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
tokens_temporales = {}
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

app = Flask(__name__)
app.secret_key = '123456789'

# ==============================================================================
# FILTROS Y FUNCIONES AUXILIARES
# ==============================================================================

def enviar_token_sms(numero):
    token = str(random.randint(100000, 999999))
    mensaje = twilio_client.messages.create(
        body=f"Tu código de verificación es: {token}",
        from_=TWILIO_PHONE,
        to=f"+57{numero}"
    )
    print(f"✅ SMS enviado a {numero}. SID: {mensaje.sid}")
    return token

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
                    return jsonify({"success": False, "msg": "Sesión expirada"}), 401
                return redirect(url_for('login'))
            if rol and session.get('role') != rol:
                return jsonify({"success": False, "msg": "Acceso denegado"}), 403
            return f(*args, **kwargs)
        return decorado
    return decorador

def generar_notificaciones_caducidad():
    try:
        print(f"🕐 Iniciando generación de notificaciones - {datetime.now()}")
        hoy = datetime.now().date()
        limite = hoy + timedelta(days=3)
        
        print(f"📅 Hoy: {hoy}, Límite: {limite}")
        
        # Verificar conexión a Supabase
        print("🔌 Probando conexión a Supabase...")
        test_connection = supabase.table("inventario").select("count", count="exact").execute()
        print(f"✅ Conexión OK. Total registros en inventario: {test_connection.count}")
        
        proximos = supabase.table("inventario") \
            .select("id_inventario, id_producto, cantidad, fecha_caducidad") \
            .gte("fecha_caducidad", hoy.isoformat()) \
            .lte("fecha_caducidad", limite.isoformat()) \
            .execute()

        print(f"🔍 Productos próximos a caducar: {len(proximos.data)}")
        
        if not proximos.data:
            print("ℹ️ No hay productos próximos a caducar")
            return
            
        notificaciones_creadas = 0
        for item in proximos.data:
            print(f"📦 Procesando: ID {item['id_inventario']}, Producto {item['id_producto']}, Caduca {item['fecha_caducidad']}")
            
            # Obtener nombre del producto
            producto = supabase.table("productos") \
                .select("nombre") \
                .eq("id_producto", item["id_producto"]) \
                .single() \
                .execute()
                
            nombre_producto = producto.data["nombre"] if producto.data else "Nombre no encontrado"
            print(f"   Producto: {nombre_producto}")

            # Verificar si ya existe notificación
            noti_existente = supabase.table("notificaciones") \
                .select("id_notificaciones") \
                .eq("id_inventario", item["id_inventario"]) \
                .eq("tipo", "caducidad") \
                .execute()

            if not noti_existente.data:
                mensaje = f" El producto '{nombre_producto}' (ID: {item['id_producto']}) caduca el {item['fecha_caducidad']} | Cantidad: {item['cantidad']}"
                print(f"   📢 Creando notificación: {mensaje}")
                
                supabase.table("notificaciones").insert({
                    "id_inventario": item["id_inventario"],
                    "mensaje": mensaje,
                    "tipo": "caducidad",
                    "leido": False,
                    "fecha": datetime.now().isoformat()
                }).execute()
                notificaciones_creadas += 1
            else:
                print(f"   ✅ Notificación ya existe")

        print(f"✅ Notificaciones generadas: {notificaciones_creadas}")
        
    except Exception as e:
        print("❌ Error al generar notificaciones:", e)
        import traceback
        traceback.print_exc()

def eliminar_notificaciones_caducadas():
    try:
        hoy = datetime.now().date()
        caducados = supabase.table("inventario") \
            .select("id_inventario, id_producto, fecha_caducidad") \
            .lte("fecha_caducidad", hoy.isoformat()) \
            .execute()

        if not caducados.data:
            print("✅ No hay productos caducados hoy.")
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
        print(f"🗑️ Notificaciones eliminadas: {len(res_notif.data)}")
        print(f"💀 Productos eliminados: {len(res_inv.data)}")
    except Exception as e:
        print("❌ Error al eliminar notificaciones o productos caducados:", e)

def insertar_informe(id_pedido):
    existente = supabase.table("informe").select("id_inf_pedido").eq("id_inf_pedido", id_pedido).execute().data
    if not existente:
        supabase.table("informe").insert({
            "id_inf_pedido": id_pedido,
            "fecha_creacion": datetime.now().isoformat()
        }).execute()
        return True
    return False


# ==============================================================================
# RUTAS PRINCIPALES Y AUTENTICACIÓN
# ==============================================================================

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        usuario = data.get('id')
        password = data.get('password')
        role = data.get('role')
        branch = data.get('branch')

        if not usuario or not password or not role:
            return jsonify({"success": False, "msg": "Por favor completa todos los campos."})

        try:
            if role == "Administrador":
                if not usuario.isdigit():
                    return jsonify({"success": False, "msg": "El ID de administrador debe ser numérico."})
                query = supabase.table("administrador").select("*").eq("id", int(usuario)).execute()
                if not query.data:
                    return jsonify({"success": False, "msg": "Administrador no encontrado."}),404
                admin_user = query.data[0]
                if not check_password_hash(admin_user['contrasena'], password):
                    return jsonify({"success": False, "msg": "Contraseña incorrecta."}),401
                session['logged_in'] = True
                session['role'] = 'Administrador'
                session['cedula'] = admin_user.get('id', usuario)
                session['nombre'] = admin_user.get('nombre', '')
                return jsonify({"success": True, "msg": f"Bienvenido, {admin_user.get('nombre', '')}", "redirect": url_for('Ad_Inicio')})

            elif role == "Empleado":
                if not branch:
                    return jsonify({"success": False, "msg": "Por favor selecciona una sucursal."})
                query = supabase.table("empleados").select("*").eq("cedula", int(usuario)).execute()
                if not query.data:
                    return jsonify({"success": False, "msg": "Empleado no encontrado."}),404
                empleado = query.data[0]
                if not empleado.get('habilitado', True):
                    return jsonify({"success": False, "msg": "Empleado deshabilitado. Contacta al administrador."}),403
                if not check_password_hash(empleado['contrasena'], password):
                    return jsonify({"success": False, "msg": "Contraseña incorrecta."}),401
                session['logged_in'] = True
                session['role'] = 'Empleado'
                session['cedula'] = empleado.get('cedula', usuario)
                session['nombre'] = empleado.get('nombre', '')
                session['branch'] = int(branch)
                return jsonify({"success": True, "msg": f"Bienvenido, {empleado.get('nombre', '')}", "redirect": url_for('Em_Inicio')})
            else:
                return jsonify({"success": False, "msg": "Rol no válido."}),400
        except Exception as e:
            print("❌ Error durante el login:", e)
            return jsonify({"success": False, "msg": "Error en el servidor."}),500
    return render_template("login.html")

@app.route("/get_locales", methods=["GET"])
def get_locales():
    try:
        response = supabase.table("locales").select("id_local, nombre").execute()
        locales = response.data
        return jsonify({"success": True, "locales": locales})
    except Exception as e:
        print("❌ Error al obtener locales:", e)
        return jsonify({"success": False, "msg": "Error al obtener locales"})

@app.route('/logout')
def logout():
    session.clear()
    response = redirect(url_for('login'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# ==============================================================================
# RUTAS DE ADMINISTRADOR - INICIO Y GESTIÓN
# ==============================================================================

@app.route('/Ad_Inicio', methods=['GET', 'POST'])
@login_requerido(rol='Administrador')
def Ad_Inicio():
    try:
        print("=== AD_INICIO EJECUTÁNDOSE ===")
        
        # Generar notificaciones de caducidad
        generar_notificaciones_caducidad()
        eliminar_notificaciones_caducadas()
        
        # CONSULTA CORREGIDA: Obtener notificaciones de la base de datos
        try:
            print("🔍 Buscando notificaciones en la base de datos...")
            todas_response = supabase.table("notificaciones").select("*").order("fecha", desc=True).execute()
            todas = todas_response.data if todas_response.data else []
            print(f"✅ Notificaciones encontradas en BD: {len(todas)}")
            
            # DEBUG: Mostrar todas las notificaciones obtenidas
            for i, noti in enumerate(todas):
                print(f"  📋 {i+1}. ID: {noti.get('id_notificaciones')} - Mensaje: {noti.get('mensaje')} - Fecha: {noti.get('fecha')}")
                
        except Exception as db_error:
            print(f"❌ Error al consultar notificaciones: {db_error}")
            todas = []

        # Filtrar notificaciones vacías (pero ser más permisivo)
        todas_filtradas = []
        for n in todas:
            mensaje = n.get("mensaje", "")
            # Solo filtrar si el mensaje está completamente vacío o es None
            if mensaje is not None and str(mensaje).strip() != "":
                todas_filtradas.append(n)
            else:
                print(f" Notificación filtrada por mensaje vacío: ID {n.get('id_notificaciones')}")
        
        print(f"📊 Notificaciones después de filtrar: {len(todas_filtradas)}")
        
        # AGREGAR NOTIFICACIÓN DE PRUEBA SOLO SI NO HAY NOTIFICACIONES REALES
        if not todas_filtradas:
            print("ℹ️ No hay notificaciones reales, agregando de prueba")
            notificacion_prueba = {
                "mensaje": "🔔 NOTIFICACIÓN DE PRUEBA - Sistema funcionando",
                "fecha_formateada": datetime.now().strftime("%d de %B de %Y, %I:%M %p"),
                "leido": False
            }
            todas_filtradas.append(notificacion_prueba)
        else:
            print("✅ Usando notificaciones reales de la base de datos")

        # Configurar locale para formato en español
        try:
            locale.setlocale(locale.LC_TIME, "es_ES.utf8")
        except:
            try:
                locale.setlocale(locale.LC_TIME, "es_CO.utf8")
            except:
                print(" No se pudo configurar locale español")

        # Formatear fechas
        for noti in todas_filtradas:
            if noti.get("fecha") and not noti.get("fecha_formateada"):
                try:
                    # Manejar diferentes formatos de fecha
                    fecha_str = noti["fecha"]
                    if 'T' in fecha_str:
                        fecha_obj = datetime.fromisoformat(fecha_str.replace('Z', '+00:00'))
                    else:
                        fecha_obj = datetime.strptime(fecha_str, "%Y-%m-%d %H:%M:%S")
                    
                    noti["fecha_formateada"] = fecha_obj.strftime("%d de %B de %Y, %I:%M %p").capitalize()
                except Exception as date_error:
                    print(f" Error al formatear fecha {noti['fecha']}: {date_error}")
                    noti["fecha_formateada"] = noti["fecha"]

        # Preparar notificaciones para mostrar (máximo 3)
        notificaciones = todas_filtradas[:3]
        total_notificaciones = len(todas_filtradas)
        restantes = max(0, total_notificaciones - 3)

        print(f"📤 Enviando al template: {len(notificaciones)} notificaciones de {total_notificaciones} totales")
        print(f"🔢 Restantes: {restantes}")

        # Crear respuesta con headers para evitar cache
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
        print(f"❌ Error crítico al cargar página de inicio: {e}")
        import traceback
        traceback.print_exc()
        return render_template("Ad_templates/Ad_Inicio.html", 
                             notificaciones=[], 
                             restantes=0, 
                             total_notificaciones=0), 500

# ==============================================================================
# GESTIÓN DE EMPLEADOS (ADMIN)
# ==============================================================================

@app.route('/Ad_Rempleados', methods=['GET', 'POST'])
@login_requerido(rol='Administrador')
def Ad_Rempleados():
    return render_template("Ad_templates/Ad_Rempleados.html"), 200, {"Content-Type": "text/html; charset=utf-8"}

@app.route('/registrar_empleado', methods=['POST'])
@login_requerido(rol='Administrador')
def registrar_empleado():
    nombre = request.form.get('nombre')
    cedula = request.form.get('cedula')
    contrasena = request.form.get('contrasena')
    telefono = request.form.get('contacto')
    foto = request.files.get('foto')

    if not (nombre and cedula and contrasena and telefono):
        return jsonify({"success": False, "msg": "Todos los campos son obligatorios."})

    contrasena_hash = generate_password_hash(contrasena)
    foto_url = None

    if foto:
        try:
            filename = f"empleados/{cedula}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
            upload_response = supabase.storage.from_("Fotos").upload(filename, foto.read())
            if hasattr(upload_response, "error") and upload_response.error:
                print("❌ Error al subir imagen:", upload_response.error)
                return jsonify({"success": False, "msg": "Error al subir la foto al servidor."})
            foto_url = f"{SUPABASE_URL}/storage/v1/object/public/Fotos/{filename}"
        except Exception as e:
            print("❌ Error durante la subida de la foto:", e)
            return jsonify({"success": False, "msg": "Error al procesar la imagen."})

    try:
        data = {
            "cedula": int(cedula),
            "nombre": nombre,
            "telefono": str(telefono),
            "contrasena": contrasena_hash,
            "foto": foto_url
        }
        response = supabase.table("empleados").insert(data).execute()
        if hasattr(response, "data") and response.data:
            return jsonify({"success": True, "msg": f"Empleado {nombre} registrado correctamente."})
        else:
            return jsonify({"success": False, "msg": "No se pudo registrar el empleado. Verifica los datos."})
    except Exception as e:
        print("❌ Error inesperado al registrar:", e)
        return jsonify({"success": False, "msg": f"Error al registrar empleado: {e}"})

@app.route("/buscar_empleado", methods=["POST"])
def buscar_empleado():
    try:
        data = request.get_json()
        termino = data.get("termino", "").strip()
        if termino:
            response = supabase.table("empleados").select("*").ilike("nombre", f"%{termino}%").execute()
            if not response.data:
                response = supabase.table("empleados").select("*").ilike("Cedula", f"%{termino}%").execute()
        else:
            response = supabase.table("empleados").select("*").execute()
        empleados = response.data or []
        if empleados:
            return jsonify({"success": True, "empleados": empleados})
        else:
            return jsonify({"success": True, "empleados": []})
    except Exception as e:
        print("❌ Error en búsqueda de empleado:", e)
        return jsonify({"success": False, "msg": "Error en el servidor"})

@app.route("/editar_empleado/<int:cedula>", methods=["PUT"])
def editar_empleado(cedula):
    try:
        data = request.get_json()
        nombre = data.get("nombre")
        nueva_cedula = data.get("cedula")
        telefono = data.get("telefono")
        if not (nombre and nueva_cedula and telefono):
            return jsonify({"success": False, "msg": "Todos los campos son obligatorios."}), 400
        response = supabase.table("empleados").update({
            "nombre": nombre,
            "cedula": int(nueva_cedula),
            "telefono": str(telefono),
        }).eq("cedula", cedula).execute()
        if hasattr(response, "data") and response.data:
            return jsonify({"success": True, "msg": "Empleado actualizado correctamente."}), 200
        else:
            return jsonify({"success": False, "msg": "No se pudo actualizar el empleado."}), 500
    except Exception as e:
        print("❌ Error al editar empleado:", e)
        return jsonify({"success": False, "msg": f"Error en el servidor: {e}"}), 500

@app.route("/eliminar_empleado/<cedula>", methods=["DELETE"])
def eliminar_empleado(cedula):
    try:
        verificar = supabase.table("empleados").select("*").eq("cedula", cedula).execute()
        if not verificar.data:
            return jsonify({"success": False, "msg": "Empleado no encontrado."}), 404
        eliminar = supabase.table("empleados").delete().eq("cedula", cedula).execute()
        if hasattr(eliminar, "data") and eliminar.data:
            return jsonify({"success": True, "msg": "Empleado eliminado correctamente."}), 200
        else:
            return jsonify({"success": False, "msg": "No se pudo eliminar el empleado."}), 500
    except Exception as e:
        print("Error al eliminar empleado:", e)
        return jsonify({"success": False, "msg": "Error en el servidor"}), 500

@app.route("/cambiar_estado_empleado/<int:cedula>", methods=["POST"])
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
            return jsonify({"success": False, "msg": "No se encontró el empleado."}), 404
    except Exception as e:
        print("❌ Error al cambiar estado del producto:", e)
        return jsonify({"success": False, "msg": f"Error en servidor: {e}"}), 500

# ==============================================================================
# GESTIÓN DE PRODUCTOS (ADMIN)
# ==============================================================================

@app.route('/Ad_Rproductos', methods=['GET', 'POST'])
@login_requerido(rol='Administrador')
def Ad_Rproductos():
    return render_template("Ad_templates/Ad_Rproductos.html")

@app.route('/registrar_producto', methods=['POST'])
def registrar_producto():
    nombre = request.form.get('nombre')
    categoria = request.form.get('categoria')
    unidad = request.form.get('unidad')
    foto = request.files.get('foto')

    if not (nombre and categoria and unidad):
        return jsonify({"success": False, "msg": "Todos los campos son obligatorios."})

    try:
        data = {
            "nombre": nombre,
            "categoria": categoria,
            "unidad": unidad,
            "habilitado": True,
            "foto": None
        }
        response = supabase.table("productos").insert(data).execute()
        if not (hasattr(response, "data") and response.data):
            return jsonify({"success": False, "msg": "Error al registrar producto."})
        producto_id = response.data[0]["id_producto"]
    except Exception as e:
        print("❌ Error al insertar producto:", e)
        return jsonify({"success": False, "msg": f"Error en servidor: {e}"})

    foto_url = None
    if foto:
        try:
            filename = f"productos/{producto_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
            upload_response = supabase.storage.from_("Fotos").upload(filename, foto.read())
            if hasattr(upload_response, "error") and upload_response.error:
                print("❌ Error al subir imagen:", upload_response.error)
                return jsonify({"success": False, "msg": "Error al subir imagen."})
            foto_url = f"{SUPABASE_URL}/storage/v1/object/public/Fotos/{filename}"
            supabase.table("productos").update({"foto": foto_url}).eq("id_producto", producto_id).execute()
        except Exception as e:
            print("❌ Error al subir foto:", e)
            return jsonify({"success": False, "msg": "Error al subir foto."})

    return jsonify({
        "success": True,
        "msg": f"Producto registrado correctamente con el serial #{producto_id}.",
        "id_generado": producto_id,
        "foto_url": foto_url
    })

@app.route("/buscar_producto", methods=["POST"])
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
        print("❌ Error en búsqueda de producto:", e)
        return jsonify({"success": False, "msg": "Error en servidor"}), 500

@app.route("/obtener_proximo_id",methods=["GET"])
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
        print("❌ Error al obtener próximo ID de producto:", e)
        return jsonify({"success": False, "msg": "Error en servidor"}), 500

@app.route("/editar_producto/<int:id_producto>", methods=["PUT"])
def editar_producto(id_producto):
    try:
        data = request.get_json()
        nombre = data.get("nombre")
        categoria = data.get("categoria")
        unidad = data.get("unidad")
        if not (nombre and categoria and unidad):
            return jsonify({"success": False, "msg": "Todos los campos son obligatorios."}), 400
        response = supabase.table("productos").update({
            "nombre": nombre,
            "categoria": categoria,
            "unidad": unidad
        }).eq("id_producto", id_producto).execute()
        if hasattr(response, "data") and response.data:
            return jsonify({"success": True, "msg": "Producto actualizado correctamente."})
        else:
            return jsonify({"success": False, "msg": "No se pudo actualizar el producto."}), 500
    except Exception as e:
        print("❌ Error al editar producto:", e)
        return jsonify({"success": False, "msg": f"Error en servidor: {e}"}), 500

@app.route("/cambiar_estado_producto/<int:id_producto>", methods=["POST"])
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
            return jsonify({"success": False, "msg": "No se encontró el producto."}), 404
    except Exception as e:
        print("❌ Error al cambiar estado del producto:", e)
        return jsonify({"success": False, "msg": f"Error en servidor: {e}"}), 500

# ==============================================================================
# GESTIÓN DE INFORMES (ADMIN)
# ==============================================================================

@app.route('/Ad_Dinformes', methods=['GET'])
@login_requerido(rol='Administrador')
def Ad_Dinformes():
    try:
        # Obtener el último informe para mostrarlo en el template
        ultimo_informe = None
        informes = supabase.table("informe").select("*").order("id_informe", desc=True).limit(1).execute()
        
        if informes.data:
            ultimo_informe = informes.data[0]
        
        return render_template("Ad_templates/Ad_Dinformes.html", ultimo_informe=ultimo_informe)
    except Exception as e:
        print("❌ Error al cargar página de informes:", e)
        return render_template("Ad_templates/Ad_Dinformes.html", ultimo_informe=None)

def crear_informe_consolidado(pedidos, fecha):
    try:
        # Verificar si ya existe un informe para hoy
        fecha_inicio = f"{fecha}T00:00:00"
        fecha_fin = f"{fecha}T23:59:59"
        
        informe_existente = supabase.table("informe").select("*") \
            .gte("fecha_creacion", fecha_inicio) \
            .lte("fecha_creacion", fecha_fin) \
            .execute().data
        
        if informe_existente:
            print(" Ya existe un informe para hoy")
            return False
        
        # Crear nuevo informe consolidado
        nuevo_informe = {
            "fecha_creacion": datetime.now().isoformat(),
            "tipo": "diario_consolidado",
            "total_pedidos": len(pedidos)
        }
        
        # Insertar en la base de datos
        result = supabase.table("informe").insert(nuevo_informe).execute()
        
        if result.data:
            print(f"✅ Informe consolidado creado con {len(pedidos)} pedidos")
            return True
        return False
        
    except Exception as e:
        print("❌ Error al crear informe consolidado:", e)
        return False

def generar_pdf_consolidado(informe_id, pedidos):
    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter,
                                leftMargin=30, rightMargin=30, topMargin=40, bottomMargin=40)
        styles = getSampleStyleSheet()
        elements = []

        # ==================== ENCABEZADO ====================
        elements.append(Paragraph(
            "<font size=18 color='#e63900'><b>🍜 ICHIRAKU RAMEN - INFORME DIARIO</b></font>", 
            styles['Heading1']
        ))
        elements.append(Paragraph(
            f"<b>ID Informe:</b> #{informe_id} | <b>Fecha:</b> {datetime.now().strftime('%d/%m/%Y')}", 
            styles['Normal']
        ))
        
        # Línea decorativa
        elements.append(Spacer(1, 10))
        elements.append(Table([[""]], colWidths=[500], style=[
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#e63900")),
        ]))
        elements.append(Spacer(1, 20))

        # ==================== RESUMEN EJECUTIVO ====================
        elements.append(Paragraph("<b><font color='#e63900' size=14>📊 RESUMEN DEL DÍA</font></b>", styles['Heading2']))
        
        total_productos = 0
        categorias_totales = {}
        locales_participantes = set()
        productos_detallados = []

        # Procesar todos los pedidos para obtener estadísticas
        for pedido in pedidos:
            try:
                # Obtener detalles del pedido
                detalles = supabase.table("detalle_pedido").select("id_producto, cantidad")\
                    .eq("id_pedido", pedido["id_pedido"]).execute().data
                
                # Obtener información del local
                inventario_result = supabase.table("inventario").select("id_local")\
                    .eq("id_inventario", pedido["id_inventario"]).execute()
                
                local_nombre = "No especificado"
                if inventario_result.data:
                    local_result = supabase.table("locales").select("nombre, direccion")\
                        .eq("id_local", inventario_result.data[0]["id_local"]).execute()
                    if local_result.data:
                        local_nombre = local_result.data[0]['nombre']
                        locales_participantes.add(local_nombre)
                
                # Procesar cada detalle del pedido
                for detalle in detalles:
                    total_productos += detalle['cantidad']
                    
                    # Obtener información del producto
                    producto_result = supabase.table("productos").select("nombre, categoria, unidad")\
                        .eq("id_producto", detalle['id_producto']).execute()
                    
                    if producto_result.data:
                        producto = producto_result.data[0]
                        cat = producto.get('categoria', 'Sin categoría')
                        categorias_totales[cat] = categorias_totales.get(cat, 0) + detalle['cantidad']
                        
                        # Agregar a lista detallada
                        productos_detallados.append({
                            'pedido_id': pedido['id_pedido'],
                            'local': local_nombre,
                            'producto': producto.get('nombre', 'Desconocido'),
                            'categoria': cat,
                            'cantidad': detalle['cantidad'],
                            'unidad': producto.get('unidad', 'und'),
                            'hora': datetime.fromisoformat(pedido["fecha_pedido"]).strftime("%H:%M")
                        })
                        
            except Exception as e:
                print(f" Error procesando pedido {pedido['id_pedido']}: {e}")
                continue

        # Tabla de resumen ejecutivo
        hora_primero = min([datetime.fromisoformat(p["fecha_pedido"]).strftime("%H:%M") for p in pedidos]) if pedidos else "N/A"
        hora_ultimo = max([datetime.fromisoformat(p["fecha_pedido"]).strftime("%H:%M") for p in pedidos]) if pedidos else "N/A"
        
        resumen_data = [
            ["🗓️ Fecha", datetime.now().strftime("%d/%m/%Y")],
            ["📦 Total de Pedidos", str(len(pedidos))],
            ["⏰ Horario de Actividad", f"{hora_primero} - {hora_ultimo}"],
            ["🏪 Locales Activos", str(len(locales_participantes))],
            ["📍 Locales", ", ".join(locales_participantes) if locales_participantes else "No especificado"]
        ]
        
        resumen_table = Table(resumen_data, colWidths=[180, 320])
        resumen_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f8f9fa")),
            ("BACKGROUND", (1, 0), (1, -1), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("PADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(resumen_table)
        elements.append(Spacer(1, 25))

        # ==================== DETALLE DE PEDIDOS ====================
        elements.append(Paragraph("<b><font color='#e63900' size=14>📋 DETALLE DE PEDIDOS</font></b>", styles['Heading2']))
        elements.append(Spacer(1, 10))

        # Agrupar productos por pedido
        pedidos_agrupados = {}
        for producto in productos_detallados:
            pedido_id = producto['pedido_id']
            if pedido_id not in pedidos_agrupados:
                pedidos_agrupados[pedido_id] = {
                    'local': producto['local'],
                    'hora': producto['hora'],
                    'productos': [],
                    'total_platos': 0
                }
            pedidos_agrupados[pedido_id]['productos'].append(producto)
            pedidos_agrupados[pedido_id]['total_platos'] += producto['cantidad']

        # Generar tabla para cada pedido
        for pedido_id, info in pedidos_agrupados.items():
            # Encabezado del pedido
            elements.append(Paragraph(
                f"<b>🍱 Pedido #{pedido_id}</b> | 🏪 {info['local']} | 🕒 {info['hora']} | 🍜 {info['total_platos']} platos", 
                styles['Heading3']
            ))
            
            # Tabla de productos del pedido
            table_data = [["Plato", "Categoría", "Cantidad"]]
            
            for prod in info['productos']:
                table_data.append([
                    prod['producto'],
                    prod['categoria'],
                    f"{prod['cantidad']} {prod['unidad']}"
                ])
            
            pedido_table = Table(table_data, colWidths=[250, 150, 100])
            pedido_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e63900")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]))
            elements.append(pedido_table)
            elements.append(Spacer(1, 15))

        # ==================== PIE DE PÁGINA ====================
        elements.append(Spacer(1, 20))
        elements.append(Table([[""]], colWidths=[500], style=[
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#e63900"))
        ]))
        elements.append(Spacer(1, 10))
        
        footer_text = f"""
        <para alignment='center'>
        <font size=8 color='#666'>
        <b>🍜 Ichiraku Ramen - Sistema de Gestión</b><br/>
        Informe generado automáticamente el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}<br/>
        © 2025 Ichiraku Ramen - Todos los derechos reservados
        </font>
        </para>
        """
        elements.append(Paragraph(footer_text, styles['Normal']))

        # Generar el PDF
        doc.build(elements)
        buffer.seek(0)
        return buffer
        
    except Exception as e:
        print("❌ Error al generar PDF consolidado:", e)
        import traceback
        traceback.print_exc()
        return None

def descargar_informe_consolidado_individual(id_informe):
    try:
        print(f"📊 Generando PDF consolidado individual para informe {id_informe}")
        
        # Obtener el informe consolidado
        informe_result = supabase.table("informe").select("*").eq("id_informe", id_informe).execute()
        if not informe_result.data:
            return jsonify({"success": False, "msg": "Informe consolidado no encontrado"}), 404
        
        informe = informe_result.data[0]
        fecha_creacion = datetime.fromisoformat(informe["fecha_creacion"])
        fecha = fecha_creacion.date()
        
        # Obtener todos los pedidos del día del informe
        pedidos_hoy = supabase.table("pedido").select("*").execute().data
        pedidos_hoy = [p for p in pedidos_hoy if datetime.fromisoformat(p["fecha_pedido"]).date() == fecha]
        
        if not pedidos_hoy:
            return jsonify({"success": False, "msg": "No hay pedidos para esta fecha."})
        
        # Generar PDF
        buffer = generar_pdf_consolidado(id_informe, pedidos_hoy)
        if not buffer:
            return jsonify({"success": False, "msg": "Error al generar el PDF consolidado."})
        
        response = make_response(buffer.read())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=informe_diario_consolidado_{fecha}.pdf'
        return response
        
    except Exception as e:
        print(f"❌ Error al descargar informe consolidado individual {id_informe}: {e}")
        return jsonify({"success": False, "msg": f"Error: {e}"})

    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter,
                                leftMargin=40, rightMargin=40, topMargin=50, bottomMargin=40)
        styles = getSampleStyleSheet()
        elements = []

        # Encabezado
        encabezado = Table([
            [Paragraph("<font size=20 color='#e63900'><b>🍜 Ichiraku - Informe Diario Consolidado</b></font>", styles['Normal']),
                Paragraph(f"<font color='#555'>#{informe_id}</font>", styles['Normal'])]
        ], colWidths=[400, 100])
        encabezado.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.whitesmoke),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(encabezado)
        elements.append(Spacer(1, 15))

        # Información general
        hoy = datetime.now().strftime("%d/%m/%Y")
        total_productos = 0
        categorias_totales = {}
        locales_participantes = set()

        for pedido in pedidos:
            try:
                # Obtener detalles del pedido
                detalles = supabase.table("detalle_pedido").select("id_producto, cantidad")\
                    .eq("id_pedido", pedido["id_pedido"]).execute().data
                
                # Obtener información del local de forma segura
                inventario_result = supabase.table("inventario").select("id_local")\
                    .eq("id_inventario", pedido["id_inventario"]).execute()
                
                if inventario_result.data:
                    local_result = supabase.table("locales").select("nombre")\
                        .eq("id_local", inventario_result.data[0]["id_local"]).execute()
                    
                    if local_result.data:
                        locales_participantes.add(local_result.data[0]['nombre'])
                
                # Contar productos y categorías
                for detalle in detalles:
                    total_productos += detalle['cantidad']
                    producto_result = supabase.table("productos").select("categoria")\
                        .eq("id_producto", detalle['id_producto']).execute()
                    
                    if producto_result.data:
                        cat = producto_result.data[0].get('categoria', 'Sin categoría')
                        categorias_totales[cat] = categorias_totales.get(cat, 0) + detalle['cantidad']
                    else:
                        categorias_totales['Sin categoría'] = categorias_totales.get('Sin categoría', 0) + detalle['cantidad']
                        
            except Exception as e:
                print(f" Error procesando pedido {pedido['id_pedido']}: {e}")
                continue

        # Tabla de resumen
        info_table = [
            ["Fecha:", hoy],
            ["Total de pedidos:", str(len(pedidos))],
            ["Total de productos:", str(total_productos)],
            ["Locales participantes:", ", ".join(locales_participantes) if locales_participantes else "No especificado"]
        ]
        
        t = Table(info_table, colWidths=[150, 350])
        t.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 20))

        # Detalle de pedidos
        elements.append(Paragraph("<b><font color='#e63900' size=14>Detalle de Pedidos del Día</font></b>", styles['Heading2']))
        
        table_data = [["ID Pedido", "Local", "Productos", "Hora"]]
        for pedido in pedidos:
            try:
                inventario_result = supabase.table("inventario").select("id_local")\
                    .eq("id_inventario", pedido["id_inventario"]).execute()
                
                local_nombre = "No especificado"
                if inventario_result.data:
                    local_result = supabase.table("locales").select("nombre")\
                        .eq("id_local", inventario_result.data[0]["id_local"]).execute()
                    if local_result.data:
                        local_nombre = local_result.data[0]['nombre']
                
                detalles = supabase.table("detalle_pedido").select("id_producto, cantidad")\
                    .eq("id_pedido", pedido["id_pedido"]).execute().data
                
                hora = datetime.fromisoformat(pedido["fecha_pedido"]).strftime("%H:%M")
                
                table_data.append([
                    str(pedido["id_pedido"]),
                    local_nombre,
                    str(len(detalles)),
                    hora
                ])
            except Exception as e:
                print(f" Error en tabla para pedido {pedido['id_pedido']}: {e}")
                continue

        dt = Table(table_data, colWidths=[80, 150, 80, 80])
        dt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e63900")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        elements.append(dt)

        doc.build(elements)
        buffer.seek(0)
        return buffer
        
    except Exception as e:
        print("❌ Error al generar PDF consolidado:", e)
        return None

@app.route('/generar_informe_diario', methods=['POST'])
def generar_informe_diario():
    try:
        hoy = datetime.now().date()
        print(f"📅 Generando informe para: {hoy}")
        
        # Obtener TODOS los pedidos del día actual
        todos_pedidos = supabase.table("pedido").select("*").execute()
        
        if not todos_pedidos.data:
            return jsonify({"success": False, "msg": "No hay pedidos registrados en el sistema."})
        
        pedidos_hoy = [p for p in todos_pedidos.data 
                      if datetime.fromisoformat(p["fecha_pedido"]).date() == hoy]
        
        print(f"📊 Pedidos encontrados hoy: {len(pedidos_hoy)}")
        
        if not pedidos_hoy:
            return jsonify({"success": False, "msg": "No hay pedidos registrados para hoy."})
        
        # Verificar si ya existe un informe para hoy
        fecha_inicio = f"{hoy}T00:00:00"
        fecha_fin = f"{hoy}T23:59:59"
        
        informe_existente = supabase.table("informe").select("*") \
            .gte("fecha_creacion", fecha_inicio) \
            .lte("fecha_creacion", fecha_fin) \
            .eq("tipo", "diario_consolidado") \
            .execute()
        
        if informe_existente.data:
            print(" Ya existe un informe para hoy")
            # Retornar el ID del informe existente para poder descargarlo
            informe_id = informe_existente.data[0]['id_informe']
            return jsonify({
                "success": False, 
                "msg": f"Ya existe un informe para hoy (ID: {informe_id}).",
                "informe_id": informe_id
            })
        
        # Crear nuevo informe consolidado
        nuevo_informe = {
            "fecha_creacion": datetime.now().isoformat(),
            "tipo": "diario_consolidado",
            "total_pedidos": len(pedidos_hoy),
            "id_inf_pedido": None  # Importante: dejar como None para informes consolidados
        }
        
        print(f"💾 Insertando nuevo informe: {nuevo_informe}")
        result = supabase.table("informe").insert(nuevo_informe).execute()
        
        if result.data:
            informe_id = result.data[0]['id_informe']
            print(f"✅ Informe consolidado creado: ID {informe_id}")
            
            return jsonify({
                "success": True, 
                "msg": f"Informe diario generado exitosamente con {len(pedidos_hoy)} pedidos.",
                "informe_id": informe_id
            })
        else:
            print("❌ Error al insertar informe")
            return jsonify({"success": False, "msg": "No se pudo guardar el informe en la base de datos."})
            
    except Exception as e:
        print(f"❌ Error al generar informe diario: {e}")
        return jsonify({"success": False, "msg": f"Error: {str(e)}"})

@app.route('/obtener_ultimo_informe', methods=['GET'])
def obtener_ultimo_informe():
    try:
        # Obtener el último informe ordenado por ID descendente
        informes = supabase.table("informe").select("*").order("id_informe", desc=True).limit(1).execute()
        
        if informes.data:
            return jsonify({"success": True, "informe": informes.data[0]})
        else:
            return jsonify({"success": False, "msg": "No hay informes generados."})
            
    except Exception as e:
        print("❌ Error al obtener último informe:", e)
        return jsonify({"success": False, "msg": f"Error: {e}"})

@app.route('/buscar_informe', methods=['POST'])
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
        print("❌ Error al buscar informe:", e)
        return jsonify({"success": False, "msg": f"Error: {e}"})
    
@app.route('/descargar_informe_diario_consolidado', methods=['GET'])
def descargar_informe_diario_consolidado():
    try:
        hoy = datetime.now().date()
        
        # Buscar el informe consolidado de hoy
        fecha_inicio = f"{hoy}T00:00:00"
        fecha_fin = f"{hoy}T23:59:59"
        
        informe = supabase.table("informe").select("*") \
            .gte("fecha_creacion", fecha_inicio) \
            .lte("fecha_creacion", fecha_fin) \
            .eq("tipo", "diario_consolidado") \
            .single().execute().data
        
        if not informe:
            return jsonify({"success": False, "msg": "No hay informe diario generado para hoy."})
        
        # Obtener todos los pedidos de hoy
        pedidos_hoy = supabase.table("pedido").select("*").execute().data
        pedidos_hoy = [p for p in pedidos_hoy if datetime.fromisoformat(p["fecha_pedido"]).date() == hoy]
        
        # Generar PDF
        buffer = generar_pdf_consolidado(informe['id_informe'], pedidos_hoy)
        if not buffer:
            return jsonify({"success": False, "msg": "Error al generar el PDF."})
        
        response = make_response(buffer.read())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=informe_diario_{hoy}.pdf'
        return response
        
    except Exception as e:
        print("❌ Error al descargar informe diario:", e)
        return jsonify({"success": False, "msg": f"Error: {e}"})


@app.route('/descargar_informe/<int:id_informe>', methods=['GET'])
def descargar_informe(id_informe):
    try:
        print(f"🔍 Descargando informe ID: {id_informe}")
        
        # Obtener el informe
        informe_result = supabase.table("informe").select("*").eq("id_informe", id_informe).execute()
        if not informe_result.data:
            return jsonify({"success": False, "msg": "Informe no encontrado"}), 404
        
        informe = informe_result.data[0]
        print(f"✅ Informe encontrado: {informe}")
        
        # Verificar si es un informe consolidado
        if informe.get("tipo") == "diario_consolidado":
            print("📊 Es un informe consolidado, redirigiendo...")
            return descargar_informe_consolidado_individual(id_informe)
        
        # Si es un informe individual, continuar con la lógica original
        if not informe.get("id_inf_pedido"):
            return jsonify({"success": False, "msg": "Este informe no está asociado a un pedido"}), 404
        
        pedido_result = supabase.table("pedido").select("*").eq("id_pedido", informe["id_inf_pedido"]).execute()
        if not pedido_result.data:
            return jsonify({"success": False, "msg": "Pedido no encontrado"}), 404
        
        pedido = pedido_result.data[0]
        
        # Resto de la lógica original para informes individuales...
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
            cat = prod.get("categoria", "Sin categoría")
            categorias_count[cat] = categorias_count.get(cat, 0) + d["cantidad"]

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter,
                                leftMargin=40, rightMargin=40, topMargin=50, bottomMargin=40)
        styles = getSampleStyleSheet()
        elements = []

        encabezado = Table(
            [[
                Paragraph("<font size=20 color='#e63900'><b>🍜 Ichiraku - Informe de Pedido</b></font>", styles['Normal']),
                Paragraph(f"<font color='#555'>#{informe['id_informe']}</font>", styles['Normal'])
            ]],
            colWidths=[400, 100]
        )
        encabezado.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.whitesmoke),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10)
        ]))
        elements.append(encabezado)
        elements.append(Spacer(1, 15))

        elements.append(Table([[""]], colWidths=[540], style=[
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#e63900"))
        ]))
        elements.append(Spacer(1, 15))

        try:
            fecha_formateada = datetime.fromisoformat(informe["fecha_creacion"]).strftime("%d/%m/%Y - %I:%M %p")
        except:
            fecha_formateada = informe.get("fecha_creacion", "Sin fecha")

        info_table = [
            ["ID Informe:", informe["id_informe"]],
            ["ID Pedido:", informe["id_inf_pedido"]],
            ["Fecha de Creación:", fecha_formateada],
            ["Local:", f"{local['nombre']} ({local['direccion']})"]
        ]
        t = Table(info_table, colWidths=[150, 350])
        t.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 20))

        if data_productos:
            elements.append(Paragraph("<b><font color='#e63900' size=14>Productos del Pedido</font></b>", styles['Heading2']))
            table_data = [["ID Producto", "Nombre", "Cantidad", "Unidad"]] + data_productos
            dt = Table(table_data, colWidths=[100, 200, 100, 100])
            dt.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e63900")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica")
            ]))
            elements.append(dt)
            elements.append(Spacer(1, 25))

        if categorias_count:
            from reportlab.graphics.charts.piecharts import Pie
            from reportlab.graphics.shapes import Drawing
            elements.append(Paragraph("<b><font color='#e63900' size=14>Distribución por Categoría</font></b>", styles['Heading2']))
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

        elements.append(Spacer(1, 30))
        elements.append(Table(
            [[Paragraph("<font size=8 color='#666'>Sistema de gestión Ichiraku © 2025</font>", styles['Normal'])]],
            colWidths=[540],
            style=[('ALIGN', (0, 0), (-1, -1), 'CENTER')]
        ))

        doc.build(elements)
        buffer.seek(0)
        response = make_response(buffer.read())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=informe_{id_informe}.pdf'
        return response
        
    except Exception as e:
        print(f"❌ Error al generar PDF para informe {id_informe}: {e}")
        return jsonify({"success": False, "msg": f"Error al generar informe PDF: {e}"})

@app.route('/descargar_informes_rango', methods=['POST'])
def descargar_informes_rango():
    try:
        data = request.get_json()
        tipo = data.get("tipo")
        fecha_inicio = data.get("fecha_inicio")
        fecha_fin = data.get("fecha_fin")
        
        print(f"📅 Generando informe {tipo} desde {fecha_inicio} hasta {fecha_fin}")
        
        # Validar que tenemos los datos necesarios
        if not tipo:
            return jsonify({"success": False, "msg": "Tipo de informe no especificado."})
        
        if not fecha_inicio or not fecha_fin:
            return jsonify({"success": False, "msg": "Fechas de rango no especificadas."})

        # Obtener informes del rango de fechas
        informes = supabase.table("informe") \
            .select("*") \
            .gte("fecha_creacion", fecha_inicio) \
            .lte("fecha_creacion", fecha_fin) \
            .order("fecha_creacion", desc=True) \
            .execute()

        if not informes.data:
            return jsonify({"success": False, "msg": "No se encontraron informes en el rango especificado."})

        print(f"📊 Encontrados {len(informes.data)} informes en el rango")

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter,
                                leftMargin=30, rightMargin=30, topMargin=40, bottomMargin=40)
        styles = getSampleStyleSheet()
        elements = []

        # ==================== ENCABEZADO ====================
        # Título según el tipo
        if tipo == "semana":
            titulo = "INFORME SEMANAL CONSOLIDADO"
        elif tipo == "mes":
            titulo = "INFORME MENSUAL CONSOLIDADO"
        elif tipo == "anio":
            titulo = "INFORME ANUAL CONSOLIDADO"
        else:
            titulo = "INFORME CONSOLIDADO"

        elements.append(Paragraph(f"<font size=18 color='#e63900'><b>🍜 {titulo}</b></font>", styles['Heading1']))
        
        # Información del rango de fechas
        fecha_inicio_obj = datetime.fromisoformat(fecha_inicio.replace('T', ' '))
        fecha_fin_obj = datetime.fromisoformat(fecha_fin.replace('T', ' '))
        
        elements.append(Paragraph(
            f"<b>Período:</b> {fecha_inicio_obj.strftime('%d/%m/%Y')} - {fecha_fin_obj.strftime('%d/%m/%Y')}",
            styles['Normal']
        ))
        elements.append(Paragraph(f"<b>Total de informes:</b> {len(informes.data)}", styles['Normal']))
        
        # Línea decorativa
        elements.append(Spacer(1, 10))
        elements.append(Table([[""]], colWidths=[500], style=[
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#e63900")),
        ]))
        elements.append(Spacer(1, 20))

        # ==================== RESUMEN GENERAL ====================
        elements.append(Paragraph("<b><font color='#e63900' size=14>📊 RESUMEN GENERAL</font></b>", styles['Heading2']))
        
        total_pedidos = 0
        total_productos = 0
        categorias_totales = {}
        locales_participantes = set()
        todos_productos_detallados = []

        # Procesar TODOS los informes para obtener estadísticas consolidadas
        for inf in informes.data:
            try:
                # Si es un informe consolidado, obtener pedidos del día
                if inf.get("tipo") == "diario_consolidado":
                    fecha_inf = datetime.fromisoformat(inf["fecha_creacion"]).date()
                    
                    # Obtener todos los pedidos de ese día
                    pedidos_dia = supabase.table("pedido").select("*").execute().data
                    pedidos_dia = [p for p in pedidos_dia if datetime.fromisoformat(p["fecha_pedido"]).date() == fecha_inf]
                    
                    total_pedidos += len(pedidos_dia)
                    
                    # Procesar cada pedido del día
                    for pedido in pedidos_dia:
                        detalles = supabase.table("detalle_pedido").select("id_producto, cantidad")\
                            .eq("id_pedido", pedido["id_pedido"]).execute().data
                        
                        # Obtener información del local
                        inventario_result = supabase.table("inventario").select("id_local")\
                            .eq("id_inventario", pedido["id_inventario"]).execute()
                        
                        local_nombre = "No especificado"
                        if inventario_result.data:
                            local_result = supabase.table("locales").select("nombre")\
                                .eq("id_local", inventario_result.data[0]["id_local"]).execute()
                            if local_result.data:
                                local_nombre = local_result.data[0]['nombre']
                                locales_participantes.add(local_nombre)
                        
                        # Procesar cada detalle del pedido
                        for detalle in detalles:
                            total_productos += detalle['cantidad']
                            
                            # Obtener información del producto
                            producto_result = supabase.table("productos").select("nombre, categoria, unidad")\
                                .eq("id_producto", detalle['id_producto']).execute()
                            
                            if producto_result.data:
                                producto = producto_result.data[0]
                                cat = producto.get('categoria', 'Sin categoría')
                                categorias_totales[cat] = categorias_totales.get(cat, 0) + detalle['cantidad']
                                
                                # Agregar a lista detallada
                                todos_productos_detallados.append({
                                    'fecha': fecha_inf.strftime("%d/%m/%Y"),
                                    'informe_id': inf['id_informe'],
                                    'pedido_id': pedido['id_pedido'],
                                    'local': local_nombre,
                                    'producto': producto.get('nombre', 'Desconocido'),
                                    'categoria': cat,
                                    'cantidad': detalle['cantidad'],
                                    'unidad': producto.get('unidad', 'und'),
                                    'hora': datetime.fromisoformat(pedido["fecha_pedido"]).strftime("%H:%M")
                                })
                
                # Si es un informe individual
                elif inf.get("id_inf_pedido"):
                    total_pedidos += 1
                    
                    pedido_result = supabase.table("pedido").select("*").eq("id_pedido", inf["id_inf_pedido"]).execute()
                    if pedido_result.data:
                        pedido = pedido_result.data[0]
                        
                        detalles = supabase.table("detalle_pedido").select("id_producto, cantidad")\
                            .eq("id_pedido", pedido["id_pedido"]).execute().data
                        
                        # Obtener información del local
                        inventario_result = supabase.table("inventario").select("id_local")\
                            .eq("id_inventario", pedido["id_inventario"]).execute()
                        
                        local_nombre = "No especificado"
                        if inventario_result.data:
                            local_result = supabase.table("locales").select("nombre")\
                                .eq("id_local", inventario_result.data[0]["id_local"]).execute()
                            if local_result.data:
                                local_nombre = local_result.data[0]['nombre']
                                locales_participantes.add(local_nombre)
                        
                        # Procesar cada detalle del pedido
                        for detalle in detalles:
                            total_productos += detalle['cantidad']
                            
                            # Obtener información del producto
                            producto_result = supabase.table("productos").select("nombre, categoria, unidad")\
                                .eq("id_producto", detalle['id_producto']).execute()
                            
                            if producto_result.data:
                                producto = producto_result.data[0]
                                cat = producto.get('categoria', 'Sin categoría')
                                categorias_totales[cat] = categorias_totales.get(cat, 0) + detalle['cantidad']
                                
                                # Agregar a lista detallada
                                todos_productos_detallados.append({
                                    'fecha': datetime.fromisoformat(inf["fecha_creacion"]).strftime("%d/%m/%Y"),
                                    'informe_id': inf['id_informe'],
                                    'pedido_id': pedido['id_pedido'],
                                    'local': local_nombre,
                                    'producto': producto.get('nombre', 'Desconocido'),
                                    'categoria': cat,
                                    'cantidad': detalle['cantidad'],
                                    'unidad': producto.get('unidad', 'und'),
                                    'hora': datetime.fromisoformat(pedido["fecha_pedido"]).strftime("%H:%M")
                                })
                                
            except Exception as e:
                print(f" Error procesando informe {inf['id_informe']}: {e}")
                continue

        # Tabla de resumen general
        resumen_data = [
            ["📅 Período", f"{fecha_inicio_obj.strftime('%d/%m/%Y')} - {fecha_fin_obj.strftime('%d/%m/%Y')}"],
            ["📦 Total de Pedidos", str(total_pedidos)],
            ["📋 Total de Informes", str(len(informes.data))],
            ["🏪 Locales Activos", str(len(locales_participantes))],
            ["📍 Locales", ", ".join(locales_participantes) if locales_participantes else "No especificado"]
        ]
        
        resumen_table = Table(resumen_data, colWidths=[180, 320])
        resumen_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f8f9fa")),
            ("BACKGROUND", (1, 0), (1, -1), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("PADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(resumen_table)
        elements.append(Spacer(1, 25))


        # ==================== DETALLE POR DÍA ====================
        if todos_productos_detallados:
            elements.append(Paragraph("<b><font color='#e63900' size=14>📋 DETALLE POR DÍA</font></b>", styles['Heading2']))
            
            # Agrupar por fecha
            productos_por_fecha = {}
            for prod in todos_productos_detallados:
                fecha = prod['fecha']
                if fecha not in productos_por_fecha:
                    productos_por_fecha[fecha] = []
                productos_por_fecha[fecha].append(prod)
            
            # Ordenar fechas
            for fecha in sorted(productos_por_fecha.keys(), reverse=True):
                elements.append(Paragraph(f"<b>🗓️ {fecha}</b>", styles['Heading3']))
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
                            'total_platos': 0
                        }
                    pedidos_fecha[pedido_id]['productos'].append(prod)
                    pedidos_fecha[pedido_id]['total_platos'] += prod['cantidad']
                
                # Mostrar cada pedido de esta fecha
                for pedido_id, info in pedidos_fecha.items():
                    elements.append(Paragraph(
                        f"<b>🍱 Pedido #{pedido_id}</b> | 🏪 {info['local']} | 🕒 {info['hora']} | 🍜 {info['total_platos']} platos", 
                        styles['Normal']
                    ))
                    
                    # Tabla de productos del pedido
                    table_data = [["Plato", "Categoría", "Cantidad"]]
                    for prod in info['productos']:
                        table_data.append([
                            prod['producto'],
                            prod['categoria'],
                            f"{prod['cantidad']} {prod['unidad']}"
                        ])
                    
                    pedido_table = Table(table_data, colWidths=[250, 150, 100])
                    pedido_table.setStyle(TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e63900")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        ("PADDING", (0, 0), (-1, -1), 4),
                    ]))
                    elements.append(pedido_table)
                    elements.append(Spacer(1, 10))
                
                elements.append(Spacer(1, 15))

        # ==================== PIE DE PÁGINA ====================
        elements.append(Spacer(1, 20))
        elements.append(Table([[""]], colWidths=[500], style=[
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#e63900"))
        ]))
        elements.append(Spacer(1, 10))
        
        footer_text = f"""
        <para alignment='center'>
        <font size=8 color='#666'>
        <b>🍜 Ichiraku Ramen - Sistema de Gestión</b><br/>
        Informe {tipo} generado automáticamente el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}<br/>
        Período: {fecha_inicio_obj.strftime('%d/%m/%Y')} - {fecha_fin_obj.strftime('%d/%m/%Y')}<br/>
        © 2025 Ichiraku Ramen - Todos los derechos reservados
        </font>
        </para>
        """
        elements.append(Paragraph(footer_text, styles['Normal']))

        # Generar PDF
        doc.build(elements)
        buffer.seek(0)

        response = make_response(buffer.read())
        response.headers["Content-Type"] = "application/pdf"
        response.headers["Content-Disposition"] = f"attachment; filename=informe_{tipo}_{datetime.now().strftime('%Y%m%d')}.pdf"
        return response
        
    except Exception as e:
        print(f"❌ Error al generar informe unificado {tipo}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "msg": f"Error: {e}"})
    
# ==============================================================================
# GESTIÓN DE NOTIFICACIONES (ADMIN)
# ==============================================================================

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
def marcar_prioritaria(id):
    supabase.table("notificaciones").update({"tipo": "prioritaria"}).eq("id_notificaciones", id).execute()
    return jsonify({"success": True})

# ==============================================================================
# GESTIÓN DE LOCALES (ADMIN)
# ==============================================================================

@app.route('/Ad_Rlocales', methods=['GET', 'POST'])
@login_requerido(rol='Administrador')
def Ad_Rlocales():
    return render_template("Ad_templates/Ad_Rlocales.html")

@app.route('/registrar_local', methods=['POST'])
def registrar_local():
    nombre = request.form.get('nombre')
    direccion = request.form.get('direccion')
    id_local = request.form.get('id_local')
    foto = request.files.get('foto')

    if not (nombre and direccion and id_local):
        return jsonify({"success": False, "msg": "Todos los campos son obligatorios."})

    try:
        existing = supabase.table("locales").select("*").eq("id_local", id_local).execute()
        if existing.data:
            return jsonify({"success": False, "msg": "Ya existe un local con ese ID."})
    except Exception as e:
        print("Error al verificar local:", e)
        return jsonify({"success": False, "msg": "Error al verificar duplicados."})

    foto_url = None
    if foto:
        try:
            filename = f"locales/{id_local}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
            upload_response = supabase.storage.from_("Fotos").upload(filename, foto.read())
            if hasattr(upload_response, "error") and upload_response.error:
                print("❌ Error al subir imagen:", upload_response.error)
                return jsonify({"success": False, "msg": "Error al subir imagen."})
            foto_url = f"{SUPABASE_URL}/storage/v1/object/public/Fotos/{filename}"
        except Exception as e:
            print("❌ Error al subir foto:", e)
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
        print("❌ Error inesperado al registrar local:", e)
        return jsonify({"success": False, "msg": "Error en el servidor."})

@app.route('/obtener_siguiente_id_local', methods=['GET'])
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
        print("❌ Error al obtener siguiente ID:", e)
        return jsonify({"success": False, "msg": "Error al calcular el ID."})

@app.route("/buscar_local", methods=["POST"])
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
        print("❌ Error en búsqueda de local:", e)
        return jsonify({"success": False, "msg": "Error en el servidor"})

@app.route("/editar_local/<int:id_local>", methods=["PUT"])
def editar_local(id_local):
    try:
        data = request.get_json()
        nombre = data.get("nombre")
        direccion = data.get("direccion")
        if not (nombre and direccion):
            return jsonify({"success": False, "msg": "Todos los campos son obligatorios."}), 400
        response = supabase.table("locales").update({
            "nombre": nombre,
            "direccion": direccion
        }).eq("id_local", id_local).execute()
        if response.data:
            return jsonify({"success": True, "msg": "Local actualizado correctamente."})
        else:
            return jsonify({"success": False, "msg": "No se pudo actualizar el local."})
    except Exception as e:
        print("❌ Error al editar local:", e)
        return jsonify({"success": False, "msg": "Error en el servidor"})

@app.route("/cambiar_estado_local/<int:id_local>", methods=["POST"])
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
            return jsonify({"success": False, "msg": "No se encontró el Local."}), 404
    except Exception as e:
        print("❌ Error al cambiar estado del Local:", e)
        return jsonify({"success": False, "msg": f"Error en servidor: {e}"}), 500

# ==============================================================================
# GESTIÓN DE PERFIL ADMINISTRADOR
# ==============================================================================

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
                    "photo_url": photo_url
                }
            )

        if request.method == "POST" and request.is_json:
            data = request.get_json()
            nombre = data.get("Nombre")
            if not nombre:
                return jsonify({"success": False, "msg": "Todos los campos son obligatorios."}), 400
            update_response = supabase.table("administrador").update({"nombre" : nombre}).eq("id", cedula).execute()
            if update_response.data:
                return jsonify({"success": True, "msg": "Usuario actualizado correctamente"}), 200
            else:
                return jsonify({"success": False, "msg": "No se pudo actualizar el usuario."}), 500
    except Exception as e:
        print("❌ Error en Ad_Ceditar:", e)
        return jsonify({"success": False, "msg": "Error en el servidor"}), 500

@app.route('/Ad_Ceditar_foto', methods=['POST', 'DELETE'])
@login_requerido(rol='Administrador')
def Ad_Ceditar_foto():
    cedula = session.get('cedula')
    try:
        if request.method == 'POST':
            foto = request.files.get('foto')
            if not foto:
                return jsonify({"success": False, "msg": "No se envió ninguna foto"}), 400
            file_name = f"admin_{cedula}_{foto.filename}"
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
        print("❌ Error en Ad_Ceditar_foto:", e)
        return jsonify({"success": False, "msg": str(e)}), 500

@app.route("/enviar_token_recuperacion", methods=["POST"])
def enviar_token_recuperacion():
    try:
        data = request.get_json()
        telefono = data.get("telefono", "").strip()
        if not telefono:
            return jsonify({"success": False, "msg": "Debe ingresar un número de teléfono."}), 400

        telefono = telefono.replace(" ", "")
        if telefono.startswith("+57"):
            telefono = telefono[3:]
        elif telefono.startswith("57"):
            telefono = telefono[2:]

        if not telefono.isdigit() or len(telefono) != 10:
            return jsonify({"success": False, "msg": "El número de teléfono no es válido (debe tener 10 dígitos)."}), 400

        client = Client(TWILIO_SID, TWILIO_AUTH)
        try:
            verification = client.verify.v2.services(VERIFY_SID).verifications.create(
                to=f"+57{telefono}",
                channel="sms"
            )
            logger.info("✅ Token enviado a +57%s - SID: %s", telefono, getattr(verification, 'sid', ''))
            return jsonify({"success": True, "msg": "Código enviado correctamente."})
        except TwilioRestException as tre:
            # Manejo específico de errores de Twilio (por ejemplo: número no verificado en cuentas de prueba)
            logger.debug("TwilioRestException al enviar verificación: %s", tre)
            msg = str(tre).lower()
            if "unverified" in msg or "not verified" in msg or "cannot send messages to unverified numbers" in msg:
                return jsonify({"success": False, "msg": "El número no está verificado o no está permitido por Twilio."}), 400
            # Mensaje genérico para otros errores de Twilio
            return jsonify({"success": False, "msg": "No se pudo enviar el SMS. Verifica el número e inténtalo más tarde."}), 500
    except Exception as e:
        logger.exception("❌ Error en enviar_token_recuperacion: %s", e)
        return jsonify({"success": False, "msg": "Error interno al procesar la solicitud."}), 500

@app.route("/validar_token", methods=["POST"])
def validar_token():
    try:
        data = request.get_json()
        nombre = data.get("nombre")
        telefono = data.get("telefono", "").strip()
        token = data.get("token")
        nueva_contrasena = data.get("nueva_clave")

        if not (telefono and token and nueva_contrasena):
            return jsonify({"success": False, "msg": "Todos los campos son obligatorios."}), 400

        # Normalizar número similar a enviar_token_recuperacion
        telefono = telefono.replace(" ", "")
        if telefono.startswith("+57"):
            telefono = telefono[3:]
        elif telefono.startswith("57"):
            telefono = telefono[2:]

        client = Client(TWILIO_SID, TWILIO_AUTH)
        try:
            verfification_check = client.verify.v2.services(VERIFY_SID).verification_checks.create(
                to=f"+57{telefono}",
                code=token
            )
        except TwilioRestException as tre:
            logger.debug("TwilioRestException en verificación de código: %s", tre)
            msg = str(tre).lower()
            if "unverified" in msg or "not verified" in msg:
                return jsonify({"success": False, "msg": "El número no está verificado en Twilio o no está permitido por la cuenta de Twilio."}), 400
            return jsonify({"success": False, "msg": "No se pudo validar el código por un error del servicio de mensajería."}), 500

        if verfification_check.status != "approved":
            return jsonify({"success": False, "msg": "Código inválido o expirado."}), 400
        
        hashed_password = generate_password_hash(nueva_contrasena)
        supabase.table("administrador").update(
            {"contrasena": hashed_password}
        ).eq("nombre", nombre).execute()

        return jsonify({"success": True, "msg": "Contraseña actualizada correctamente."})
    except Exception as e:
        logger.exception("❌ Error en validar_token: %s", e)
        return jsonify({"success": False, "msg": "Error interno al validar el token."}), 500

# ==============================================================================
# RUTAS DE EMPLEADO - INICIO Y GESTIÓN
# ==============================================================================

@app.route('/Em_Inicio', methods=['GET', 'POST'])
@login_requerido(rol='Empleado')
def Em_Inicio():
    try:
        print("=== EM_INICIO EJECUTÁNDOSE ===")
        
        # Generar notificaciones de caducidad
        generar_notificaciones_caducidad()
        eliminar_notificaciones_caducadas()
        
        # CONSULTA CORREGIDA: Obtener notificaciones de la base de datos
        try:
            print("🔍 Buscando notificaciones en la base de datos (Empleado)...")
            todas_response = supabase.table("notificaciones").select("*").order("fecha", desc=True).execute()
            todas = todas_response.data if todas_response.data else []
            print(f"✅ Notificaciones encontradas en BD: {len(todas)}")
            
            # DEBUG: Mostrar todas las notificaciones obtenidas
            for i, noti in enumerate(todas):
                print(f"  📋 {i+1}. ID: {noti.get('id_notificaciones')} - Mensaje: {noti.get('mensaje')} - Fecha: {noti.get('fecha')}")
                
        except Exception as db_error:
            print(f"❌ Error al consultar notificaciones: {db_error}")
            todas = []

        # Filtrar notificaciones vacías (pero ser más permisivo)
        todas_filtradas = []
        for n in todas:
            mensaje = n.get("mensaje", "")
            # Solo filtrar si el mensaje está completamente vacío o es None
            if mensaje is not None and str(mensaje).strip() != "":
                todas_filtradas.append(n)
            else:
                print(f" Notificación filtrada por mensaje vacío: ID {n.get('id_notificaciones')}")
        
        print(f"📊 Notificaciones después de filtrar: {len(todas_filtradas)}")
        
        # AGREGAR NOTIFICACIÓN DE PRUEBA SOLO SI NO HAY NOTIFICACIONES REALES
        if not todas_filtradas:
            print("ℹ️ No hay notificaciones reales, agregando de prueba")
            notificacion_prueba = {
                "mensaje": "🔔 BIENVENIDO/AL SISTEMA - Notificaciones aparecerán aquí",
                "fecha_formateada": datetime.now().strftime("%d de %B de %Y, %I:%M %p"),
                "leido": False
            }
            todas_filtradas.append(notificacion_prueba)
        else:
            print("✅ Usando notificaciones reales de la base de datos")

        # Configurar locale para formato en español
        try:
            locale.setlocale(locale.LC_TIME, "es_ES.utf8")
        except:
            try:
                locale.setlocale(locale.LC_TIME, "es_CO.utf8")
            except:
                print(" No se pudo configurar locale español")

        # Formatear fechas
        for noti in todas_filtradas:
            if noti.get("fecha") and not noti.get("fecha_formateada"):
                try:
                    # Manejar diferentes formatos de fecha
                    fecha_str = noti["fecha"]
                    if 'T' in fecha_str:
                        fecha_obj = datetime.fromisoformat(fecha_str.replace('Z', '+00:00'))
                    else:
                        fecha_obj = datetime.strptime(fecha_str, "%Y-%m-%d %H:%M:%S")
                    
                    noti["fecha_formateada"] = fecha_obj.strftime("%d de %B de %Y, %I:%M %p").capitalize()
                except Exception as date_error:
                    print(f" Error al formatear fecha {noti['fecha']}: {date_error}")
                    noti["fecha_formateada"] = noti["fecha"]

        # Preparar notificaciones para mostrar (máximo 3)
        notificaciones = todas_filtradas[:3]
        total_notificaciones = len(todas_filtradas)
        restantes = max(0, total_notificaciones - 3)

        print(f"📤 Enviando al template: {len(notificaciones)} notificaciones de {total_notificaciones} totales")
        print(f"🔢 Restantes: {restantes}")

        # Crear respuesta con headers para evitar cache
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
        print(f"❌ Error crítico al cargar página de inicio del empleado: {e}")
        import traceback
        traceback.print_exc()
        return render_template("Em_templates/Em_Inicio.html", 
                             notificaciones=[], 
                             restantes=0, 
                             total_notificaciones=0), 500

# ==============================================================================
# GESTIÓN DE PEDIDOS (EMPLEADO)
# ==============================================================================

@app.route('/Em_Rpedido', methods=['GET', 'POST'])
@login_requerido(rol='Empleado')
def Em_Rpedido():
    return render_template("Em_templates/Em_Rpedido.html")

@app.route("/registrar_pedido", methods=["POST"])
def registrar_pedido():
    if not session.get("logged_in") or session.get("role") != "Empleado":
        return jsonify({"success": False, "msg": "No autorizado"}), 401

    try:
        data = request.get_json()
        id_local = session.get("branch")
        productos = data.get("Productos")

        if not (id_local and productos and isinstance(productos, list) and len(productos) > 0):
            return jsonify({"success": False, "msg": "Datos inválidos"}), 400

        inventarios = []
        for prod in productos:
            id_producto = prod.get("Id_Producto")
            cantidad = prod.get("Cantidad")
            fecha_ingreso = prod.get("Fecha_Ingreso")
            fecha_caducidad = prod.get("Fecha_Caducidad")

            if not (id_producto and cantidad and fecha_ingreso and fecha_caducidad):
                continue

            try:
                id_producto = int(id_producto)
            except ValueError:
                id_producto = str(id_producto)

            inv = supabase.table("inventario").insert({
                "id_local": id_local,
                "id_producto": id_producto,
                "cantidad": cantidad,
                "stock_minimo": 0
            }).execute()

            if inv.data:
                inventarios.append(inv.data[0]["id_inventario"])

        if not inventarios:
            return jsonify({"success": False, "msg": "No se pudieron registrar inventarios"}), 400

        pedido = supabase.table("pedido").insert({
            "id_inventario": inventarios[0],
            "cedula": session.get("cedula")
        }).execute()

        if not pedido.data:
            return jsonify({"success": False, "msg": "No se pudo registrar el pedido"}), 500

        id_pedido = pedido.data[0]["id_pedido"]

        for prod in productos:
            id_producto = prod.get("Id_Producto")
            try:
                id_producto = int(id_producto)
            except ValueError:
                id_producto = str(id_producto)

            supabase.table("detalle_pedido").insert({
                "id_pedido": id_pedido,
                "id_producto": id_producto,
                "cantidad": prod.get("Cantidad"),
                "fecha_pedido": prod.get("Fecha_Ingreso")
            }).execute()

        return jsonify({
            "success": True,
            "msg": f"Pedido #{id_pedido} registrado con éxito con {len(productos)} productos."
        })
    except Exception as e:
        print("❌ Error al registrar pedido:", e)
        return jsonify({"success": False, "msg": f"Error en el servidor: {str(e)}"}), 500

@app.route("/buscar_producto_empleado", methods=["POST"])
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
        print("❌ Error en búsqueda de producto (empleado):", e)
        return jsonify({"success": False, "msg": "Error al obtener productos"}), 500

# ==============================================================================
# RECEPCIÓN DE PEDIDOS (EMPLEADO)
# ==============================================================================

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

            hoy = date.today()
            if fecha_cad_dt <= hoy:
                return jsonify({"success": False, "msg": "La fecha de caducidad debe ser posterior a hoy."}), 400

            inv_res = supabase.table("inventario")\
                .select("*")\
                .eq("id_local", session.get("branch"))\
                .eq("id_producto", id_producto)\
                .execute()

            inventarios = inv_res.data or []
            if not inventarios:
                return jsonify({"success": False, "msg": "No existe inventario previo para este producto."}), 400

            inventario_id = inventarios[0]["id_inventario"]

            try:
                supabase.table("inventario").update({
                    "cantidad": cantidad,
                    "fecha_ingreso": hoy.isoformat(),
                    "fecha_caducidad": fecha_cad_dt.isoformat()
                }).eq("id_inventario", inventario_id).execute()
            except Exception as e:
                return jsonify({"success": False, "msg": f"Error al actualizar inventario: {e}"}), 500

            return jsonify({"success": True, "msg": "Producto confirmado correctamente."})

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
            return jsonify({"success": False, "msg": "No se recibió id_pedido"}), 400

        try:
            id_pedido = int(data['id_pedido'])
        except (ValueError, TypeError):
            return jsonify({"success": False, "msg": "id_pedido inválido"}), 400

        supabase.table("pedido").update({"estado": "Recibido"})\
            .eq("id_pedido", id_pedido).execute()

        return jsonify({"success": True, "msg": "Pedido actualizado correctamente."})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "msg": str(e)}), 500

# ==============================================================================
# HISTORIAL DE PEDIDOS (EMPLEADO)
# ==============================================================================

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
        print("❌ Error al cargar historial de órdenes:", e)
        return render_template("Em_templates/Em_Hordenes.html", pedidos=[])

# ==============================================================================
# GESTIÓN DE PERFIL EMPLEADO
# ==============================================================================

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
                    "photo_url": photo_url
                }
            )

        if request.method == "POST" and request.is_json:
            data = request.get_json()
            nombre = data.get("Nombre")
            if not nombre:
                return jsonify({"success": False, "msg": "El nombre es obligatorio."}), 400
            update_response = supabase.table("empleados").update({"nombre": nombre}).eq("cedula", cedula).execute()
            if update_response.data:
                return jsonify({"success": True, "msg": "Perfil actualizado correctamente"}), 200
            else:
                return jsonify({"success": False, "msg": "No se pudo actualizar el perfil."}), 500
    except Exception as e:
        print("❌ Error en Em_Ceditar:", e)
        return jsonify({"success": False, "msg": "Error en el servidor"}), 500

@app.route('/Em_Ceditar_foto', methods=['POST', 'DELETE'])
@login_requerido(rol='Empleado')
def Em_Ceditar_foto():
    cedula = session.get('cedula')
    try:
        if request.method == 'POST':
            foto = request.files.get('foto')
            if not foto:
                return jsonify({"success": False, "msg": "No se envió ninguna foto"}), 400
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
        print("❌ Error en Em_Ceditar_foto:", e)
        return jsonify({"success": False, "msg": str(e)}), 500

# ==============================================================================
# RECUPERACIÓN DE CONTRASEÑA EMPLEADO
# ==============================================================================

@app.route("/Em_enviar_token_recuperacion", methods=["POST"])
def Em_enviar_token_recuperacion():
    try:
        data = request.get_json()
        telefono = data.get("telefono", "").strip()
        if not telefono:
            return jsonify({"success": False, "msg": "Debe ingresar un número de teléfono."}), 400

        telefono = telefono.replace(" ", "")
        if telefono.startswith("+57"):
            telefono = telefono[3:]
        elif telefono.startswith("57"):
            telefono = telefono[2:]

        if not telefono.isdigit() or len(telefono) != 10:
            return jsonify({"success": False, "msg": "Número de teléfono no válido."}), 400

        client = Client(TWILIO_SID, TWILIO_AUTH)
        client.verify.v2.services(VERIFY_SID).verifications.create(to=f"+57{telefono}", channel="sms")
        return jsonify({"success": True, "msg": "Código enviado correctamente."})
    except Exception as e:
        print(f"❌ Error en Em_enviar_token_recuperacion: {e}")
        return jsonify({"success": False, "msg": str(e)}), 500

@app.route("/Em_validar_token", methods=["POST"])
def Em_validar_token():
    try:
        data = request.get_json()
        nombre = data.get("nombre", "").strip()
        telefono = data.get("telefono", "").strip()
        token = data.get("token", "").strip()
        nueva_contrasena = data.get("nueva_clave", "").strip()

        if not (nombre and telefono and token and nueva_contrasena):
            return jsonify({"success": False, "msg": "Todos los campos son obligatorios."}), 400

        if telefono.startswith("+57"):
            telefono = telefono[3:]
        elif telefono.startswith("57"):
            telefono = telefono[2:]

        client = Client(TWILIO_SID, TWILIO_AUTH)
        verification_check = client.verify.v2.services(VERIFY_SID).verification_checks.create(
            to=f"+57{telefono}",
            code=token
        )

        if verification_check.status != "approved":
            return jsonify({"success": False, "msg": "Código inválido o expirado."}), 400

        empleado_resp = supabase.table("empleados").select("*")\
            .eq("nombre", nombre)\
            .eq("telefono", telefono)\
            .execute()

        if not empleado_resp.data:
            return jsonify({"success": False, "msg": "Empleado no encontrado."}), 404

        cedula = empleado_resp.data[0]["cedula"]
        hashed_password = generate_password_hash(nueva_contrasena)
        update_resp = supabase.table("empleados").update(
            {"contrasena": hashed_password}
        ).match({"cedula": cedula}).execute()

        if not update_resp.data:
            return jsonify({"success": False, "msg": "No se actualizó ninguna fila. Verifique el filtro."}), 400

        return jsonify({"success": True, "msg": "Contraseña actualizada correctamente."})
    except Exception as e:
        print(f"❌ Error en Em_validar_token: {e}")
        return jsonify({"success": False, "msg": str(e)}), 500

# ==============================================================================
# EJECUCIÓN PRINCIPAL
# ==============================================================================

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)