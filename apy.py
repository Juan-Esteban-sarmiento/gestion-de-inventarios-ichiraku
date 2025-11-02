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


# Cargar variables del archivo .env
load_dotenv()



TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE = os.getenv("TWILIO_PHONE_NUMBER")
VERIFY_SID = os.getenv("VERIFY_SERVICE_SID")

twilio_client = Client(TWILIO_SID, TWILIO_AUTH)
tokens_temporales = {}

# Leer valores desde el .env
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")


# Crear el cliente de Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))



app = Flask(__name__)
app.secret_key = '123456789'

import random

def enviar_token_sms(numero):
    # Generar código de 6 dígitos
    token = str(random.randint(100000, 999999))

    # Enviar SMS
    mensaje = twilio_client.messages.create(
        body=f"Tu código de verificación es: {token}",
        from_=TWILIO_PHONE,
        to=f"+57{numero}"  # Agrega el código de país
    )

    print(f"✅ SMS enviado a {numero}. SID: {mensaje.sid}")
    return token





# ╔══════════════════════════════════════════════╗
# ║ Redirección inicial de Logueo                ║
# ╚══════════════════════════════════════════════╝

@app.route('/')
def index():
    return redirect(url_for('login'))

# ╔══════════════════════════════════════════════╗
# ║ Configuración de Logueo                      ║
# ╚══════════════════════════════════════════════╝

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
            # LOGIN ADMINISTRADOR
            if role == "Administrador":

                if not usuario.isdigit():
                    return jsonify({"success": False, "msg": "El ID de administrador debe ser numérico."})
                
                query = (
                    supabase.table("administrador")
                    .select("*")
                    .eq("id", int(usuario))
                    .execute()
                )

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

            # LOGIN EMPLEADO
            elif role == "Empleado":
                if not branch:
                    return jsonify({"success": False, "msg": "Por favor selecciona una sucursal."})

                query = (
                    supabase.table("empleados")
                    .select("*")
                    .eq("cedula", int(usuario))
                    .execute()
                )

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

# Obtener locales para select dinámico
@app.route("/get_locales", methods=["GET"])
def get_locales():
    try:
        response = supabase.table("locales").select("id_local, nombre").execute()
        locales = response.data
        return jsonify({"success": True, "locales": locales})
    except Exception as e:
        print("❌ Error al obtener locales:", e)
        return jsonify({"success": False, "msg": "Error al obtener locales"})
    

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

# ╔════════════════╗
# ║ Ruta de inicio ║
# ╚════════════════╝

@app.route('/Ad_Inicio', methods=['GET', 'POST'])
@login_requerido(rol='Administrador')
def Ad_Inicio():
    try:
        generar_notificaciones_caducidad()
        eliminar_notificaciones_caducadas()

        hoy = datetime.now().date()

       # Obtener todas las notificaciones ordenadas por fecha
        todas_response = supabase.table("notificaciones").select("*").order("fecha", desc=True).execute()
        todas = todas_response.data if todas_response.data else []

        # 🔹 Filtrar solo las que tienen mensaje válido
        todas = [n for n in todas if n.get("mensaje") and n["mensaje"].strip() != ""]

        # 🔹 Formatear la fecha para que se vea más legible (30 de octubre de 2025, 04:11 p.m.)

        try:
            locale.setlocale(locale.LC_TIME, "es_ES.utf8")
        except:
            locale.setlocale(locale.LC_TIME, "es_CO.utf8")

        for noti in todas:
            if noti.get("fecha"):
                try:
                    fecha_obj = datetime.fromisoformat(noti["fecha"])
                    noti["fecha_formateada"] = fecha_obj.strftime("%d de %B de %Y, %I:%M %p").capitalize()
                except:
                    noti["fecha_formateada"] = noti["fecha"]

        # 🔹 Mostrar solo las primeras 3 si existen
        notificaciones = todas[:3]
        total_notificaciones = len(todas)
        restantes = max(0, total_notificaciones - 3)

        http_response = make_response(render_template(
            "Ad_templates/Ad_Inicio.html",
            notificaciones=notificaciones,
            restantes=restantes,
            total_notificaciones=total_notificaciones
        ))

        # Evitar caché
        http_response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        http_response.headers['Pragma'] = 'no-cache'
        http_response.headers['Expires'] = '-1'

        return http_response

    except Exception as e:
        print("❌ Error al cargar página de inicio:", e)
        return render_template("Ad_templates/Ad_Inicio.html", notificaciones=[], restantes=0), 500

