import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# See if we can query the same way the endpoints do:
try:
    print("Testing historial query...")
    res = supabase.table("consumo_detalle") \
            .select("*, productos(nombre, unidad), consumo(*), inventario(id_local)") \
            .limit(5) \
            .execute()
    print("Success historial!")
except Exception as e:
    print("Error historial:", e)

try:
    print("\nTesting comparative query...")
    res = supabase.table("consumo_detalle") \
            .select("id_producto, cantidad_consumida, productos(nombre, unidad), inventario(id_local)") \
            .limit(5) \
            .execute()
    print("Success comparative!")
except Exception as e:
    print("Error comparative:", e)
