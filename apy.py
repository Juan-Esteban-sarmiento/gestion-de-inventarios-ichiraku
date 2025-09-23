import os
import base64
from flask import Flask, flash, jsonify, render_template, request, redirect, url_for, session, make_response
from db import add_empleado, get_db_connection

app = Flask(__name__)
app.secret_key = '123456789'


#redirecion inicial de logueo


@app.route('/')
def index():
    return redirect(url_for('login'))

#configuiracion de logueo, cierre de sesion y rutas de administrador

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        usuario = data.get('id')
        password = data.get('password')
        role = data.get('role')
        branch = data.get('branch')

        if role == "Administrador":
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            # Cambia los nombres de columna según tu tabla 'administrador'
            cursor.execute(
                "SELECT * FROM administrador WHERE ID=%s AND Contrasena=%s",
                (usuario, password)
            )
            admin_user = cursor.fetchone()
            cursor.close()
            conn.close()

            if admin_user:
                session['logged_in'] = True
                session['role'] = 'Administrador'
                session['cedula'] = admin_user.get('ID', usuario)
                session['nombre'] = admin_user.get('Nombre', '')
                return jsonify({"success": True, "redirect": url_for('Ad_Inicio')})
            else:
                return jsonify({"success": False, "msg": "Usuario o contraseña de administrador incorrectos"})

        elif role == "Empleado":
            if not branch:
                return jsonify({"success": False, "msg": "Por favor selecciona una sucursal."})
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT * FROM empleados WHERE Cedula=%s AND Contrasena=%s",
                (usuario, password)
            )
            user = cursor.fetchone()
            cursor.close()
            conn.close()

            if user:
                session['logged_in'] = True
                session["cedula"] = user["Cedula"]
                session['role'] = 'Empleado'
                return jsonify({
                    "success": True,
                    "msg": "Bienvenido, has iniciado sesión correctamente",
                    "redirect": url_for('Em_Inicio')
                })
            else:
                return jsonify({"success": False, "msg": "Usuario o contraseña incorrectos"})


    return render_template("login.html")

# Rutas de administrador con control de sesión y caché deshabilitada

@app.route('/Ad_Inicio', methods=['GET', 'POST'])
def Ad_Inicio():
    if not session.get('logged_in') or session.get('role') != 'Administrador':
        return redirect(url_for('login'))
    response = make_response(render_template("Ad_templates/Ad_Inicio.html"))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

@app.route('/Ad_Rempleados', methods=['GET', 'POST'])
def Ad_Rempleados():
    return render_template("Ad_templates/Ad_Rempleados.html"), 200, {"Content-Type": "text/html; charset=utf-8"}


@app.route('/registrar_empleado', methods=['POST'])
def registrar_empleado():
    nombre = request.form.get('nombre')
    cedula = request.form.get('cedula')
    contrasena = request.form.get('contrasena')
    contacto = request.form.get('contacto')
    foto = request.files.get('foto')

    if not (nombre and cedula and contrasena and contacto):
        return jsonify({"success": False, "msg": "Todos los campos son obligatorios."})

    foto_binaria = None
    if foto:
        foto_binaria = foto.read()  # leemos archivo como binario

    try:
        add_empleado(cedula, nombre, contacto, contrasena, foto_binaria)
        return jsonify({"success": True, "msg": "Empleado registrado correctamente."})
    except Exception as e:
        print("Error al registrar:", e)
        return jsonify({"success": False, "msg": f"Error al registrar: {str(e)}"})

    

 #busqueda de empleado