# ╔════════════════════════════════════════════════════════╗
# ║ Registro, Búsqueda, Edicion y Eliminación de Empleados ║
# ╚════════════════════════════════════════════════════════╝

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
    telefono = request.form.get('contacto')  # 🟢 Renombramos a 'telefono'
    foto = request.files.get('foto')

    if not (nombre and cedula and contrasena and telefono):
        return jsonify({"success": False, "msg": "Todos los campos son obligatorios."})

    # 🔒 Hashear la contraseña antes de guardarla
    contrasena_hash = generate_password_hash(contrasena)

    foto_url = None

    # 🖼️ Subir la foto al bucket de Supabase
    if foto:
        try:
            filename = f"empleados/{cedula}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
            upload_response = supabase.storage.from_("Fotos").upload(filename, foto.read())

            if hasattr(upload_response, "error") and upload_response.error:
                print("❌ Error al subir imagen:", upload_response.error)
                return jsonify({"success": False, "msg": "Error al subir la foto al servidor."})

            foto_url = f"{SUPABASE_URL}/storage/v1/object/public/Fotos/{filename}"
            print("✅ Foto subida correctamente:", foto_url)

        except Exception as e:
            print("❌ Error durante la subida de la foto:", e)
            return jsonify({"success": False, "msg": "Error al procesar la imagen."})

    try:
        # 🟢 Insertar en la tabla 'empleados' con la nueva columna 'telefono'
        data = {
            "cedula": int(cedula),
            "nombre": nombre,
            "telefono": str(telefono),  # <- aquí usamos la columna correcta
            "contrasena": contrasena_hash,
            "foto": foto_url
        }

        response = supabase.table("empleados").insert(data).execute()

        if hasattr(response, "data") and response.data:
            print("✅ Empleado insertado correctamente:", response.data)
            return jsonify({
                "success": True,
                "msg": f"Empleado {nombre} registrado correctamente."
            })
        else:
            print("❌ Error al insertar en empleados:", response)
            return jsonify({
                "success": False,
                "msg": "No se pudo registrar el empleado. Verifica los datos."
            })

    except Exception as e:
        print("❌ Error inesperado al registrar:", e)
        return jsonify({
            "success": False,
            "msg": f"Error al registrar empleado: {e}"
        })


@app.route("/buscar_empleado", methods=["POST"])
def buscar_empleado():
    try:
        data = request.get_json()
        termino = data.get("termino", "").strip()

        if termino:
            # 🔍 Buscar por nombre o cédula (coincidencia parcial)
            response = (
                supabase.table("empleados")
                .select("*")
                .ilike("nombre", f"%{termino}%")
                .execute()
            )

            if not response.data:
                # Si no hay coincidencias por nombre, buscar por cédula
                response = (
                    supabase.table("empleados")
                    .select("*")
                    .ilike("Cedula", f"%{termino}%")
                    .execute()
                )
        else:
            # 📋 Si no hay término, traer todos los empleados
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
        numero_contacto = data.get("numero_contacto")

        if not (nombre and nueva_cedula and numero_contacto):
            return jsonify({"success": False, "msg": "Todos los campos son obligatorios."}), 400

        response = (
            supabase.table("empleados")
            .update({
                "nombre": nombre,
                "cedula": int(nueva_cedula),
                "numero_contacto": int(numero_contacto),
            })
            .eq("cedula", cedula)
            .execute()
        )

        if hasattr(response, "data") and response.data:
            print("Empleado actualizado correctamente:", response.data)
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
            print("Empleado eliminado correctamente:", eliminar.data)
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




# ╔══════════════════════════════════════════════╗
# ║ Registro, Búsqueda y Eliminación de Productos║
# ╚══════════════════════════════════════════════╝

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

    # Insertamos primero para obtener el ID del producto
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

    # Subir imagen con el nombre final después de tener el ID
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

        # Los administradores ven TODOS los productos (habilitados y deshabilitados)
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

        response = (
            supabase.table("productos")
            .update({
                "nombre": nombre,
                "categoria": categoria,
                "unidad": unidad
            })
            .eq("id_producto", id_producto)
            .execute()
        )

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



# ╔══════════════════════════════════════════════╗
# ║ Generación y gestión de informes             ║
# ╚══════════════════════════════════════════════╝

@app.route('/Ad_Dinformes', methods=['GET'])
@login_requerido(rol='Administrador')
def Ad_Dinformes():
    return render_template("Ad_templates/Ad_Dinformes.html")

