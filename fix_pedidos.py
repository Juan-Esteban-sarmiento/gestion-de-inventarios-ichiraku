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

if not supabase_url or not supabase_key:
    print("No URL or KEY")
    exit(1)

headers = {
    "apikey": supabase_key,
    "Authorization": f"Bearer {supabase_key}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

url = f"{supabase_url}/rest/v1/pedido?select=*"
req = urllib.request.Request(url, headers=headers)
try:
    with urllib.request.urlopen(req) as resp:
        pedidos = json.loads(resp.read().decode())
        print(f"Total pedidos: {len(pedidos)}")
        if pedidos:
            print("Keys:", list(pedidos[0].keys()))
except Exception as e:
    print("Failed to fetch schema:", e)
