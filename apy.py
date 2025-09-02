from flask import Flask, jsonify, render_template, request, redirect, url_for, session
from flask import make_response
from db import get_db_connection

app = Flask(__name__)
app.secret_key = '123456789'  
from flask import Flask, jsonify, render_template, request, redirect, url_for, session
from flask import make_response
from db import get_db_connection

app = Flask(__name__)
app.secret_key = '123456789'  


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
                # Aquí puedes poner un redirect diferente si lo necesitas
                return jsonify({"success": True, "msg": "Bienvenido, has iniciado sesión correctamente"})
            else:
                return jsonify({"success": False, "msg": "Usuario o contraseña incorrectos"})

    return render_template("login.html")

@app.route('/Ad_Inicio', methods=['GET', 'POST'])
def Ad_Inicio():
    if not session.get('logged_in') or session.get('role') != 'Administrador':
        return redirect(url_for('login'))
    response = make_response(render_template("Ad_Inicio.html"))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response
    if request.method == 'POST':
        return "Acción de administrador ejecutada"
    return render_template("Ad_Inicio.html")

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)

#EMPLEADO INICIO
@app.route('/')
def index():
    return redirect(url_for('Em_Inicio'))

# Vista login
@app.route('/Em_Inicio', methods=['GET', 'POST'])
def Em_Inicio():
    if request.method == 'POST':
        usuario = request.form['usuario']
        password = request.form['password']

        # Ejemplo simple de validación
        if usuario == "admin" and password == "1234":
            return "✅ Bienvenido, has iniciado sesión correctamente"
        else:
            return "❌ Usuario o contraseña incorrectos"
    return render_template("Em_Inicio.html")

if __name__ == '__main__':
    app.run(debug=True)

#Administrador Registro Empleados
@app.route('/')
def index():
    return redirect(url_for('Ad_Rempleados'))

# Vista login
@app.route('/Ad_Rempleados', methods=['GET', 'POST'])
def Ad_Rempleados():
    if request.method == 'POST':
        usuario = request.form['usuario']
        password = request.form['password']

        # Ejemplo simple de validación
        if usuario == "admin" and password == "1234":
            return "✅ Bienvenido, has iniciado sesión correctamente"
        else:
            return "❌ Usuario o contraseña incorrectos"
    return render_template("Ad_Rempleados.html")

if __name__ == '__main__':
    app.run(debug=True)

#Administrador Registro Productos
@app.route('/')
def index():
    return redirect(url_for('Ad_Rproductos'))

# Vista login
@app.route('/Ad_Rproductos', methods=['GET', 'POST'])
def Ad_Rproductos():
    if request.method == 'POST':
        usuario = request.form['usuario']
        password = request.form['password']

        # Ejemplo simple de validación
        if usuario == "admin" and password == "1234":
            return "✅ Bienvenido, has iniciado sesión correctamente"
        else:
            return "❌ Usuario o contraseña incorrectos"
    return render_template("Ad_Rproductos.html")

if __name__ == '__main__':
    app.run(debug=True)

#Administrador Descargar Informes
@app.route('/')
def index():
    return redirect(url_for('Ad_Dinformes'))

# Vista login
@app.route('/Ad_Dinformes', methods=['GET', 'POST'])
def Ad_Dinformes():
    if request.method == 'POST':
        usuario = request.form['usuario']
        password = request.form['password']

        # Ejemplo simple de validación
        if usuario == "admin" and password == "1234":
            return "✅ Bienvenido, has iniciado sesión correctamente"
        else:
            return "❌ Usuario o contraseña incorrectos"
    return render_template("Ad_Dinformes.html")

if __name__ == '__main__':
    app.run(debug=True)

# Administrador Registro de locales
@app.route('/')
def index():
    return redirect(url_for('Ad_Rlocales'))

# Vista login
@app.route('/Ad_Rlocales', methods=['GET', 'POST'])
def Ad_Rlocales():
    if request.method == 'POST':
        usuario = request.form['usuario']
        password = request.form['password']

        # Ejemplo simple de validación
        if usuario == "admin" and password == "1234":
            return "✅ Bienvenido, has iniciado sesión correctamente"
        else:
            return "❌ Usuario o contraseña incorrectos"
    return render_template("Ad_Rlocales.html")

if __name__ == '__main__':
    app.run(debug=True)

# Administrador panel notificaciones
@app.route('/')
def index():
    return redirect(url_for('Ad_Pnotificaciones'))

# Vista login
@app.route('/Ad_Pnotificaciones', methods=['GET', 'POST'])
def Ad_Pnotificaciones():
    if request.method == 'POST':
        usuario = request.form['usuario']
        password = request.form['password']

        # Ejemplo simple de validación
        if usuario == "admin" and password == "1234":
            return "✅ Bienvenido, has iniciado sesión correctamente"
        else:
            return "❌ Usuario o contraseña incorrectos"
    return render_template("Ad_Pnotificaciones.html")

if __name__ == '__main__':
    app.run(debug=True)

# Administrador cuenta editar
@app.route('/')
def index():
    return redirect(url_for('Ad_Ceditar'))

# Vista login
@app.route('/Ad_Ceditar', methods=['GET', 'POST'])
def Ad_Ceditar():
    if request.method == 'POST':
        usuario = request.form['usuario']
        password = request.form['password']

        # Ejemplo simple de validación
        if usuario == "admin" and password == "1234":
            return "✅ Bienvenido, has iniciado sesión correctamente"
        else:
            return "❌ Usuario o contraseña incorrectos"
    return render_template("Ad_Ceditar.html")

if __name__ == '__main__':
    app.run(debug=True)