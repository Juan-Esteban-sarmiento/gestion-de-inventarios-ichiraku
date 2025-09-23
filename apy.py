import os
import base64
from flask import Flask, flash, jsonify, render_template, request, redirect, url_for, session, make_response
from db import add_empleado, get_db_connection
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = '123456789'
app.config['JSON_AS_ASCII'] = False
UPLOAD_FOLDER = 'static/uploads/empleados'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


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
            ADMIN_USER = "admin"
            ADMIN_PASS = "admin123"
            if usuario == ADMIN_USER and password == ADMIN_PASS:
                session['logged_in'] = True
                session['role'] = 'Administrador'
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

    
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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


@app.route('/Ad_Rproductos', methods=['GET', 'POST'])
def Ad_Rproductos():
    return render_template("Ad_templates/Ad_Rproductos.html")

@app.route('/Ad_Dinformes', methods=['GET', 'POST'])
def Ad_Dinformes():
    return render_template("Ad_templates/Ad_Dinformes.html")

@app.route('/Ad_Rlocales', methods=['GET', 'POST'])
def Ad_Rlocales():
    return render_template("Ad_templates/Ad_Rlocales.html")

@app.route('/Ad_Pnotificaciones', methods=['GET', 'POST'])
def Ad_Pnotificaciones():
    return render_template("Ad_templates/Ad_Pnotificaciones.html")

@app.route('/Ad_Ceditar', methods=['GET'])
def Ad_Ceditar():
    if not session.get('logged_in') or session.get('role') != 'Administrador':
        return redirect(url_for('login'))

    # Datos fijos del administrador
    user = {
        "Cedula": "0001",
        "Nombre": "admin",
        "Contrasena": "admin123"
    }

    return render_template("Ad_templates/Ad_Ceditar.html", user=user)

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

