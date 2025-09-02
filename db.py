import mysql.connector

# función de conexión
def get_db_connection():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="admin",
        database="dbgich"
    )
    return conn

def get_empleados():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True) 
    cursor.execute("SELECT * FROM empleados")
    empleados = cursor.fetchall()
    cursor.close()
    conn.close()
    return empleados


def add_empleado(cedula, nombre, numero_contacto, contrasena, foto):
    conn = get_db_connection()
    cursor = conn.cursor()
    sql = "INSERT INTO empleados (Cedula, Nombre, Numero_contacto, Contrasena, Foto) VALUES (%s, %s, %s, %s, %s)"
    values = (cedula, nombre, numero_contacto, contrasena, foto)
    cursor.execute(sql, values)
    conn.commit()
    cursor.close()
    conn.close()