def insertar_informe(id_pedido):
    existente = supabase.table("informe").select("id_inf_pedido").eq("id_inf_pedido", id_pedido).execute().data
    if not existente:
        supabase.table("informe").insert({
            "id_inf_pedido": id_pedido,
            "fecha_creacion": datetime.now().isoformat()
        }).execute()
        return True
    return False


@app.route('/generar_informe_diario', methods=['POST'])
def generar_informe_diario():
    try:
        hoy = datetime.now().date()
        pedidos = supabase.table("pedido").select("id_pedido, fecha_pedido").execute().data
        if not pedidos:
            return jsonify({"success": False, "msg": "No hay pedidos registrados."})

        informes_creados = sum(insertar_informe(p["id_pedido"]) for p in pedidos if datetime.fromisoformat(p["fecha_pedido"]).date() == hoy)
        msg = f"Informes diarios generados: {informes_creados}" if informes_creados else "No se generaron nuevos informes hoy."
        return jsonify({"success": True, "msg": msg})

    except Exception as e:
        print("❌ Error al generar informe diario:", e)
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
    
@app.route('/descargar_informe/<int:id_informe>', methods=['GET'])
def descargar_informe(id_informe):
    try:
        # 🧾 Obtener el informe desde la base de datos
        informe = supabase.table("informe").select("*").eq("id_informe", id_informe).single().execute().data
        if not informe:
            return jsonify({"success": False, "msg": "Informe no encontrado"}), 404

        # 🧩 Obtener pedido asociado
        pedido = supabase.table("pedido").select("*").eq("id_pedido", informe["id_inf_pedido"]).single().execute().data
        if not pedido:
            return jsonify({"success": False, "msg": "Pedido no encontrado"}), 404

        # 📦 Obtener información de inventario y local
        inventario = supabase.table("inventario").select("id_local").eq("id_inventario", pedido["id_inventario"]).single().execute().data
        local = supabase.table("locales").select("nombre, direccion").eq("id_local", inventario["id_local"]).single().execute().data

        # 📋 Obtener detalles del pedido y productos
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

        # 🧾 --- Generar PDF ---
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter,
                                leftMargin=40, rightMargin=40, topMargin=50, bottomMargin=40)
        styles = getSampleStyleSheet()
        elements = []

        # ✅ Encabezado
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

        # 🔸 Separador
        elements.append(Table([[""]], colWidths=[540], style=[
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#e63900"))
        ]))
        elements.append(Spacer(1, 15))

        # 🕒 Información general
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

        # 📦 Productos
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

        # 📊 Gráfico de categorías
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

        # 🔻 Pie
        elements.append(Spacer(1, 30))
        elements.append(Table(
            [[Paragraph("<font size=8 color='#666'>Sistema de gestión Ichiraku © 2025</font>", styles['Normal'])]],
            colWidths=[540],
            style=[('ALIGN', (0, 0), (-1, -1), 'CENTER')]
        ))

        # ✅ Cerrar PDF correctamente
        doc.build(elements)
        buffer.seek(0)

        # 🧠 OPCIONAL: Guardar localmente para probar
        # with open("test_informe.pdf", "wb") as f:
        #     f.write(buffer.getvalue())

        # 📤 Responder PDF
        response = make_response(buffer.read())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=informe_{id_informe}.pdf'
        return response

    except Exception as e:
        print("❌ Error al generar PDF:", e)
        return jsonify({"success": False, "msg": f"Error al generar informe PDF: {e}"})


