import os
import base64
import csv
import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from io import StringIO
from flask import Flask, flash, jsonify, render_template, request, redirect, url_for, session, make_response
from db import add_empleado, get_db_connection



app = Flask(__name__)
app.secret_key = '123456789'


# ╔══════════════════════════════════════════════╗
# ║ Redirección inicial de Logueo             ║
# ╚══════════════════════════════════════════════╝

@app.route('/')
def index():
    return redirect(url_for('login'))

# ╔══════════════════════════════════════════════╗
# ║ Configuración de Logueo y Cierre de Sesión     ║
# ╚══════════════════════════════════════════════╝

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

# ╔══════════════════════════════════════════════╗
# ║ Registro, Búsqueda y Eliminación de Empleados║
# ╚══════════════════════════════════════════════╝

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

@app.route('/Ad_Rproductos', methods=['GET', 'POST'])
def Ad_Rproductos():
    return render_template("Ad_templates/Ad_Rproductos.html")

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

@app.route('/Ad_Dinformes', methods=['GET', 'POST'])
def Ad_Dinformes():
    return render_template("Ad_templates/Ad_Dinformes.html")

@app.route('/Ad_Rlocales', methods=['GET', 'POST'])
def Ad_Rlocales():
    return render_template("Ad_templates/Ad_Rlocales.html")

@app.route('/Ad_Pnotificaciones', methods=['GET', 'POST'])
def Ad_Pnotificaciones():
    return render_template("Ad_templates/Ad_Pnotificaciones.html")

# ╔══════════════════════════════════════════════╗
# ║ Registro, Búsqueda y Eliminación de Productos║
# ╚══════════════════════════════════════════════╝

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


# ╔══════════════════════════════════════════════╗
# ║ Generación y gestión de informes             ║
# ╚══════════════════════════════════════════════╝

@app.route('/generar_informe_semanal', methods=['POST'])
def generar_informe_semanal():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute('''
            SELECT YEAR(fecha_pedido) as anio, WEEK(fecha_pedido) as semana, GROUP_CONCAT(Id_Pedido) as pedidos
            FROM pedido
            GROUP BY anio, semana
        ''')
        semanas = cursor.fetchall()
        informes_creados = []

        for semana in semanas:
            periodo = f"{semana['anio']}-W{semana['semana']}"
            pedidos_ids = semana['pedidos'] if semana['pedidos'] else ""

            # Guardar 1 informe por semana
            cursor.execute('''
                INSERT INTO informe (Tipo, Periodo, Id_Inf_Pedido)
                VALUES (%s, %s, %s)
            ''', ("semanal", periodo, pedidos_ids))
            informes_creados.append(cursor.lastrowid)

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"success": True, "msg": f"Informes semanales creados: {len(informes_creados)}"})
    except Exception as e:
        print("Error al generar informe semanal:", e)
        return jsonify({"success": False, "msg": "Error al generar informe semanal"})

@app.route('/generar_informe_mensual', methods=['POST'])
def generar_informe_mensual():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute('''
            SELECT YEAR(fecha_pedido) as anio, MONTH(fecha_pedido) as mes, GROUP_CONCAT(Id_Pedido) as pedidos
            FROM pedido
            GROUP BY anio, mes
        ''')
        meses = cursor.fetchall()
        informes_creados = []

        for mes in meses:
            periodo = f"{mes['anio']}-M{str(mes['mes']).zfill(2)}"
            pedidos_ids = mes['pedidos'] if mes['pedidos'] else ""

            cursor.execute('''
                INSERT INTO informe (Tipo, Periodo, Id_Inf_Pedido)
                VALUES (%s, %s, %s)
            ''', ("mensual", periodo, pedidos_ids))
            informes_creados.append(cursor.lastrowid)

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"success": True, "msg": f"Informes mensuales creados: {len(informes_creados)}"})
    except Exception as e:
        print("Error al generar informe mensual:", e)
        return jsonify({"success": False, "msg": "Error al generar informe mensual"})

@app.route('/buscar_informe', methods=['POST'])
def buscar_informe():
    data = request.get_json()
    id_informe = data.get('id_informe')
    fecha = data.get('fecha')
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if id_informe:
            cursor.execute('SELECT * FROM informe WHERE Id_Informe = %s', (id_informe,))
            informe = cursor.fetchall()
        elif fecha:
            cursor.execute('SELECT * FROM informe WHERE DATE(Fecha_Creacion) = %s', (fecha,))
            informe = cursor.fetchall()
        else:
            informe = []

        cursor.close()
        conn.close()

        if informe:
            return jsonify({"success": True, "informes": informe})
        else:
            return jsonify({"success": False, "msg": "No se encontraron informes"})
    except Exception as e:
        print("Error al buscar informe:", e)
        return jsonify({"success": False, "msg": "Error al buscar informe"})
    
