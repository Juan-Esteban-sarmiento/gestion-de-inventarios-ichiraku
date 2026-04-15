import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

print("--- Empleados ---")
res = supabase.table("empleados").select("*").limit(1).execute()
if res.data:
    print(res.data[0].keys())

print("--- Administrador ---")
res2 = supabase.table("administrador").select("*").limit(1).execute()
if res2.data:
    print(res2.data[0].keys())