@app.route('/descargar_informes_rango', methods=['POST'])
def descargar_informes_rango():
    try:
        data = request.get_json()
        tipo = data.get("tipo")
        ahora = datetime.now()

        if tipo == "semana":
            inicio = ahora - timedelta(days=ahora.weekday())
            fin = inicio + timedelta(days=6)
            titulo = "INFORME UNIFICADO SEMANAL"
        elif tipo == "mes":
            _, dias_mes = calendar.monthrange(ahora.year, ahora.month)
            inicio = datetime(ahora.year, ahora.month, 1)
            fin = datetime(ahora.year, ahora.month, dias_mes)
            titulo = "INFORME UNIFICADO MENSUAL"
        elif tipo == "anio":
            inicio = datetime(ahora.year, 1, 1)
            fin = datetime(ahora.year, 12, 31, 23, 59, 59)
            titulo = "INFORME UNIFICADO ANUAL"
        else:
            return jsonify({"success": False, "msg": "Tipo inválido."})

        # 🔹 Obtener todos los informes dentro del rango
        informes = supabase.table("informe") \
            .select("*") \
            .gte("fecha_creacion", inicio.isoformat()) \
            .lte("fecha_creacion", fin.isoformat()) \
            .execute().data

        if not informes:
            return jsonify({"success": False, "msg": "No se encontraron informes."})

        # 🔸 PDF setup
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []

        elements.append(Paragraph(f"<b><font color='#e63900' size=18>🍥 {titulo}</font></b>", styles['Title']))
        elements.append(Spacer(1, 20))

        for inf in informes:
            # Obtener pedido asociado
            pedido = supabase.table("pedido").select("*").eq("id_pedido", inf["id_inf_pedido"]).single().execute().data
            if not pedido:
                continue

            # Obtener detalles de productos
            detalles = supabase.table("detalle_pedido").select("id_producto, cantidad").eq("id_pedido", pedido["id_pedido"]).execute().data
            productos = supabase.table("productos").select("id_producto, nombre, unidad").execute().data
            mapa = {p["id_producto"]: p for p in productos}

            # Encabezado del informe individual
            fecha_f = datetime.fromisoformat(inf["fecha_creacion"]).strftime("%d/%m/%Y %I:%M %p")
            elements.append(Paragraph(f"<b>ID Informe:</b> {inf['id_informe']} — <b>Pedido:</b> {inf['id_inf_pedido']} — <b>Fecha:</b> {fecha_f}", styles["Normal"]))
            elements.append(Spacer(1, 8))

            if detalles:
                table_data = [["Producto", "Cantidad", "Unidad"]]
                for d in detalles:
                    prod = mapa.get(d["id_producto"], {})
                    table_data.append([
                        prod.get("nombre", "Desconocido"),
                        d["cantidad"],
                        prod.get("unidad", "-")
                    ])

                tabla = Table(table_data, colWidths=[250, 100, 100])
                tabla.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e63900")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold")
                ]))
                elements.append(tabla)
                elements.append(Spacer(1, 15))

            # Separador entre informes
            elements.append(Table([[""]], colWidths=[540], style=[
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#e63900"))
            ]))
            elements.append(Spacer(1, 20))

        # Pie
        elements.append(Paragraph("<font size=8 color='#666'>Sistema de gestión Ichiraku © 2025</font>", styles['Normal']))

        # Crear PDF
        doc.build(elements)
        buffer.seek(0)

        response = make_response(buffer.read())
        response.headers["Content-Type"] = "application/pdf"
        response.headers["Content-Disposition"] = f"attachment; filename=informe_unificado_{tipo}.pdf"
        return response

    except Exception as e:
        print("❌ Error al generar informe unificado:", e)
        return jsonify({"success": False, "msg": f"Error: {e}"})


# ╔═══════════════════════════════════════════════════════╗
# ║ Gestión de notificaciones                             ║
# ╚═══════════════════════════════════════════════════════╝

@app.route('/Ad_Pnotificaciones', methods=['GET'])
@login_requerido(rol='Administrador')
def Ad_Pnotificaciones():
    generar_notificaciones_caducidad()
    eliminar_notificaciones_caducadas()

    # Obtener todas las notificaciones ordenadas por fecha
    notificaciones = supabase.table("notificaciones") \
        .select("*") \
        .order("fecha", desc=True) \
        .execute()

    return render_template("Ad_templates/Ad_Pnotificaciones.html", notificaciones=notificaciones.data)


def generar_notificaciones_caducidad():
    """
    🔹 Genera notificaciones 3 días antes de la fecha de caducidad.
    """
    try:
        hoy = datetime.now().date()
        limite = hoy + timedelta(days=3)

        proximos = supabase.table("inventario") \
            .select("id_inventario, id_producto, cantidad, fecha_caducidad") \
            .gte("fecha_caducidad", hoy.isoformat()) \
            .lte("fecha_caducidad", limite.isoformat()) \
            .execute()

        for item in proximos.data:
            producto = supabase.table("productos") \
                .select("nombre") \
                .eq("id_producto", item["id_producto"]) \
                .single() \
                .execute()

            nombre_producto = producto.data["nombre"] if producto.data else "Nombre no encontrado"

            noti_existente = supabase.table("notificaciones") \
                .select("id_notificaciones") \
                .eq("id_inventario", item["id_inventario"]) \
                .eq("tipo", "caducidad") \
                .execute()

            if not noti_existente.data:
                mensaje = f"⚠️ El producto '{nombre_producto}' (ID: {item['id_producto']}) caduca el {item['fecha_caducidad']} | Cantidad: {item['cantidad']}"
                supabase.table("notificaciones").insert({
                    "id_inventario": item["id_inventario"],
                    "mensaje": mensaje,
                    "tipo": "caducidad",
                    "leido": False,
                    "fecha": datetime.now().isoformat()
                }).execute()

        print("✅ Notificaciones generadas correctamente.")
    except Exception as e:
        print("❌ Error al generar notificaciones:", e)