@app.route("/buscar_empleado", methods=["POST"])
def buscar_empleado():
    data = request.get_json()
    termino = data.get("termino")

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT Cedula, Nombre, Numero_contacto, Foto
            FROM empleados
            WHERE Cedula LIKE %s OR Nombre LIKE %s
        """
        like_pattern = f"%{termino}%"
        cursor.execute(query, (like_pattern, like_pattern))

        empleados = cursor.fetchall()
        cursor.close()
        conn.close()

        # Convertir binario a Base64
        for emp in empleados:
            if emp["Foto"]:
                emp["Foto"] = f"data:image/jpeg;base64,{base64.b64encode(emp['Foto']).decode('utf-8')}"
            else:
                emp["Foto"] = None

        if empleados:
            return jsonify({"success": True, "empleados": empleados})
        else:
            return jsonify({"success": False, "msg": "Empleado no encontrado"})
    
    except Exception as e:
        print("Error en búsqueda:", e)
        return jsonify({"success": False, "msg": "Error en servidor"})

    
@app.route("/eliminar_empleado/<cedula>", methods=["DELETE"])
def eliminar_empleado(cedula):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Verifica que exista
        cursor.execute("SELECT * FROM empleados WHERE Cedula = %s", (cedula,))
        emp = cursor.fetchone()

        if not emp:
            cursor.close()
            conn.close()
            return jsonify({"success": False, "msg": "Empleado no encontrado"}), 404

        # Eliminar
        cursor.execute("DELETE FROM empleados WHERE Cedula = %s", (cedula,))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"success": True, "msg": "Empleado eliminado correctamente."}), 200

    except Exception as e:
        print("Error al eliminar empleado:", e)
        return jsonify({"success": False, "msg": "Error en el servidor"}), 500


# Registrar producto

@app.route('/Ad_Rproductos', methods=['GET', 'POST'])
def Ad_Rproductos():
    return render_template("Ad_templates/Ad_Rproductos.html")

@app.route('/registrar_producto', methods=['POST'])
def registrar_producto():
    nombre = request.form.get('nombre')
    categoria = request.form.get('categoria')
    unidad = request.form.get('unidad')
    serial = request.form.get('serial')
    try:
        serial_int = int(serial)
        if serial_int <= 0 or serial_int == 2147483647:
            return jsonify({"success": False, "msg": "El ID del producto no puede ser 0 ni 2147483647."})
    except Exception:
        return jsonify({"success": False, "msg": "El ID del producto debe ser un número válido."})

    # Verificar si el ID ya existe
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT Id_Producto FROM productos WHERE Id_Producto = %s", (serial_int,))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({"success": False, "msg": "Ya existe un producto con ese ID."})
    cursor.close()
    conn.close()
    foto = request.files.get('foto')

    if not (nombre and categoria and unidad and serial and foto):
        return jsonify({"success": False, "msg": "Todos los campos son obligatorios, incluyendo la foto."})

    foto_binaria = foto.read() if foto else None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = """
            INSERT INTO productos (Id_Producto, Nombre, Categoria, Unidad, Foto)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(query, (serial, nombre, categoria, unidad, foto_binaria))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "msg": "Producto registrado correctamente."})
    except Exception as e:
        print("Error al registrar producto:", e)
        if "Duplicate entry" in str(e):
            return jsonify({"success": False, "msg": "Ya existe un producto con ese ID."})
        return jsonify({"success": False, "msg": f"Error al registrar: {str(e)}"})
    
# Eliminar producto
@app.route("/eliminar_producto/<id_producto>", methods=["DELETE"])
def eliminar_producto(id_producto):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM productos WHERE Id_Producto = %s", (id_producto,))
        prod = cursor.fetchone()
        if not prod:
            cursor.close()
            conn.close()
            return jsonify({"success": False, "msg": "Producto no encontrado"}), 404
        cursor.execute("DELETE FROM productos WHERE Id_Producto = %s", (id_producto,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "msg": "Producto eliminado correctamente."}), 200
    except Exception as e:
        print("Error al eliminar producto:", e)
        return jsonify({"success": False, "msg": "Error en el servidor"}), 500
    

