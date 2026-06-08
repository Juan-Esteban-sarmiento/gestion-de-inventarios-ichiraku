from flask import render_template, request, jsonify, redirect, url_for, session, make_response, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import re
import math
from io import BytesIO
import csv

from extensions import app, supabase, logger, generate_master_key, is_valid_image, SUPABASE_URL
from utils import login_requerido, generar_notificaciones_stock_bajo, eliminar_notificaciones_caducadas
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
        response = supabase.table("recetarios").select("*").order("id_receta", desc=False).execute()
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
                print(f"DEBUG registrar_receta: Ingrediente {detalle_data['id_producto']} -> Cantidad: {detalle_data['cantidad']}, Unidad: {detalle_data['unidad']}")
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