def eliminar_notificaciones_caducadas():
    """
    🔹 Elimina notificaciones y productos cuando llegan a su fecha de caducidad.
    🔹 Orden correcto: primero notificaciones -> luego inventario.
    """
    try:
        hoy = datetime.now().date()

        # Buscar inventario caducado (fecha de caducidad <= hoy)
        caducados = supabase.table("inventario") \
            .select("id_inventario, id_producto, fecha_caducidad") \
            .lte("fecha_caducidad", hoy.isoformat()) \
            .execute()

        if not caducados.data:
            print("✅ No hay productos caducados hoy.")
            return

        print(f"🧾 Se encontraron {len(caducados.data)} productos caducados:")

        # 1️⃣ Obtener todos los IDs de inventario caducados
        ids_caducados = [item["id_inventario"] for item in caducados.data]

        # 2️⃣ Eliminar todas las notificaciones asociadas a esos inventarios
        res_notif = supabase.table("notificaciones") \
            .delete() \
            .in_("id_inventario", ids_caducados) \
            .execute()
        print(f"🗑️ Notificaciones eliminadas asociadas a productos caducados → {len(res_notif.data)} registros.")

        # 3️⃣ Eliminar los inventarios caducados
        res_inv = supabase.table("inventario") \
            .delete() \
            .in_("id_inventario", ids_caducados) \
            .execute()
        print(f"💀 Productos caducados eliminados del inventario → {len(res_inv.data)} registros.")

        print("✅ Limpieza completada correctamente.")
    except Exception as e:
        print("❌ Error al eliminar notificaciones o productos caducados:", e)

# 🔹 Solo mantener la función de marcar como prioritaria
@app.route('/marcar_prioritaria/<int:id>', methods=['POST'])
def marcar_prioritaria(id):
    supabase.table("notificaciones").update({"tipo": "prioritaria"}).eq("id_notificaciones", id).execute()
    return jsonify({"success": True})


# ╔═══════════════════════════════════════════════════════╗
# ║ Gestion , busqueda, edicion y eliminacion de locales  ║
# ╚═══════════════════════════════════════════════════════╝

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

    # Validación
    if not (nombre and direccion and id_local):
        return jsonify({"success": False, "msg": "Todos los campos son obligatorios."})

    # Verificar duplicado
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
            print("✅ Local registrado correctamente:", response.data)
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

        response = (
            supabase.table("locales")
            .update({
                "nombre": nombre,
                "direccion": direccion
            })
            .eq("id_local", id_local)
            .execute()
        )

        if response.data:
            print("Local actualizado correctamente:", response.data)
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


# ╔══════════════════════════════════════════════╗
# ║ Edición de Datos del Administrador           ║
# ╚══════════════════════════════════════════════╝