# Busqueda de producto
@app.route("/buscar_producto", methods=["POST"])
def buscar_producto():
    data = request.get_json()
    termino = data.get("termino")

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT Id_Producto, Nombre, Categoria, Unidad, Foto
            FROM productos
            WHERE Id_Producto LIKE %s OR Nombre LIKE %s
        """
        like_pattern = f"%{termino}%"
        cursor.execute(query, (like_pattern, like_pattern))

        productos = cursor.fetchall()
        cursor.close()
        conn.close()

        # Convertir binario a Base64
        for prod in productos:
            if prod["Foto"]:
                prod["Foto"] = f"data:image/jpeg;base64,{base64.b64encode(prod['Foto']).decode('utf-8')}"
            else:
                prod["Foto"] = None

        if productos:
            return jsonify({"success": True, "productos": productos})
        else:
            return jsonify({"success": False, "msg": "Producto no encontrado"})
    except Exception as e:
        print("Error en búsqueda de producto:", e)
        return jsonify({"success": False, "msg": "Error en servidor"})

@app.route('/Ad_Dinformes', methods=['GET', 'POST'])
def Ad_Dinformes():
    return render_template("Ad_templates/Ad_Dinformes.html")

@app.route('/Ad_Rlocales', methods=['GET', 'POST'])
def Ad_Rlocales():
    return render_template("Ad_templates/Ad_Rlocales.html")

@app.route('/Ad_Pnotificaciones', methods=['GET', 'POST'])
def Ad_Pnotificaciones():
    return render_template("Ad_templates/Ad_Pnotificaciones.html")


# Edicion de administrador: GET muestra datos, POST actualiza, foto POST/DELETE
@app.route('/Ad_Ceditar', methods=['GET', 'POST'])
def Ad_Ceditar():
    if not session.get('logged_in') or session.get('role') != 'Administrador':
        return redirect(url_for('login'))

    cedula = session.get('cedula')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM administrador WHERE ID = %s", (cedula,))
    admin = cursor.fetchone()

    # GET normal
    if request.method == 'GET':
        photo_url = None
        if admin and admin.get('Foto'):
            photo_url = f"data:image/jpeg;base64,{base64.b64encode(admin['Foto']).decode('utf-8')}"
        return render_template("Ad_templates/Ad_Ceditar.html", user={
            "Cedula": admin.get('ID', ''),
            "Nombre": admin.get('Nombre', ''),
            "Contrasena": admin.get('Contrasena', ''),
            "photo_url": photo_url
        })

    # POST actualiza datos
    if request.method == 'POST' and request.is_json:
        try:
            data = request.get_json()
            nombre = data.get("Nombre")
            contrasena = data.get("Contrasena")
            cursor.execute("""
                UPDATE administrador SET Nombre = %s, Contrasena = %s WHERE ID = %s
            """, (nombre, contrasena, cedula))
            conn.commit()
            return jsonify({"success": True, "msg": "Usuario actualizado correctamente"}), 200
        except Exception as e:
            print("Error update admin:", e)
            return jsonify({"success": False, "msg": "Error en servidor"}), 500
        finally:
            cursor.close()
            conn.close()

    cursor.close()
    conn.close()
    return redirect(url_for('Ad_Ceditar'))

# Subir o eliminar foto de administrador
@app.route('/Ad_Ceditar_foto', methods=['POST', 'DELETE'])
def Ad_Ceditar_foto():
    if not session.get('logged_in') or session.get('role') != 'Administrador':
        return jsonify({"success": False, "msg": "No autorizado"}), 401
    cedula = session.get('cedula')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    if request.method == 'POST':
        foto = request.files.get('foto')
        if not foto:
            return jsonify({"success": False, "msg": "No se envio foto"})
        foto_binaria = foto.read()
        cursor.execute("UPDATE administrador SET Foto = %s WHERE ID = %s", (foto_binaria, cedula))
        conn.commit()
        photo_url = f"data:image/jpeg;base64,{base64.b64encode(foto_binaria).decode('utf-8')}"
        cursor.close()
        conn.close()
        return jsonify({"success": True, "photo_url": photo_url})
    elif request.method == 'DELETE':
        cursor.execute("UPDATE administrador SET Foto = NULL WHERE ID = %s", (cedula,))
        conn.commit()
        cursor.close()
        conn.close()
        default_url = url_for('static', filename='image/default.png')
        return jsonify({"success": True, "photo_url": default_url})

#rutas de empleado con control de sesión y caché deshabilitada

@app.route('/Em_Inicio', methods=['GET', 'POST'])
def Em_Inicio():
    if not session.get('logged_in') or session.get('role') != 'Empleado':
        return redirect(url_for('login'))
    response = make_response(render_template("Em_templates/Em_Inicio.html"))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response


@app.route("/Em_Ceditar", methods=["GET", "POST"])
def Em_Ceditar():
    if not session.get('logged_in'):
        if request.is_json:
            return jsonify({"success": False, "msg": "Sesión expirada, inicia sesión de nuevo"}), 401
        return redirect(url_for('login'))

    cedula = session.get("cedula")
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM empleados WHERE Cedula = %s", (cedula,))
    empleado = cursor.fetchone()

    if not empleado:
        cursor.close()
        conn.close()
        if request.is_json:
            return jsonify({"success": False, "msg": "Empleado no encontrado"}), 404
        return redirect(url_for("Em_Inicio"))

    # 🚀 POST (AJAX JSON)
    if request.method == "POST" and request.is_json:
        try:
            data = request.get_json()
            nombre = data.get("Nombre")
            numero_contacto = data.get("Numero_contacto")
            contrasena = data.get("Contrasena")

            cursor.execute("""
                UPDATE empleados
                SET Nombre = %s, Numero_contacto = %s, Contrasena = %s
                WHERE Cedula = %s
            """, (nombre, numero_contacto, contrasena, cedula))
            conn.commit()

            respuesta = {"success": True, "msg": "Usuario actualizado correctamente"}
            print("🔎 Enviando JSON:", respuesta)  # 👈 Log de lo que se manda
            return jsonify(respuesta), 200

        except Exception as e:
            print("❌ Error en update:", e)
            return jsonify({"success": False, "msg": "Error en servidor"}), 500

        finally:
            cursor.close()
            conn.close()

    # 🚀 GET normal
    cursor.close()
    conn.close()
    return render_template("Em_templates/Em_Ceditar.html", user=empleado)


#configuracion de cierre de sesion

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

#Apartao para que el empleado revice las ordenes
@app.route('/Em_Rordenes', methods=['GET', 'POST'])
def Em_Rordenes():
    return render_template("Em_templates/Em_Rordenes.html")

@app.route('/Em_Rpedido', methods=['GET', 'POST'])
def Em_Rpedido():
    return render_template("Em_templates/Em_Rpedido.html")

@app.route('/Em_Hordenes', methods=['GET', 'POST'])
def Em_Hordenes():
    return render_template("Em_templates/Em_Hordenes.html")

if __name__ == '__main__':
    app.run(debug=True)

