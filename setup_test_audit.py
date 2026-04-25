from app import supabase
from werkzeug.security import generate_password_hash

def setup_test_data():
    password = generate_password_hash("test1234")
    
    # 1. Crear Admin de prueba (ID 777)
    admin_data = {
        "id": 777,
        "nombre": "NINJA TESTER",
        "contrasena": password,
        "master_key": "MASTER777NINJA"
    }
    supabase.table("administrador").upsert(admin_data).execute()
    print("Admin de prueba 777 creado.")

    # 2. Asegurar que el local 1 este habilitado (ya lo esta, pero por si acaso)
    
if __name__ == "__main__":
    setup_test_data()
