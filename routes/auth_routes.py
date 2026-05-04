from flask import render_template, request, jsonify, redirect, url_for, session, make_response, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import re
import math
from io import BytesIO
import csv

from extensions import app, supabase, logger, generate_master_key, is_valid_image, assign_session_token, is_valid_session, revoke_session_token
from utils import login_requerido
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
                print(f"DEBUG: Hash recibido para admin {usuario}: '{admin_user.get('contrasena')}'")
                
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
                    "photo_url": photo_url
                }
            )

        if request.method == "POST" and request.is_json:
            data = request.get_json()
            nombre = data.get("Nombre")
            telefono = data.get("telefono", "").strip()
            
            if not nombre:
                return jsonify({"success": False, "msg": "El nombre es obligatorio."}), 400
            
            update_data = {"nombre": nombre}
            if telefono:
                update_data["telefono"] = telefono
                
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

        if len(nueva_clave) < 8:
            return jsonify({"success": False, "msg": "La nueva clave debe tener al menos 8 caracteres."}), 400

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
                    "photo_url": photo_url
                }
            )

        if request.method == "POST" and request.is_json:
            data = request.get_json()
            nombre = data.get("Nombre")
            
            if not nombre:
                return jsonify({"success": False, "msg": "El nombre es obligatorio."}), 400
            
            update_data = {"nombre": nombre}
                
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

# ==============================================================================