@app.route('/descargar_informe/<int:id_informe>', methods=['GET'])
def descargar_informe(id_informe):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 🔹 Obtener datos del informe
        cursor.execute('SELECT * FROM informe WHERE Id_Informe = %s', (id_informe,))
        informe = cursor.fetchone()
        if not informe:
            cursor.close()
            conn.close()
            return jsonify({"success": False, "msg": "Informe no encontrado"}), 404

        # 🔹 Determinar período según tipo
        pedidos = []
        if informe["Tipo"] == "semanal":
            # formato esperado: "2025-W39"
            anio, semana = map(int, informe["Periodo"].split('-W'))
            cursor.execute("""
                SELECT pe.Id_Pedido
                FROM pedido pe
                WHERE YEAR(pe.fecha_pedido) = %s AND WEEK(pe.fecha_pedido) = %s
                ORDER BY pe.Id_Pedido
            """, (anio, semana))
            pedidos = [row["Id_Pedido"] for row in cursor.fetchall()]
        elif informe["Tipo"] == "mensual":
            # formato esperado: "2025-M09"
            anio, mes = informe["Periodo"].split('-M')
            anio = int(anio)
            mes = int(mes)
            cursor.execute("""
                SELECT pe.Id_Pedido
                FROM pedido pe
                WHERE YEAR(pe.fecha_pedido) = %s AND MONTH(pe.fecha_pedido) = %s
                ORDER BY pe.Id_Pedido
            """, (anio, mes))
            pedidos = [row["Id_Pedido"] for row in cursor.fetchall()]

        # 🔹 Obtener detalles de todos los pedidos
        if pedidos:
            cursor.execute(f"""
                SELECT pe.Id_Pedido, i.Id_Local, p.Nombre, p.Categoria, dp.Cantidad
                FROM pedido pe
                JOIN detalle_pedido dp ON pe.Id_Pedido = dp.Id_Pedido
                JOIN inventario i ON i.Id_Producto = dp.Id_Producto
                JOIN productos p ON p.Id_Producto = dp.Id_Producto
                WHERE pe.Id_Pedido IN ({','.join(['%s']*len(pedidos))})
                ORDER BY pe.Id_Pedido
            """, tuple(pedidos))
            detalles = cursor.fetchall()
        else:
            detalles = []

        cursor.close()
        conn.close()

        # 🔹 Crear PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()

        elements.append(Paragraph(f"📊 Informe #{informe['Id_Informe']}", styles['Title']))
        elements.append(Spacer(1, 20))

        info_table_data = [
            ["ID Informe", informe["Id_Informe"]],
            ["Tipo", informe["Tipo"]],
            ["Periodo", informe["Periodo"]],
            ["Fecha Creación", str(informe["Fecha_Creacion"])],
        ]
        info_table = Table(info_table_data, colWidths=[150, 300])
        info_table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#e63900")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("ALIGN", (0,0), (-1,-1), "LEFT"),
            ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
            ("BACKGROUND", (0,1), (-1,-1), colors.whitesmoke),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 20))

        if detalles:
            elements.append(Paragraph("📦 Detalles de Pedidos", styles['Heading2']))
            detalles_data = [["ID Pedido", "ID Local", "Producto", "Categoría", "Cantidad"]] + [
                [d["Id_Pedido"], d["Id_Local"], d["Nombre"], d["Categoria"], d["Cantidad"]] for d in detalles
            ]
            detalles_table = Table(detalles_data, colWidths=[60, 60, 180, 120, 60])
            detalles_table.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#e63900")),
                ("TEXTCOLOR", (0,0), (-1,0), colors.white),
                ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
                ("ALIGN", (0,0), (-1,-1), "CENTER"),
                ("GRID", (0,0), (-1,-1), 0.5, colors.black),
                ("BACKGROUND", (0,1), (-1,-1), colors.HexColor("#fbe9e7")),
            ]))
            elements.append(detalles_table)
        else:
            elements.append(Paragraph("⚠️ No hay pedidos en este período.", styles['Normal']))

        doc.build(elements)

        buffer.seek(0)
        response = make_response(buffer.read())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=informe_{id_informe}.pdf'
        return response

    except Exception as e:
        print("Error al generar PDF:", e)
        return jsonify({"success": False, "msg": f"Error al generar informe PDF: {e}"})


# ╔══════════════════════════════════════════════╗
# ║ Edición de Datos del Administrador           ║
# ╚══════════════════════════════════════════════╝

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

# ╔══════════════════════════════════════════════╗
# ║ Rutas de Empleado                            ║
# ╚══════════════════════════════════════════════╝

@app.route('/Em_Inicio', methods=['GET', 'POST'])
def Em_Inicio():
    if not session.get('logged_in') or session.get('role') != 'Empleado':
        return redirect(url_for('login'))
    response = make_response(render_template("Em_templates/Em_Inicio.html"))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

@app.route('/Em_Rordenes', methods=['GET', 'POST'])
def Em_Rordenes():
    return render_template("Em_templates/Em_Rordenes.html")

@app.route('/Em_Rpedido', methods=['GET', 'POST'])
def Em_Rpedido():
    return render_template("Em_templates/Em_Rpedido.html")

