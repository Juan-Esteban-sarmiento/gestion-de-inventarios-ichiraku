from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

"""# Ruta principal -> login
@app.route('/')
def index():
    return redirect(url_for('login'))

# Vista login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        password = request.form['password']

        # Ejemplo simple de validación
        if usuario == "admin" and password == "1234":
            return "Bienvenido, has iniciado sesión correctamente"
        else:
            return "Usuario o contraseña incorrectos"
    return render_template("login.html")
if __name__ == '__main__':
    app.run(debug=True)"""

#Ruta principal -> Administrador Inicio
@app.route('/')
def index():
    return redirect(url_for('Ad_Inicio'))

# Vista Administrador Inicio
@app.route('/Ad_Inicio', methods=['GET', 'POST'])
def Ad_Inicio():
    if request.method == 'POST':
        return "Acción de administrador ejecutada"
    return render_template("Ad_Inicio.html")

if __name__ == '__main__':
    app.run(debug=True)