import os
import json
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

def audit():
    print("--- AUDIT START ---")
    hoy = datetime.now().strftime('%Y-%m-%d')
    
    # Get consumos of today
    res = supabase.table('consumo').select('*').gte('fecha', hoy).order('fecha', desc=True).execute()
    
    if not res.data:
        print("No consumos found for today.")
        return

    for c in res.data:
        # Get details
        details = supabase.table('consumo_detalle').select('*, productos(nombre)').eq('id_consumo', c['id_consumo']).execute()
        dets = []
        for d in (details.data or []):
            p_name = d['productos']['nombre'] if d.get('productos') else f"ID {d['id_producto']}"
            dets.append(f"{p_name}: {d['cantidad_consumida']}")
        det_str = " | ".join(dets)
        print(f"ID {c['id_consumo']} | {c['fecha']} | {c['observacion']} | DETAILS: {det_str}")

if __name__ == "__main__":
    audit()