@app.route("/Ad_Ceditar", methods=["GET", "POST"])
@login_requerido(rol='Administrador')
def Ad_Ceditar():
    cedula = session.get("cedula")

    try:
        # 🧩 Obtener datos del administrador desde Supabase
        response = (
            supabase.table("administrador")
            .select("*")
            .eq("id", cedula)
            .execute()
        )

        admin = response.data[0] if response.data else None

        if not admin:
            return jsonify({"success": False, "msg": "Administrador no encontrado."}), 404

        # 🧠 Si es un GET → mostrar plantilla con datos actuales
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

        # 🧱 Si es un POST JSON → actualizar datos
        if request.method == "POST" and request.is_json:
            data = request.get_json()
            nombre = data.get("Nombre")

            if not nombre:
                return jsonify({"success": False, "msg": "Todos los campos son obligatorios."}), 400

            update_response = (
                supabase.table("administrador")
                .update({"nombre" : nombre})
                .eq("id", cedula)
                .execute()
            )

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

            # Crear nombre único y leer bytes
            file_name = f"admin_{cedula}_{foto.filename}"
            file_bytes = foto.read()

            # ✅ Subir al bucket de Supabase (sin encabezado adicional)
            upload_response = supabase.storage.from_("fotos_admin").upload(file_name, file_bytes)

            if hasattr(upload_response, "error") and upload_response.error:
                return jsonify({"success": False, "msg": "Error al subir la foto a Supabase"}), 500

            # Obtener URL pública
            photo_url = supabase.storage.from_("fotos_admin").get_public_url(file_name)

            # Actualizar la tabla administrador
            update_response = (
                supabase.table("administrador")
                .update({"foto": photo_url})
                .eq("id", cedula)
                .execute()
            )

            if update_response.data:
                return jsonify({"success": True, "photo_url": photo_url}), 200
            else:
                return jsonify({"success": False, "msg": "No se pudo guardar la foto"}), 500

        # ❌ ELIMINAR FOTO
        elif request.method == 'DELETE':
            response = (
                supabase.table("administrador")
                .select("foto")
                .eq("id", cedula)
                .execute()
            )

            if response.data and response.data[0].get("foto"):
                foto_url = response.data[0]["foto"]
                file_name = foto_url.split("/")[-1]
                supabase.storage.from_("fotos_admin").remove([file_name])

            supabase.table("administrador").update({"foto": None}).eq("id", cedula).execute()

            default_url = url_for("static", filename="image/default.png")
            return jsonify({"success": True, "photo_url": default_url}), 200

    except Exception as e:
        print("❌ Error en Ad_Ceditar_foto:", e)
        return jsonify({"success": False, "msg": "Error en el servidor"}), 500
    
@app.route("/enviar_token_recuperacion", methods=["POST"])
def enviar_token_recuperacion():
    try:
        data = request.get_json()
        telefono = data.get("telefono", "").strip()

        if not telefono:
            return jsonify({"success": False, "msg": "Debe ingresar un número de teléfono."}), 400

        # 🔹 Limpiar duplicados de prefijo (+57 o 57)
        telefono = telefono.replace(" ", "")
        if telefono.startswith("+57"):
            telefono = telefono[3:]
        elif telefono.startswith("57"):
            telefono = telefono[2:]

        # 🔹 Validar longitud y formato
        if not telefono.isdigit() or len(telefono) != 10:
            return jsonify({"success": False, "msg": "El número de teléfono no es válido (debe tener 10 dígitos)."}), 400

        # 🔹 Crear cliente Twilio
        client = Client(TWILIO_SID, TWILIO_AUTH)

        # 🔹 Enviar el código
        verification = client.verify.v2.services(VERIFY_SID).verifications.create(
            to=f"+57{telefono}",
            channel="sms"
        )

        print(f"✅ Token enviado a +57{telefono}")
        return jsonify({"success": True, "msg": "Código enviado correctamente."})

    except Exception as e:
        print(f"❌ Error en enviar_token_recuperacion: {e}")
        return jsonify({"success": False, "msg": str(e)}), 500


@app.route("/validar_token", methods=["POST"])
def validar_token():
    try:
        data = request.get_json()
        nombre = data.get("nombre")
        telefono = data.get("telefono")
        token = data.get("token")
        nueva_contrasena = data.get("nueva_clave")


        if not (telefono and token and nueva_contrasena):
            return jsonify({"success": False, "msg": "Todos los campos son obligatorios."}), 400

        client = Client(TWILIO_SID, TWILIO_AUTH)
        verfification_check = client.verify.v2.services(VERIFY_SID).verification_checks.create(
            to=f"+57{telefono}",
            code=token
        )

        if verfification_check.status != "approved":
            return jsonify({"success": False, "msg": "Código inválido o expirado."}), 400
        
        hashed_password = generate_password_hash(nueva_contrasena)
        supabase.table("administrador").update(
            {"contrasena": hashed_password}
        ).eq("nombre", nombre).execute()

        return jsonify({"success": True, "msg": "Contraseña actualizada correctamente."})
    
    except Exception as e:
        print(f"❌ Error en validar_token: {e}")
        return jsonify({"success": False, "msg": str(e)}), 500

# ╔══════════════════════════════════════════════╗
# ║ Rutas de Empleado                            ║
# ╚══════════════════════════════════════════════╝

@app.route('/Em_Inicio', methods=['GET', 'POST'])
@login_requerido(rol='Empleado')
def Em_Inicio():
    response = make_response(render_template("Em_templates/Em_Inicio.html"))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response


