from extensions import app, supabase, logger
from flask import session, jsonify, request, redirect, url_for, flash, render_template
from functools import wraps
from datetime import datetime, timedelta
# 2. UTILIDADES Y FILTROS
# ==============================================================================

@app.template_filter('format_fecha')
def format_fecha(value):
    if not value:
        return "Sin fecha"
    dt = datetime.fromisoformat(value.split('T')[0])
    return dt.strftime("%d/%m/%Y")

def to_num(val):
    """Centralized utility to format numbers for display (Removes unnecessary decimals)."""
    if isinstance(val, (int, float)):
        return int(val) if float(val).is_integer() else float(val)
    return val

def insertar_informe(id_pedido):
    existente = supabase.table("informe").select("id_inf_pedido").eq("id_inf_pedido", id_pedido).execute().data
    if not existente:
        supabase.table("informe").insert({
            "id_inf_pedido": id_pedido,
            "fecha_creacion": datetime.now().isoformat()
        }).execute()
        return True
    return False

def login_requerido(rol=None):
    def decorador(f):
        @wraps(f)
        def decorado(*args, **kwargs):
            if not session.get('logged_in'):
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({"success": False, "msg": "Sesion expirada"}), 401
                return redirect(url_for('login'))
            if rol and session.get('role') != rol:
                return jsonify({"success": False, "msg": "Acceso denegado"}), 403
            return f(*args, **kwargs)
        return decorado
    return decorador

# ==============================================================================
# 2.1 CONVERSOR DE UNIDADES
# ==============================================================================
CONVERSIONES = {
    # Masa (Base: kg)
    'kg': 1.0, 'kilogramo': 1.0,
    'g': 0.001, 'gramo': 0.001,
    'lb': 0.453592, 'libra': 0.453592,
    'oz': 0.0283495, 'onza': 0.0283495,
    # Volumen (Base: lt)
    'lt': 1.0, 'litro': 1.0,
    'ml': 0.001, 'mililitro': 0.001,
    'cda': 0.015, 'cucharada': 0.015,
    'cdta': 0.005, 'cucharadita': 0.005,
    # Conteo (Base: und)
    'und': 1.0, 'unidad': 1.0
}

def convertir_cantidad(cantidad, unidad_origen, unidad_destino):
    """
    Convierte una cantidad de una unidad a otra basándose en el mapa de conversiones.
    Ejemplo: 500g a kg -> 0.5
    """
    if not unidad_origen or not unidad_destino:
        return cantidad
        
    u_orig = unidad_origen.lower().strip()
    u_dest = unidad_destino.lower().strip()
    
    if u_orig == u_dest:
        return cantidad
    
    if u_orig in CONVERSIONES and u_dest in CONVERSIONES:
        # Pasamos a la unidad base y luego a la destino
        cantidad_base = cantidad * CONVERSIONES[u_orig]
        return cantidad_base / CONVERSIONES[u_dest]
        
    return cantidad

# ==============================================================================
# 3. SISTEMA DE NOTIFICACIONES (LOGICA)
# ==============================================================================
def generar_notificaciones_caducidad():
    try:
        hoy = datetime.now().date()
        limite = hoy + timedelta(days=3)
        
        test_connection = supabase.table("inventario").select("count", count="exact").execute()
        
        proximos = supabase.table("inventario") \
            .select("id_inventario, id_producto, cantidad, fecha_caducidad") \
            .gte("fecha_caducidad", hoy.isoformat()) \
            .lte("fecha_caducidad", limite.isoformat()) \
            .execute()

        if not proximos.data:
            return
            
        notificaciones_creadas = 0
        for item in proximos.data:
            producto = supabase.table("productos") \
                .select("nombre") \
                .eq("id_producto", item["id_producto"]) \
                .single() \
                .execute()
                
            nombre_producto = producto.data["nombre"] if producto.data else "Nombre no encontrado"

            noti_existente = supabase.table("notificaciones") \
                .eq("id_inventario", item["id_inventario"]) \
                .eq("tipo", "caducidad") \
                .execute()

            if not noti_existente.data:
                mensaje = f" El producto '{nombre_producto}' (ID: {item['id_producto']}) caduca el {item['fecha_caducidad']} | Cantidad: {item['cantidad']}"
                
                supabase.table("notificaciones").insert({
                    "id_inventario": item["id_inventario"],
                    "mensaje": mensaje,
                    "tipo": "caducidad",
                    "leido": False,
                    "fecha": datetime.now().isoformat()
                }).execute()
                notificaciones_creadas += 1

    except Exception as e:
        print("Error al generar notificaciones:", e)
        import traceback
        traceback.print_exc()

