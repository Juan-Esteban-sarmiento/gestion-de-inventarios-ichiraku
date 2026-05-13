import requests

s = requests.Session()

print("Logueando...")
res = s.post('http://127.0.0.1:5000/login', json={"id": "11111", "password": "123", "role": "Empleado", "branch": "1"})
print(res.status_code, res.text)

print("Consultando historial...")
try:
    res = s.get('http://127.0.0.1:5000/historial_consumo_hoy')
    print(res.status_code, res.text[:200])
except Exception as e:
    print(e)
    
print("Consultando comparativa...")
try:
    res = s.get('http://127.0.0.1:5000/get_consumo_comparative')
    print(res.status_code, res.text[:200])
except Exception as e:
    print(e)