# ╔══════════════════════════════════════════════╗
# ║ Registro de Pedidos para EMPLEADO            ║
# ╚══════════════════════════════════════════════╝

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

        # Crear registros en inventario
        inventarios = []
        for prod in productos:
            id_producto = prod.get("Id_Producto")
            cantidad = prod.get("Cantidad")
            fecha_ingreso = prod.get("Fecha_Ingreso")
            fecha_caducidad = prod.get("Fecha_Caducidad")

            if not (id_producto and cantidad and fecha_ingreso and fecha_caducidad):
                continue

            # 👇 Convertimos a int o string según el tamaño
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

        # Crear el pedido (usa el primer inventario)
        pedido = supabase.table("pedido").insert({
            "id_inventario": inventarios[0],
            "cedula": session.get("cedula")
        }).execute()

        if not pedido.data:
            return jsonify({"success": False, "msg": "No se pudo registrar el pedido"}), 500

        id_pedido = pedido.data[0]["id_pedido"]

        # Insertar detalles del pedido
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

        # Los empleados solo ven productos HABILITADOS
        query = supabase.table("productos").select("id_producto, nombre, categoria, unidad, foto").eq("habilitado", True)

        if termino:
            query = query.or_(f"nombre.ilike.%{termino}%,categoria.ilike.%{termino}%")

        result = query.order("nombre").execute()
        productos = result.data or []

        # Si hay imagen, ya viene en texto base64 o URL
        for prod in productos:
            if not prod.get("foto"):
                prod["foto"] = "/static/image/default.png"

        return jsonify({"success": True, "productos": productos})
    except Exception as e:
        print("❌ Error en búsqueda de producto (empleado):", e)
        return jsonify({"success": False, "msg": "Error al obtener productos"}), 500
    

# ╔══════════════════════════════════════════════╗
# ║ Recibir pedidos                              ║
# ╚══════════════════════════════════════════════╝

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

            # Validación
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

            # 🔹 Buscar el inventario que corresponde al producto y al local
            inv_res = supabase.table("inventario")\
                .select("*")\
                .eq("id_local", session.get("branch"))\
                .eq("id_producto", id_producto)\
                .execute()

            inventarios = inv_res.data or []
            if not inventarios:
                return jsonify({"success": False, "msg": "No existe inventario previo para este producto."}), 400

            inventario_id = inventarios[0]["id_inventario"]

            # 🔹 Actualizar el registro existente
            try:
                supabase.table("inventario").update({
                    "cantidad": cantidad,                          # cantidad recibida
                    "fecha_ingreso": hoy.isoformat(),              # actualizar fecha de ingreso al día de recepción
                    "fecha_caducidad": fecha_cad_dt.isoformat()   # fecha de caducidad recibida
                }).eq("id_inventario", inventario_id).execute()
            except Exception as e:
                return jsonify({"success": False, "msg": f"Error al actualizar inventario: {e}"}), 500


            return jsonify({"success": True, "msg": "Producto confirmado correctamente."})

        # GET: mostrar pedidos
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

        # Actualizar estado en Supabase
        supabase.table("pedido").update({"estado": "Recibido"})\
            .eq("id_pedido", id_pedido).execute()

        # Como la base ya actualizó, solo devolvemos éxito
        return jsonify({"success": True, "msg": "Pedido actualizado correctamente."})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "msg": str(e)}), 500

# ╔══════════════════════════════════════════════╗
# ║ Historial de pedidos                         ║
# ╚══════════════════════════════════════════════╝

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

        query = supabase.table("pedido") \
            .select("id_pedido, estado, fecha_pedido, detalle_pedido(id_producto, cantidad, productos(nombre, categoria, unidad))") \
            .eq("estado", "Recibido") \
            .order("fecha_pedido", desc=True)

        pedidos = query.execute().data or []

        # 🔹 Filtro en servidor
        if any(filtros.values()):
            pedidos_filtrados = []
            for pedido in pedidos:
                detalles_filtrados = []
                for detalle in pedido["detalle_pedido"]:
                    if (
                        (not filtros["categoria"] or filtros["categoria"].lower() in detalle["productos"]["categoria"].lower()) and
                        (not filtros["producto"] or filtros["producto"].lower() in detalle["productos"]["nombre"].lower()) and
                        (not filtros["unidad"] or filtros["unidad"].lower() in detalle["productos"]["unidad"].lower()) and
                        (not filtros["cantidad"] or str(detalle["cantidad"]) == filtros["cantidad"]) and
                        (not filtros["fecha"] or filtros["fecha"] == (pedido["fecha_pedido"] or "").split("T")[0])
                    ):
                        detalles_filtrados.append(detalle)
                if detalles_filtrados:
                    pedido["detalle_pedido"] = detalles_filtrados
                    pedidos_filtrados.append(pedido)
            pedidos = pedidos_filtrados

        return render_template("Em_templates/Em_Hordenes.html", pedidos=pedidos)

    except Exception as e:
        print("❌ Error al cargar historial de órdenes:", e)
        return render_template("Em_templates/Em_Hordenes.html", pedidos=[])


