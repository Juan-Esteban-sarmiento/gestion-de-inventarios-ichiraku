import os
import json
from supabase import create_client
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Backup hashes if not already backed up
if not os.path.exists("scratch/backup_hashes.json"):
    admin_data = supabase.table("administrador").select("id, contrasena").eq("id", 5).execute().data
    emp_data = supabase.table("empleados").select("cedula, contrasena").eq("cedula", 88800888).execute().data
    backup = {
        "admin": admin_data[0] if admin_data else None,
        "emp": emp_data[0] if emp_data else None
    }
    with open("scratch/backup_hashes.json", "w") as f:
        json.dump(backup, f)

new_hash = generate_password_hash("123")
supabase.table("administrador").update({"contrasena": new_hash}).eq("id", 5).execute()
supabase.table("empleados").update({"contrasena": new_hash}).eq("cedula", 88800888).execute()

print("Passwords temporarily changed to '123'")