def generar_notificaciones_stock_bajo(target_local_id=None):
    try:
        # 1. Obtener todos los productos habilitados
        try:
            productos_res = supabase.table("productos").select("id_producto, nombre, unidad").eq("habilitado", True).execute()
            productos = productos_res.data or []
        except Exception as e:
            print("Error al consultar tabla productos:", e)
            return

        if not productos:
            return

        # 2. Filtrar locales: solo el objetivo o todos
        if target_local_id:
            locales_res = supabase.table("locales").select("id_local, nombre").eq("id_local", target_local_id).execute()
        else:
            locales_res = supabase.table("locales").select("id_local, nombre").execute()
        
        locales = locales_res.data or []
        
        for local in locales:
            id_l = local["id_local"]
            nombre_l = local["nombre"]
            
            # 2. Obtener todo el inventario de este local
            inv_res = supabase.table("inventario").select("id_producto, cantidad").eq("id_local", id_l).execute()
            inv_data = inv_res.data or []
            
            # 3. Consolidar stock actual por producto
            stock_actual_map = {}
            for item in inv_data:
                pid = item["id_producto"]
                stock_actual_map[pid] = stock_actual_map.get(pid, 0) + item["cantidad"]
            
            # 4. Comparar cada producto con su umbral
            for p in productos:
                pid = p["id_producto"]
                nombre_p = p["nombre"]
                unidad_p = p["unidad"]
                actual = stock_actual_map.get(pid, 0)
                if actual <= 50:
                    if actual == 0:
                        mensaje = f"🛑 AGOTADO: '{nombre_p}' en {nombre_l}. No queda stock disponible."
                        tipo_noti = "stock_agotado"
                    else:
                        mensaje = f"⚠️ STOCK BAJO: '{nombre_p}' en {nombre_l}. ACTUAL: {actual} {unidad_p} (Limite: 50)"
                        tipo_noti = "stock_bajo"
                    
                    # Evitar duplicados del mismo tipo para el mismo producto en el mismo local
                    existente = supabase.table("notificaciones")\
                        .select("id_notificaciones")\
                        .eq("tipo", tipo_noti)\
                        .ilike("mensaje", f"%{nombre_p}%{nombre_l}%")\
                        .execute()
                    
                    if not existente.data:
                        # Si existia la otra (ej: paso de bajo a agotado), borrar la vieja
                        otra_tipo = "stock_bajo" if tipo_noti == "stock_agotado" else "stock_agotado"
                        supabase.table("notificaciones").delete().eq("tipo", otra_tipo).ilike("mensaje", f"%{nombre_p}%{nombre_l}%").execute()

                        supabase.table("notificaciones").insert({
                            "mensaje": mensaje,
                            "tipo": tipo_noti,
                            "leido": False,
                            "fecha": datetime.now().isoformat()
                        }).execute()
                else:
                    # Limpiar notificaciones si el stock se recupero
                    supabase.table("notificaciones")\
                        .delete()\
                        .in_("tipo", ["stock_bajo", "stock_agotado"])\
                        .ilike("mensaje", f"%{nombre_p}%{nombre_l}%")\
                        .execute()

    except Exception as e:
        print("Error al generar notificaciones de stock bajo:", e)

def eliminar_notificaciones_caducadas():
    try:
        hoy = datetime.now().date()
        caducados = supabase.table("inventario") \
            .select("id_inventario, id_producto, fecha_caducidad") \
            .lte("fecha_caducidad", hoy.isoformat()) \
            .execute()

        if not caducados.data:
            return

        ids_caducados = [item["id_inventario"] for item in caducados.data]
        res_notif = supabase.table("notificaciones") \
            .delete() \
            .in_("id_inventario", ids_caducados) \
            .execute()
        res_inv = supabase.table("inventario") \
            .delete() \
            .in_("id_inventario", ids_caducados) \
            .execute()
    except Exception as e:
        print("Error al eliminar notificaciones o productos caducados:", e)

@app.route('/Ad_Pnotificaciones', methods=['GET'])
@login_requerido(rol='Administrador')
def Ad_Pnotificaciones():
    generar_notificaciones_caducidad()
    eliminar_notificaciones_caducadas()
    notificaciones = supabase.table("notificaciones") \
        .select("*") \
        .order("fecha", desc=True) \
        .execute()
    return render_template("Ad_templates/Ad_Pnotificaciones.html", notificaciones=notificaciones.data)

@app.route('/marcar_prioritaria/<int:id>', methods=['POST'])
@login_requerido(rol='Administrador')
def marcar_prioritaria(id):
    supabase.table("notificaciones").update({"tipo": "prioritaria"}).eq("id_notificaciones", id).execute()
    return jsonify({"success": True})


def insertar_informe(id_pedido):
    existente = supabase.table("informe").select("id_inf_pedido").eq("id_inf_pedido", id_pedido).execute().data
    if not existente:
        supabase.table("informe").insert({
            "id_inf_pedido": id_pedido,
            "fecha_creacion": datetime.now().isoformat()
        }).execute()
        return True
    return False

@app.route('/')
def index():
    return redirect(url_for('login'))

# ==============================================================================
