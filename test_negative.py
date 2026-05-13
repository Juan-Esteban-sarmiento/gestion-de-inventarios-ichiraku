import requests
import json

s = requests.Session()

# Login
s.post('http://127.0.0.1:5000/login', json={"id": "19307", "password": "123", "role": "Empleado", "branch": "1"})

print("Trying to consume recipe...")
# Use a recipe that exists in DB. First get recipes
res_recipes = s.post('http://127.0.0.1:5000/get_recetas_empleado', json={"termino": ""})
recipes = res_recipes.json().get('recetas', [])
if recipes:
    recipe_id = recipes[0]['id_receta']
    print(f"Testing recipe {recipes[0]['nombre']} (ID: {recipe_id}) with absurd quantity")
    
    res = s.post('http://127.0.0.1:5000/registrar_consumo_receta', json={
        "id_receta": recipe_id,
        "cantidad": 999999
    })
    
    print(res.status_code)
    print(res.text)
else:
    print("No recipes found.")
