from flask import Flask, jsonify, render_template, request, redirect, url_for, session, make_response
from db import get_db_connection

app = Flask(__name__)
app.secret_key = '123456789'

#redirecion inicial de logueo

<<<<<<< HEAD
=======

>>>>>>> 5d73856224571430728bedbedc683153a6a0019a
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
                session['role'] = 'Empleado'
                return jsonify({"success": True, "msg": "Bienvenido, has iniciado sesión correctamente"})
            else:
                return jsonify({"success": False, "msg": "Usuario o contraseña incorrectos"})

    return render_template("login.html")

# Rutas de administrador con control de sesión y caché deshabilitada

@app.route('/Ad_Inicio', methods=['GET', 'POST'])
def Ad_Inicio():
    if not session.get('logged_in') or session.get('role') != 'Administrador':
        return redirect(url_for('login'))
    response = make_response(render_template("Ad_Inicio.html"))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

@app.route('/Ad_Rempleados', methods=['GET', 'POST'])
def Ad_Rempleados():
    return render_template("Ad_Rempleados.html")

@app.route('/registrar_empleado', methods=['POST'])
def registrar_empleado():
    data = request.get_json()
    nombre = data.get('nombre')
    cedula = data.get('cedula')
    contrasena = data.get('contrasena')
    contacto = data.get('contacto')

    if not (nombre and cedula and contrasena and contacto):
        return jsonify({"success": False, "msg": "Todos los campos son obligatorios."})

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO empleados (Cedula, Nombre, Numero_contacto, Contrasena, Foto) VALUES (%s, %s, %s, %s, %s)",
            (cedula, nombre, contacto, contrasena, None)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "msg": "Empleado registrado correctamente."})
    except Exception as e:
        return jsonify({"success": False, "msg": f"Error al registrar: {str(e)}"})

 #busqueda de empleado

@app.route("/buscar_empleado", methods=["POST"])
def buscar_empleado():
    data = request.get_json()
    termino = data.get("termino")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT Cedula, Nombre, Numero_contacto, Foto FROM empleados WHERE Cedula = %s OR Nombre LIKE %s",
        (termino, f"%{termino}%")
    )
    empleado = cursor.fetchone()

    cursor.close()
    conn.close()

    if empleado:
        return jsonify({"success": True, "empleado": empleado})
    else:
        return jsonify({"success": False, "msg": "Empleado no encontrado"})




@app.route('/Ad_Rproductos', methods=['GET', 'POST'])
def Ad_Rproductos():
    return render_template("Ad_Rproductos.html")

@app.route('/Ad_Dinformes', methods=['GET', 'POST'])
def Ad_Dinformes():
    return render_template("Ad_Dinformes.html")

@app.route('/Ad_Rlocales', methods=['GET', 'POST'])
def Ad_Rlocales():
    return render_template("Ad_Rlocales.html")

@app.route('/Ad_Pnotificaciones', methods=['GET', 'POST'])
def Ad_Pnotificaciones():
    return render_template("Ad_Pnotificaciones.html")


#rutas de empleado con control de sesión y caché deshabilitada

@app.route('/Em_Inicio', methods=['GET', 'POST'])
def Em_Inicio():
    if not session.get('logged_in') or session.get('role') != 'Empleado':
        return redirect(url_for('login'))
    response = make_response(render_template("Em_Inicio.html"))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

@app.route('/Ad_Rempleados', methods=['GET', 'POST'])
def Ad_Rempleados():
    return render_template("Ad_Rempleados.html")

@app.route('/Ad_Rproductos', methods=['GET', 'POST'])
def Ad_Rproductos():
    return render_template("Ad_Rproductos.html")

@app.route('/Ad_Dinformes', methods=['GET', 'POST'])
def Ad_Dinformes():
    return render_template("Ad_Dinformes.html")

@app.route('/Ad_Rlocales', methods=['GET', 'POST'])
def Ad_Rlocales():
    return render_template("Ad_Rlocales.html")

@app.route('/Ad_Pnotificaciones', methods=['GET', 'POST'])
def Ad_Pnotificaciones():
    return render_template("Ad_Pnotificaciones.html")

@app.route('/Ad_Ceditar', methods=['GET', 'POST'])
def Ad_Ceditar():
    return render_template("Ad_Ceditar.html")


#configuracion de cierre de sesion

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
app.run(debug=True)