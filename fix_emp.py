import os, json, urllib.request

env = {}
try:
    with open('.env', 'r', encoding='utf-8') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                k, v = line.strip().split('=', 1)
                env[k] = v.strip('"').strip("'")
except Exception as e:
    print(e)

url = env.get('SUPABASE_URL')
key = env.get('SUPABASE_KEY')

if url and key:
    req = urllib.request.Request(url+'/rest/v1/consumo?select=*', headers={'apikey': key, 'Authorization': 'Bearer '+key})
    resp = urllib.request.urlopen(req)
    data = json.loads(resp.read().decode('utf-8'))

    updated = 0
    for row in data:
        obs = row.get('observacion', '')
        if obs and '[Emp:' not in obs:
            new_obs = obs + ' [Emp: Admin]'
            update_req = urllib.request.Request(url+'/rest/v1/consumo?id_consumo=eq.'+str(row['id_consumo']), 
                                               data=json.dumps({'observacion': new_obs}).encode('utf-8'),
                                               headers={'apikey': key, 'Authorization': 'Bearer '+key, 'Content-Type': 'application/json'},
                                               method='PATCH')
            urllib.request.urlopen(update_req)
            updated += 1
    print(f'Updated {updated} records.')
else:
    print('No credentials found')
