import os
import urllib.request
import json

env_path = os.path.join(os.getcwd(), '.env')
supabase_url = None
supabase_key = None

with open(env_path, 'r', encoding='utf-8') as f:
    for line in f:
        if line.startswith('SUPABASE_URL='):
            supabase_url = line.strip().split('=', 1)[1].strip('"').strip("'")
        elif line.startswith('SUPABASE_KEY='):
            supabase_key = line.strip().split('=', 1)[1].strip('"').strip("'")

headers = {
    "apikey": supabase_key,
    "Authorization": f"Bearer {supabase_key}",
    "Content-Type": "application/json",
}

def fetch(path):
    url = f"{supabase_url}/rest/v1/{path}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())

# 1. Get all consumo records
print("=== CONSUMO RECORDS ===")
consumos = fetch("consumo?select=id_consumo,fecha,cantidad_platos,id_local,observacion&order=id_consumo.desc&limit=10")
for c in consumos:
    print(f"  id={c['id_consumo']} | local={c.get('id_local')} | platos={c.get('cantidad_platos')} | obs={c.get('observacion','')[:80]}")

# 2. Get consumo_detalle records
print("\n=== CONSUMO_DETALLE RECORDS ===")
detalles = fetch("consumo_detalle?select=id_consumo_detalle,id_consumo,id_producto,id_inventario,cantidad_consumida,fecha&order=id_consumo_detalle.desc&limit=20")
for d in detalles:
    print(f"  det_id={d.get('id_consumo_detalle')} | consumo={d['id_consumo']} | prod={d['id_producto']} | cant={d['cantidad_consumida']} | fecha={d.get('fecha','')[:16]}")

# 3. Get JOIN query (same as the report uses)
print("\n=== CONSUMO WITH DETALLE JOIN ===")
joined = fetch("consumo?select=id_consumo,observacion,consumo_detalle(id_consumo_detalle,id_producto,cantidad_consumida,productos(nombre,unidad))&order=id_consumo.desc&limit=10")
for c in joined:
    obs = (c.get('observacion') or '')[:60]
    dets = c.get('consumo_detalle', [])
    print(f"  id={c['id_consumo']} | obs={obs}")
    if dets:
        for d in dets:
            p = d.get('productos', {})
            print(f"    -> prod={p.get('nombre','?')} | cant={d.get('cantidad_consumida')} | unit={p.get('unidad','?')}")
    else:
        print(f"    -> NO DETALLE RECORDS")