# ╔══════════════════════════════════════════════╗
# ║ Edición de Datos del Empleado                ║
# ╚══════════════════════════════════════════════╝

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

            update_response = (
                supabase.table("empleados")
                .update({"nombre": nombre})
                .eq("cedula", cedula)
                .execute()
            )

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

            # Create unique filename and read bytes
            file_name = f"empleado_{cedula}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
            file_bytes = foto.read()

            # Upload to Supabase bucket
            upload_response = supabase.storage.from_("Fotos").upload(file_name, file_bytes)

            if hasattr(upload_response, "error") and upload_response.error:
                return jsonify({"success": False, "msg": "Error al subir la foto a Supabase"}), 500

            # Get public URL
            photo_url = supabase.storage.from_("Fotos").get_public_url(file_name)

            # Update empleados table
            update_response = (
                supabase.table("empleados")
                .update({"foto": photo_url})
                .eq("cedula", cedula)
                .execute()
            )

            if update_response.data:
                return jsonify({"success": True, "photo_url": photo_url}), 200
            else:
                return jsonify({"success": False, "msg": "No se pudo guardar la foto"}), 500

        elif request.method == 'DELETE':
            # Get current photo URL
            response = (
                supabase.table("empleados")
                .select("foto")
                .eq("cedula", cedula)
                .execute()
            )

            if response.data and response.data[0].get("foto"):
                foto_url = response.data[0]["foto"]
                file_name = foto_url.split("/")[-1]
                # Delete from storage
                supabase.storage.from_("Fotos").remove([file_name])

            # Set photo to null in database
            supabase.table("empleados").update({"foto": None}).eq("cedula", cedula).execute()

            default_url = url_for("static", filename="image/default.png")
            return jsonify({"success": True, "photo_url": default_url}), 200

    except Exception as e:
        print("❌ Error en Em_Ceditar_foto:", e)
        return jsonify({"success": False, "msg": str(e)}), 500


# ╔══════════════════════════════════════════════╗
# ║ Recuperación de contraseña Empleado (Twilio) ║
# ╚══════════════════════════════════════════════╝

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

        # 🔹 Normalizar teléfono
        if telefono.startswith("+57"):
            telefono = telefono[3:]
        elif telefono.startswith("57"):
            telefono = telefono[2:]

        # 🔹 Verificar token con Twilio
        client = Client(TWILIO_SID, TWILIO_AUTH)
        verification_check = client.verify.v2.services(VERIFY_SID).verification_checks.create(
            to=f"+57{telefono}",
            code=token
        )

        if verification_check.status != "approved":
            return jsonify({"success": False, "msg": "Código inválido o expirado."}), 400

        # 🔹 Buscar empleado por nombre y teléfono
        empleado_resp = supabase.table("empleados").select("*")\
            .eq("nombre", nombre)\
            .eq("telefono", telefono)\
            .execute()

        if not empleado_resp.data:
            return jsonify({"success": False, "msg": "Empleado no encontrado."}), 404

        cedula = empleado_resp.data[0]["cedula"]
        print("🆔 Cedula encontrada:", cedula)

        # 🔹 Generar hash
        hashed_password = generate_password_hash(nueva_contrasena)
        print("🔒 Hash generado:", hashed_password)

        # 🔹 Actualizar contraseña
        update_resp = supabase.table("empleados").update(
            {"contrasena": hashed_password}
        ).match({"cedula": cedula}).execute()

        print("📤 Respuesta update:", update_resp)

        if not update_resp.data:
            return jsonify({"success": False, "msg": "No se actualizó ninguna fila. Verifique el filtro."}), 400

        return jsonify({"success": True, "msg": "Contraseña actualizada correctamente."})


    except Exception as e:
        print(f"❌ Error en Em_validar_token: {e}")
        return jsonify({"success": False, "msg": str(e)}), 500


# ╔══════════════════════════════════════════════╗
# ║ Cierre de Sesión                             ║
# ╚══════════════════════════════════════════════╝

@app.route('/logout')
def logout():
    # Clear all session data
    session.clear()
    
    # Redirect to login with cache prevention headers
    response = redirect(url_for('login'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