@app.route('/Em_Hordenes', methods=['GET', 'POST'])
def Em_Hordenes():
    return render_template("Em_templates/Em_Hordenes.html")

# ╔══════════════════════════════════════════════╗
# ║ Búsqueda y Lista de Productos para EMPLEADOS ║
# ╚══════════════════════════════════════════════╝

@app.route("/buscar_producto_empleado", methods=["POST"])
def buscar_producto_empleado():
    data = request.get_json()
    termino = data.get("termino", "").strip()  # Si no hay termino, es vacío para listar todos

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if termino:  # Si hay término de búsqueda
            query = """
                SELECT Id_Producto, Nombre, Categoria, Unidad, Foto
                FROM productos
                WHERE Nombre LIKE %s OR Categoria LIKE %s
                ORDER BY Nombre
            """
            like_pattern = f"%{termino}%"
            cursor.execute(query, (like_pattern, like_pattern))
        else:  # Si termino vacío, listar TODOS los productos
            query = """
                SELECT Id_Producto, Nombre, Categoria, Unidad, Foto
                FROM productos
                ORDER BY Nombre
            """
            cursor.execute(query)

        productos = cursor.fetchall()
        cursor.close()
        conn.close()

        # Convertir binario a Base64 para imágenes
        for prod in productos:
            if prod["Foto"]:
                prod["Foto"] = f"data:image/jpeg;base64,{base64.b64encode(prod['Foto']).decode('utf-8')}"
            else:
                prod["Foto"] = None  # O usa una imagen por defecto en JS

        return jsonify({"success": True, "productos": productos})

    except Exception as e:
        print("Error en búsqueda de producto para empleado:", e)
        return jsonify({"success": False, "msg": "Error en servidor"})


# ╔══════════════════════════════════════════════╗
# ║ Registro de Pedidos para EMPLEADO            ║
# ╚══════════════════════════════════════════════╝

@app.route("/registrar_pedido", methods=["POST"])
def registrar_pedido():
    if not session.get("logged_in") or session.get("role") != "Empleado":
        return jsonify({"success": False, "msg": "No autorizado"}), 401

    try:
        data = request.get_json()
        id_local = data.get("Id_Local")
        productos = data.get("Productos")  # Lista de {Id_Producto, Cantidad, Fecha_Ingreso, Fecha_Caducidad}

        if not (id_local and productos and isinstance(productos, list) and len(productos) > 0):
            return jsonify({"success": False, "msg": "Datos inválidos"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # 🔹 1️⃣ Crear registros en inventario para cada producto
        inventarios = []
        for prod in productos:
            id_producto = prod.get("Id_Producto")
            cantidad = prod.get("Cantidad")
            fecha_ingreso = prod.get("Fecha_Ingreso")
            fecha_caducidad = prod.get("Fecha_Caducidad")

            if not (id_producto and cantidad and fecha_ingreso and fecha_caducidad):
                continue

            cursor.execute("""
                INSERT INTO inventario (Id_Local, Id_Producto, Cantidad, Fecha_ingreso, Fecha_caducidad)
                VALUES (%s, %s, %s, %s, %s)
            """, (id_local, id_producto, cantidad, fecha_ingreso, fecha_caducidad))

            inventarios.append(cursor.lastrowid)  # Guardamos el Id_Inventario generado

        if not inventarios:
            return jsonify({"success": False, "msg": "No se pudieron registrar los inventarios"}), 400

        # 🔹 2️⃣ Crear un solo pedido apuntando al primer inventario (o puedes ajustar según tu lógica)
        id_inventario = inventarios[0]
        cursor.execute("""
            INSERT INTO pedido (Id_Inventario, Cedula, fecha_pedido)
            VALUES (%s, %s, NOW())
        """, (id_inventario, session.get("cedula")))
        id_pedido = cursor.lastrowid

        # 🔹 3️⃣ Insertar cada producto en detalle_pedido
        for prod in productos:
            id_producto = prod.get("Id_Producto")
            cantidad = prod.get("Cantidad")
            fecha_pedido = prod.get("Fecha_Ingreso")  # Usamos fecha de ingreso como referencia del pedido

            cursor.execute("""
                INSERT INTO detalle_pedido (Id_Pedido, Id_Producto, Cantidad, Fecha_Pedido)
                VALUES (%s, %s, %s, %s)
            """, (id_pedido, id_producto, cantidad, fecha_pedido))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            "success": True,
            "msg": f"Pedido #{id_pedido} registrado con éxito con {len(productos)} productos."
        }), 201

    except Exception as e:
        print("Error al registrar pedido:", e)
        return jsonify({"success": False, "msg": f"Error en servidor: {str(e)}"}), 500


# ╔══════════════════════════════════════════════╗
# ║ Edición de Datos del Empleado             ║
# ╚══════════════════════════════════════════════╝

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

    cursor.close()
    conn.close()
    return render_template("Em_templates/Em_Ceditar.html", user=empleado)


# ╔══════════════════════════════════════════════╗
# ║ Cierre de Sesión                             ║
# ╚══════════════════════════════════════════════╝

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
