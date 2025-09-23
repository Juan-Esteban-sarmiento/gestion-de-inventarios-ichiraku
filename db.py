import mysql.connector

# función de conexión
def get_db_connection():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="admin",
        database="dbgich",
        charset='utf8mb4',
        use_unicode=True
    )
    cursor = conn.cursor()
    cursor.execute("SET NAMES utf8mb4;")
    cursor.execute("SET CHARACTER SET utf8mb4;")
    cursor.execute("SET character_set_connection=utf8mb4;")
    cursor.close()
    return conn

def get_empleados():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True) 
    cursor.execute("SELECT * FROM empleados")
    empleados = cursor.fetchall()
    cursor.close()
    conn.close()
    return empleados


def add_empleado(cedula, nombre, contacto, contrasena, foto_binaria):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        INSERT INTO empleados (Cedula, Nombre, Numero_contacto, Contrasena, Foto)
        VALUES (%s, %s, %s, %s, %s)
    """
    cursor.execute(query, (cedula, nombre, contacto, contrasena, foto_binaria))
    conn.commit()
    cursor.close()
    conn.close()

