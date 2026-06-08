from flask import render_template, request, jsonify, redirect, url_for, session, make_response, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, date
import re
import math
import locale
from io import BytesIO
import csv

from extensions import app, supabase, logger
from utils import login_requerido, to_num, generar_notificaciones_caducidad, generar_notificaciones_stock_bajo, eliminar_notificaciones_caducadas, convertir_cantidad
# 7. OPERACIONES DE EMPLEADOS
# ==============================================================================

@app.route('/registrar_consumo', methods=['POST'])
@login_requerido(rol='Empleado')
def registrar_consumo():
    try:
        data = request.get_json()
        id_producto = data.get('id_producto')
        cantidad = data.get('cantidad')
        
        if not (id_producto and cantidad):
            return jsonify({"success": False, "msg": "Datos incompletos."}), 400
            
        try:
            cantidad_val = float(cantidad)
            if cantidad_val <= 0:
                raise ValueError
        except:
            return jsonify({"success": False, "msg": "La cantidad debe ser mayor a cero."}), 400

        id_sucursal = session.get('branch')
        if not id_sucursal:
            return jsonify({"success": False, "msg": "Error de sesion: Sucursal no definida."}), 403

        producto_info = supabase.table("productos").select("nombre, unidad").eq("id_producto", id_producto).execute()
        nombre_producto = producto_info.data[0].get("nombre", "Desconocido") if producto_info.data else "Desconocido"

        # Filtrar solo lotes con stock disponible
        inventario = supabase.table("inventario").select("*")\
            .eq("id_producto", id_producto)\
            .eq("id_local", id_sucursal)\
            .gt("cantidad", 0)\
            .order("fecha_caducidad")\
            .execute()
        
        if not inventario.data:
            return jsonify({"success": False, "msg": "No hay stock disponible."}), 400
        
        # Validacion atomica antes de hacer descuentos
        disponible_total = sum(float(l['cantidad']) for l in inventario.data)
        if disponible_total < float(cantidad_val):
             return jsonify({"success": False, "msg": f"Stock insuficiente. Solo hay {to_num(disponible_total)} {producto_info.data[0].get('unidad', '')}."}), 400

        restante = float(cantidad_val)
        detalles_afectados = []
        
        for lote in inventario.data:
            cant_lote = float(lote['cantidad'])
            id_inv = lote['id_inventario']
            
            if cant_lote >= restante:
                detalles_afectados.append({
                    "id_producto": int(id_producto),
                    "id_inventario": id_inv,
                    "cantidad_consumida": to_num(restante),
                    "fecha": datetime.now().isoformat()
                })
                restante = 0
                break
            else:
                detalles_afectados.append({
                    "id_producto": int(id_producto),
                    "id_inventario": id_inv,
                    "cantidad_consumida": to_num(cant_lote),
                    "fecha": datetime.now().isoformat()
                })
                restante -= cant_lote

        # Historial
        try:
            cons_res = supabase.table("consumo").insert({
                "fecha": datetime.now().isoformat(),
                "cantidad_platos": 1,
                "observacion": f"Consumo manual: {nombre_producto} (Cant: {cantidad_val})"
            }).execute()
            
            if cons_res.data:
                id_c = cons_res.data[0]["id_consumo"]
                for det in detalles_afectados:
                    det["id_consumo"] = id_c
                    supabase.table("consumo_detalle").insert(det).execute()
        except: pass

        # Generar alertas inmediatas (optimizado por local)
        generar_notificaciones_stock_bajo(session.get('branch'))

        return jsonify({"success": True, "msg": "Consumo registrado correctamente."})
    except Exception as e:
        return jsonify({"success": False, "msg": str(e)})

@app.route('/registrar_merma', methods=['POST'])
@login_requerido(rol='Empleado')
def registrar_merma():
    try:
        data = request.get_json()
        id_producto = data.get('id_producto')
        cantidad_val = data.get('cantidad')
        motivo = data.get('motivo', 'No especificado')
        id_l = session.get('branch')

        if not id_producto or not cantidad_val:
            return jsonify({"success": False, "msg": "Datos incompletos."}), 400

        try:
            cantidad_num = float(cantidad_val)
            if cantidad_num <= 0:
                return jsonify({"success": False, "msg": "La cantidad debe ser mayor a cero."}), 400
        except ValueError:
            return jsonify({"success": False, "msg": "Cantidad invalida."}), 400

        # Obtener info basica del producto
        producto_info = supabase.table("productos").select("nombre, unidad").eq("id_producto", id_producto).execute()
        if not producto_info.data:
            return jsonify({"success": False, "msg": "Producto no encontrado."}), 404
        
        nombre_producto = producto_info.data[0]['nombre']

        # Validar stock (FIFO)
        inventario = supabase.table("inventario").select("*").eq("id_producto", id_producto).eq("id_local", id_l).gt("cantidad", 0).order("fecha_caducidad").execute()
        
        if not inventario.data:
             return jsonify({"success": False, "msg": f"Stock insuficiente para '{nombre_producto}'. No hay existencias."}), 400

        disponible_total = sum(float(l['cantidad']) for l in inventario.data)
        if disponible_total < float(cantidad_val):
             return jsonify({"success": False, "msg": f"Stock insuficiente. Solo hay {to_num(disponible_total)} {producto_info.data[0].get('unidad', '')}."}), 400

        restante = float(cantidad_val)
        detalles_afectados = []
        
        for lote in inventario.data:
            cant_lote = float(lote['cantidad'])
            id_inv = lote['id_inventario']
            
            if cant_lote >= restante:
                detalles_afectados.append({
                    "id_producto": int(id_producto),
                    "id_inventario": id_inv,
                    "cantidad_consumida": to_num(restante),
                    "fecha": datetime.now().isoformat()
                })
                restante = 0
                break
            else:
                detalles_afectados.append({
                    "id_producto": int(id_producto),
                    "id_inventario": id_inv,
                    "cantidad_consumida": to_num(cant_lote),
                    "fecha": datetime.now().isoformat()
                })
                restante -= cant_lote

        # Registrar historial bajo categoria MERMA
        try:
            cons_res = supabase.table("consumo").insert({
                "fecha": datetime.now().isoformat(),
                "cantidad_platos": 0, # No es un plato vendido
                "id_local": id_l,
                "observacion": f"[MERMA] {motivo} | Prod: {nombre_producto} (Cant: {cantidad_val}) [Emp: {session.get('nombre', 'Desconocido')}]"
            }).execute()
            
            if cons_res.data:
                id_c = cons_res.data[0]["id_consumo"]
                for det in detalles_afectados:
                    det["id_consumo"] = id_c
                    # La insercion activa el Trigger de DB para descontar
                    supabase.table("consumo_detalle").insert(det).execute()
        except Exception as e:
            print("Error en insert merma:", e)
            return jsonify({"success": False, "msg": "Error al registrar merma en base de datos."}), 500

        # Generar alertas inmediatas
        generar_notificaciones_stock_bajo(id_l)

        return jsonify({"success": True, "msg": "Merma registrada correctamente."})
    except Exception as e:
        print("Error en /registrar_merma:", e)
        return jsonify({"success": False, "msg": str(e)})

@app.route('/get_recetas_empleado', methods=['POST'])
@login_requerido(rol='Empleado')
def get_recetas_empleado():
    try:
        data = request.get_json() or {}
        termino = data.get("termino", "").strip()
        query = supabase.table("recetarios").select("*").eq("habilitado", True)
        if termino:
            query = query.ilike("nombre", f"%{termino}%")
        res = query.order("nombre").execute()
        return jsonify({"success": True, "recetas": res.data or []})
    except Exception as e:
        return jsonify({"success": False, "msg": str(e)})

@app.route('/registrar_consumo_receta', methods=['POST'])
@login_requerido(rol='Empleado')
def registrar_consumo_receta():
    try:
        data = request.get_json()
        id_r = data.get('id_receta')
        cant_p = int(data.get('cantidad', 1))
        id_l = session.get('branch')
        
        receta = supabase.table("recetarios").select("nombre").eq("id_receta", id_r).execute()
        if not receta.data:
            return jsonify({"success": False, "msg": "Receta no existe"}), 404
            
        detalles = supabase.table("receta_detalle").select("*, productos(nombre, unidad)").eq("id_receta", id_r).execute()
        if not detalles.data:
            return jsonify({"success": False, "msg": "La receta no tiene ingredientes."}), 400

        # FASE 0: Agregar ingredientes por ID de producto (evita doble descuento si hay duplicados en la receta)
        ingredientes_agregados = {}
        for ing in detalles.data:
            pid = ing["id_producto"]
            cant_ing = float(ing["cantidad"])
            if pid not in ingredientes_agregados:
                ingredientes_agregados[pid] = {
                    "id_producto": pid,
                    "cantidad": 0,
                    "productos": ing.get("productos"),
                    "unidad": ing.get("unidad") # <-- IMPORTANTE: Guardamos la unidad aqui
                }
            ingredientes_agregados[pid]["cantidad"] += cant_ing

        # FASE 1: Validar stock de todos los ingredientes
        inventario_necesario = []
        for ing in ingredientes_agregados.values():
            p_name = ing['productos']['nombre'] if ing.get('productos') else ing['id_producto']
            p_unit_base = ing['productos']['unidad'] if ing.get('productos') else ""
            
            # Unidad que pide la receta
            u_receta = ing.get("unidad", "und")
            
            # Cantidad base segun la receta
            cant_receta_total = float(ing["cantidad"]) * cant_p
            
            # CONVERSION: Convertimos de la unidad de la receta a la unidad base del producto (inventario)
            requerido = round(convertir_cantidad(cant_receta_total, u_receta, p_unit_base), 4)
            
            lotes = supabase.table("inventario").select("*").eq("id_producto", ing["id_producto"]).eq("id_local", id_l).gt("cantidad", 0).order("fecha_caducidad").execute()
            
            if not lotes.data:
                return jsonify({"success": False, "msg": f"Stock insuficiente para '{p_name}'. Sin stock (Requerido: {to_num(requerido)} {p_unit_base})"}), 400
                
            disponible = round(sum(float(l['cantidad']) for l in lotes.data), 4)
            if disponible < requerido:
                return jsonify({"success": False, "msg": f"Stock insuficiente para '{p_name}'. Solo hay {to_num(disponible)} {p_unit_base} (Requerido: {to_num(requerido)} {p_unit_base})"}), 400
                
            inventario_necesario.append({
                "id_producto": ing["id_producto"],
                "requerido": requerido,
                "lotes": lotes.data
            })

        # FASE 2: Descontar stock (sin transacciones, pero con validacion previa exitosa)
        afectados_total = []
        for item in inventario_necesario:
            restante = float(item["requerido"])
            for lote in item["lotes"]:
                if restante <= 0: break
                id_inv = lote['id_inventario']
                cant_lote = float(lote['cantidad'])
                
                if cant_lote >= restante:
                    # Usamos float directo para asegurar precision en el descuento
                    afectados_total.append({"id_prod": item["id_producto"], "id_inv": id_inv, "cant": round(restante, 4)})
                    restante = 0
                else:
                    afectados_total.append({"id_prod": item["id_producto"], "id_inv": id_inv, "cant": round(cant_lote, 4)})
                    restante -= cant_lote

        # Registrar consumo e historial
        c_res = supabase.table("consumo").insert({
            "fecha": datetime.now().isoformat(),
            "cantidad_platos": cant_p,
            "id_receta": id_r,
            "id_local": id_l,
            "observacion": f"Venta: {cant_p} platos de {receta.data[0]['nombre']} [Emp: {session.get('nombre', 'Desconocido')}]"
        }).execute()
        
        if c_res.data:
            idc = c_res.data[0]["id_consumo"]
            for a in afectados_total:
                supabase.table("consumo_detalle").insert({
                    "id_consumo": idc,
                    "id_producto": a["id_prod"],
                    "id_inventario": a["id_inv"],
                    "cantidad_consumida": a["cant"],
                    "fecha": datetime.now().isoformat()
                }).execute()
                
        # Generar alertas inmediatas (optimizado por local)
        generar_notificaciones_stock_bajo(id_l)
        
        return jsonify({"success": True, "msg": "Venta registrada exitosamente!"})
    except Exception as e:
        print("Error en registrar_consumo_receta:", e)
        return jsonify({"success": False, "msg": "Verifique que todos los productos esten en el inventario. Error: "+str(e)}), 400


@app.route('/historial_consumo_hoy', methods=['GET'])
@login_requerido(rol='Empleado')
def historial_consumo_hoy():
    try:
        id_sucursal = session.get('branch')
        if not id_sucursal:
            return jsonify({"success": False, "msg": "Sucursal no definida."}), 403

        hoy = datetime.now().strftime("%Y-%m-%d")

        consumos = supabase.table("consumo") \
            .select("*, recetarios(nombre), consumo_detalle(productos(unidad))") \
            .gte("fecha", f"{hoy}T00:00:00") \
            .lte("fecha", f"{hoy}T23:59:59") \
            .eq("id_local", id_sucursal) \
            .execute()

        import re
        registros = []
        if consumos.data:
            for item in consumos.data:
                obs = item.get("observacion", "")
                empleado = "General"
                
                match_emp = re.search(r"\[Emp: (.*?)\]", obs)
                if match_emp:
                    empleado = match_emp.group(1)
                    obs = obs.replace(f"[Emp: {empleado}]", "").strip()

                if item.get("recetarios"):
                    nombre = item["recetarios"]["nombre"]
                    cantidad = item.get("cantidad_platos", 0)
                    unidad = "platos"
                else:
                    match_merma = re.search(r"\[MERMA\] (.*?) \| Prod: (.*?) \(Cant: (.*?)\)", obs)
                    if match_merma:
                        motivo = match_merma.group(1).strip()
                        prod = match_merma.group(2).strip()
                        cant = match_merma.group(3).strip()
                        nombre = f"{prod} (Merma: {motivo})"
                        cantidad = cant
                        
                        unidad_real = ""
                        if item.get("consumo_detalle") and isinstance(item["consumo_detalle"], list) and len(item["consumo_detalle"]) > 0:
                            try:
                                # Safe access to nested dicts
                                det = item["consumo_detalle"][0]
                                if "productos" in det and det["productos"]:
                                    unidad_real = det["productos"].get("unidad", "")
                            except Exception:
                                pass
                        
                        unidad = unidad_real if unidad_real else "und/kg"
                    else:
                        nombre = obs
                        cantidad = "-"
                        unidad = "-"

                registros.append({
                    "id_producto": item.get("id_consumo"),
                    "nombre_producto": nombre,
                    "cantidad": cantidad,
                    "unidad": unidad,
                    "empleado": empleado,
                    "fecha": item["fecha"]
                })

        return jsonify({"success": True, "consumos": registros})

    except Exception as e:
        print("Error en historial_consumo_hoy:", e)
        import traceback
        return jsonify({"success": False, "msg": f"Error al obtener historial: {str(e)}\n{traceback.format_exc()}"}), 500

@app.route('/get_receta_breakdown', methods=['POST'])
@login_requerido(rol='Empleado')
def get_receta_breakdown():
    try:
        data = request.get_json()
        id_receta = data.get('id_receta')
        
        if not id_receta:
            return jsonify({"success": False, "msg": "ID de receta no proporcionado."}), 400
            
        detalles = supabase.table("receta_detalle") \
            .select("*, productos(nombre, unidad)") \
            .eq("id_receta", id_receta) \
            .execute()
            
        if not detalles.data:
            return jsonify({"success": True, "breakdown": []})
            
        breakdown = []
        for d in detalles.data:
            breakdown.append({
                "nombre": d['productos']['nombre'] if d.get('productos') else "Desconocido",
                "cantidad": d['cantidad'],
                "unidad": d.get('unidad') or (d['productos']['unidad'] if d.get('productos') else "")
            })
            
        return jsonify({"success": True, "breakdown": breakdown})
    except Exception as e:
        return jsonify({"success": False, "msg": str(e)}), 500

@app.route('/get_consumo_comparative', methods=['GET'])
@login_requerido(rol='Empleado')
def get_consumo_comparative():
    try:
        id_local = session.get('branch')
        if not id_local:
            return jsonify({"success": False, "msg": "Sucursal no definida."}), 403

        hoy = datetime.now().strftime("%Y-%m-%d")
        
        # 1. Obtener consumos de hoy para el local
        consumos_hoy = supabase.table("consumo_detalle") \
            .select("id_producto, cantidad_consumida, productos(nombre, unidad), inventario(id_local)") \
            .gte("fecha", f"{hoy}T00:00:00") \
            .lte("fecha", f"{hoy}T23:59:59") \
            .execute()

        agregado_consumo = {}
        if consumos_hoy.data:
            for c in consumos_hoy.data:
                # Filtrar por local
                if c.get('inventario') and c['inventario'].get('id_local') == id_local:
                    pid = c['id_producto']
                    if pid not in agregado_consumo:
                        agregado_consumo[pid] = {
                            "nombre": c['productos']['nombre'],
                            "unidad": c['productos']['unidad'],
                            "total_consumido": 0
                        }
                    agregado_consumo[pid]["total_consumido"] += c['cantidad_consumida']

        # 2. Obtener stock actual para el local
        inventario = supabase.table("inventario") \
            .select("id_producto, cantidad") \
            .eq("id_local", id_local) \
            .execute()
            
        stock_actual = {}
        if inventario.data:
            for inv in inventario.data:
                pid = inv['id_producto']
                stock_actual[pid] = stock_actual.get(pid, 0) + inv['cantidad']

        # 3. Combinar datos
        comparativa = []
        # Asegurar incluir productos que tengan stock pero no consumo hoy, o viceversa
        todos_pids = set(agregado_consumo.keys()) | set(stock_actual.keys())
        
        # Necesitamos nombres para los que solo tienen stock
        if stock_actual:
            productos_info = supabase.table("productos").select("id_producto, nombre, unidad").in_("id_producto", list(todos_pids)).execute()
            p_map = {p['id_producto']: p for p in productos_info.data}
        else:
            p_map = {}

        for pid in todos_pids:
            consumo_data = agregado_consumo.get(pid, {})
            nombre = consumo_data.get("nombre") or (p_map.get(pid, {}).get("nombre", "Desconocido"))
            unidad = consumo_data.get("unidad") or (p_map.get(pid, {}).get("unidad", ""))
            
            comparativa.append({
                "id_producto": pid,
                "nombre": nombre,
                "unidad": unidad,
                "consumido": agregado_consumo.get(pid, {}).get("total_consumido", 0),
                "stock": max(0, stock_actual.get(pid, 0))
            })

        return jsonify({"success": True, "comparativa": comparativa})
    except Exception as e:
        print("Error en get_consumo_comparative:", e)
        import traceback
        return jsonify({"success": False, "msg": f"Error: {str(e)}\n{traceback.format_exc()}"}), 500


@app.route('/stock_producto_sucursal', methods=['POST'])
@login_requerido(rol='Empleado')
def stock_producto_sucursal():
    """Retorna el stock disponible de un producto en la sucursal del empleado."""
    try:
        data = request.get_json()
        id_producto = data.get('id_producto')
        id_sucursal = session.get('branch')

        if not (id_producto and id_sucursal):
            return jsonify({"success": False, "stock": 0})

        inv = supabase.table("inventario") \
            .select("cantidad") \
            .eq("id_producto", id_producto) \
            .eq("id_local", id_sucursal) \
            .execute()

        total = sum(lote.get("cantidad", 0) for lote in (inv.data or []))
        return jsonify({"success": True, "stock": total})

    except Exception as e:
        print("Error en stock_producto_sucursal:", e)
        return jsonify({"success": False, "stock": 0})

@app.route('/Em_Inicio', methods=['GET', 'POST'])
@login_requerido(rol='Empleado')
def Em_Inicio():
    try:
        branch_id = session.get('branch')
        generar_notificaciones_caducidad()
        generar_notificaciones_stock_bajo(branch_id)
        eliminar_notificaciones_caducadas()
        
        branch_name = session.get('branch_name')
        if not branch_name and branch_id:
            try:
                sucursal_query = supabase.table("locales").select("nombre").eq("id_local", int(branch_id)).single().execute()
                if sucursal_query.data:
                    branch_name = sucursal_query.data['nombre']
                    session['branch_name'] = branch_name
            except Exception as e:
                print("Error al recuperar nombre de sucursal:", e)

        branch_inventario_ids = set()
        if branch_id:
            try:
                inv_res = supabase.table("inventario").select("id_inventario").eq("id_local", int(branch_id)).execute()
                if inv_res.data:
                    branch_inventario_ids = {item["id_inventario"] for item in inv_res.data if item.get("id_inventario")}
            except Exception as e:
                print("Error al consultar inventario de la sucursal:", e)

        try:
            todas_response = supabase.table("notificaciones").select("*").order("fecha", desc=True).execute()
            todas = todas_response.data if todas_response.data else []
        except Exception as db_error:
            print(f"Error al consultar notificaciones: {db_error}")
            todas = []

        todas_filtradas = []
        for n in todas:
            mensaje = n.get("mensaje", "")
            if mensaje is not None and str(mensaje).strip() != "":
                tipo = n.get("tipo")
                # Filtramos las notificaciones según la sucursal del empleado
                if tipo in ["stock_bajo", "stock_agotado"]:
                    if branch_name and branch_name.lower() in mensaje.lower():
                        todas_filtradas.append(n)
                elif tipo == "caducidad":
                    if n.get("id_inventario") in branch_inventario_ids:
                        todas_filtradas.append(n)
                else:
                    todas_filtradas.append(n)

        if not todas_filtradas:
            notificacion_prueba = {
                "mensaje": "BIENVENIDO/AL SISTEMA - Notificaciones apareceran aqui",
                "fecha_formateada": datetime.now().strftime("%d de %B de %Y, %I:%M %p"),
                "leido": False
            }
            todas_filtradas.append(notificacion_prueba)

        try:
            locale.setlocale(locale.LC_TIME, "es_ES.utf8")
        except:
            try:
                locale.setlocale(locale.LC_TIME, "es_CO.utf8")
            except:
                pass

        for noti in todas_filtradas:
            if noti.get("fecha") and not noti.get("fecha_formateada"):
                try:
                    fecha_str = noti["fecha"]
                    if 'T' in fecha_str:
                        fecha_obj = datetime.fromisoformat(fecha_str.replace('Z', '+00:00'))
                    else:
                        fecha_obj = datetime.strptime(fecha_str, "%Y-%m-%d %H:%M:%S")
                    
                    noti["fecha_formateada"] = fecha_obj.strftime("%d de %B de %Y, %I:%M %p").capitalize()
                except Exception as date_error:
                    print(f"Error al formatear fecha {noti['fecha']}: {date_error}")
                    noti["fecha_formateada"] = noti["fecha"]

        notificaciones = todas_filtradas[:3]
        total_notificaciones = len(todas_filtradas)
        restantes = max(0, total_notificaciones - 3)

        http_response = make_response(render_template(
            "Em_templates/Em_Inicio.html",
            notificaciones=notificaciones,
            restantes=restantes,
            total_notificaciones=total_notificaciones
        ))
        http_response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        http_response.headers['Pragma'] = 'no-cache'
        http_response.headers['Expires'] = '-1'
        return http_response
        
    except Exception as e:
        print(f"Error critico al cargar pagina de inicio del empleado: {e}")
        import traceback
        traceback.print_exc()
        return render_template("Em_templates/Em_Inicio.html", 
                             notificaciones=[], 
                             restantes=0, 
                             total_notificaciones=0), 500

@app.route('/Em_Consumo')
@login_requerido(rol='Empleado')
def Em_Consumo():
    return render_template('Em_templates/Em_Consumo.html')

@app.route('/Em_Rpedido', methods=['GET', 'POST'])
@login_requerido(rol='Empleado')
def Em_Rpedido():
    return render_template("Em_templates/Em_Rpedido.html")

@app.route("/registrar_pedido", methods=["POST"])
@login_requerido(rol='Empleado')
def registrar_pedido():
    if not session.get("logged_in") or session.get("role") != "Empleado":
        return jsonify({"success": False, "msg": "No autorizado"}), 401

    try:
        data = request.get_json()
        id_local = session.get("branch")
        productos = data.get("Productos")
        print(f"DEBUG registrar_pedido: id_local={id_local}, productos={productos}")
        if not (id_local and productos and isinstance(productos, list) and len(productos) > 0):
            return jsonify({"success": False, "msg": "Datos invalidos", "debug": f"local={id_local}, len={len(productos) if productos else 0}"}), 400

        for prod in productos:
            # Corregido: Usar 'Cantidad' con C mayuscula para coincidir con el frontend
            if float(prod.get("Cantidad", 0)) <= 0:
                return jsonify({"success": False, "msg": "La cantidad de todos los productos debe ser mayor a cero."}), 400

        # Corregido: Ya no se inserta en 'inventario' aqui. 
        # El stock se incrementara solo cuando se RECIBE el pedido en Em_Rordenes.

        # 1. Crear el pedido principal
        pedido_res = supabase.table("pedido").insert({
            "cedula": session.get("cedula"),
            "estado": "Pendiente",
            "fecha_pedido": datetime.now().isoformat()
        }).execute()

        if not (pedido_res.data and len(pedido_res.data) > 0):
            return jsonify({"success": False, "msg": "No se pudo registrar el pedido"}), 500

        id_pedido = pedido_res.data[0]["id_pedido"]

        # 2. Registrar los detalles del pedido
        for prod in productos:
            id_producto = prod.get("Id_Producto")
            cantidad = prod.get("Cantidad")

            if not (id_producto and cantidad):
                continue

            try:
                id_producto = int(id_producto)
                cantidad = int(cantidad)
            except (ValueError, TypeError):
                continue

            if cantidad < 1 or cantidad > 500:
                return jsonify({"success": False, "msg": f"Cantidad invalida para {prod.get('Nombre', 'producto')}. Maximo 500."}), 400

            supabase.table("detalle_pedido").insert({
                "id_pedido": id_pedido,
                "id_producto": id_producto,
                "cantidad": cantidad,
                "fecha_pedido": datetime.now().isoformat()
            }).execute()

        return jsonify({
            "success": True,
            "msg": f"Pedido #{id_pedido} registrado con exito. Queda en estado 'Pendiente' hasta su recepcion."
        })
    except Exception as e:
        print("Error al registrar pedido:", e)
        return jsonify({"success": False, "msg": f"Error en el servidor: {str(e)}"}), 500

@app.route("/buscar_producto_empleado", methods=["POST"])
@login_requerido(rol='Empleado')
def buscar_producto_empleado():
    try:
        data = request.get_json()
        termino = data.get("termino", "").strip()
        query = supabase.table("productos").select("id_producto, nombre, categoria, unidad, foto").eq("habilitado", True)

        if termino:
            query = query.or_(f"nombre.ilike.%{termino}%,categoria.ilike.%{termino}%")

        result = query.order("nombre").execute()
        productos = result.data or []

        for prod in productos:
            if not prod.get("foto"):
                prod["foto"] = "/static/image/default.png"

        return jsonify({"success": True, "productos": productos})
    except Exception as e:
        print("Error en busqueda de producto (empleado):", e)
        return jsonify({"success": False, "msg": "Error al obtener productos"}), 500

@app.route('/Em_Rordenes', methods=['GET', 'POST'])
@login_requerido(rol='Empleado')
def Em_Rordenes():
    try:
        if request.method == 'POST':
            data = request.get_json()
            if not data:
                return jsonify({"success": False, "msg": "No se recibieron datos."}), 400

            id_pedido = data.get("id_pedido")
            id_producto = data.get("id_producto")
            cantidad = data.get("cantidad")
            fecha_caducidad = data.get("fecha_caducidad")

            if not all([id_pedido, id_producto, cantidad, fecha_caducidad]):
                return jsonify({"success": False, "msg": "Completa todos los campos."}), 400

            try:
                id_producto = int(id_producto)
                cantidad = int(cantidad)
                fecha_cad_dt = datetime.fromisoformat(fecha_caducidad).date()
            except Exception as e:
                return jsonify({"success": False, "msg": f"Error de tipo: {e}"}), 400

            if cantidad < 1 or cantidad > 1000:
                return jsonify({"success": False, "msg": "La cantidad debe estar entre 1 y 1000."}), 400

            hoy = date.today()
            if fecha_cad_dt <= hoy:
                return jsonify({"success": False, "msg": "La fecha de caducidad debe ser posterior a hoy."}), 400

            inv_res = supabase.table("inventario")\
                .select("*")\
                .eq("id_local", session.get("branch"))\
                .eq("id_producto", id_producto)\
                .execute()

            inventarios = inv_res.data or []
            
            try:
                # Al recibir, SIEMPRE creamos un nuevo registro (lote) en el inventario
                # para manejar correctamente las fechas de caducidad (FIFO).
                supabase.table("inventario").insert({
                    "id_local": session.get("branch"),
                    "id_producto": id_producto,
                    "cantidad": cantidad,
                    "fecha_ingreso": hoy.isoformat(),
                    "fecha_caducidad": fecha_cad_dt.isoformat(),
                    "stock_minimo": 0
                }).execute()
                
                # Opcional: Podriamos marcar el detalle como 'Recibido' si tuvieramos esa columna en detalle_pedido.
                # Por ahora, simplemente confirmamos la recepcion.
                
            except Exception as e:
                return jsonify({"success": False, "msg": f"Error al gestionar inventario: {e}"}), 500

            return jsonify({"success": True, "msg": "Producto recibido y sumado al inventario con exito."})

        pedidos = supabase.table("pedido")\
            .select("id_pedido, estado, fecha_pedido")\
            .eq("estado", "Pendiente")\
            .order("id_pedido", desc=True)\
            .execute().data or []

        detalles = supabase.table("detalle_pedido")\
            .select("id_pedido, id_producto, cantidad, productos(nombre, categoria, unidad, foto)")\
            .execute().data or []

        pedidos_dict = {p["id_pedido"]: {"info": p, "productos": []} for p in pedidos}
        for d in detalles:
            if d["id_pedido"] in pedidos_dict:
                pedidos_dict[d["id_pedido"]]["productos"].append(d)

        return render_template("Em_templates/Em_Rordenes.html", pedidos=pedidos_dict)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "msg": str(e)}), 500

@app.route('/actualizar_estado', methods=['POST'])
@login_requerido(rol='Empleado')
def actualizar_estado():
    try:
        data = request.get_json()
        if not data or 'id_pedido' not in data:
            return jsonify({"success": False, "msg": "No se recibio id_pedido"}), 400

        try:
            id_pedido = int(data['id_pedido'])
        except (ValueError, TypeError):
            return jsonify({"success": False, "msg": "id_pedido invalido"}), 400

        supabase.table("pedido").update({"estado": "Recibido"})\
            .eq("id_pedido", id_pedido).execute()

        return jsonify({"success": True, "msg": "Pedido actualizado correctamente."})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "msg": str(e)}), 500

@app.route('/Em_Hordenes', methods=['GET'])
@login_requerido(rol='Empleado')
def Em_Hordenes():
    try:
        filtros = {
            "fecha": request.args.get("fecha", ""),
            "categoria": request.args.get("categoria", ""),
            "producto": request.args.get("producto", ""),
            "cantidad": request.args.get("cantidad", ""),
            "unidad": request.args.get("unidad", "")
        }

        id_pedido = request.args.get("id_pedido", "")
        fecha = request.args.get("fecha", "")

        query = supabase.table("pedido") \
            .select("id_pedido, estado, fecha_pedido, detalle_pedido(id_producto, cantidad, productos(nombre, categoria, unidad))") \
            .eq("estado", "Recibido") \
            .order("fecha_pedido", desc=True)

        pedidos = query.execute().data or []

        if id_pedido:
            pedidos = [p for p in pedidos if str(p["id_pedido"]) == str(id_pedido)]
        if fecha:
            pedidos = [p for p in pedidos if (p["fecha_pedido"] or "").split("T")[0] == fecha]

        return render_template("Em_templates/Em_Hordenes.html", pedidos=pedidos)
    except Exception as e:
        print("Error al cargar historial de ordenes:", e)
        return render_template("Em_templates/Em_Hordenes.html", pedidos=[])


if __name__ == '__main__':
    app.run(
        debug=(os.getenv('FLASK_DEBUG', 'False').lower() == 'true'),
        host=os.getenv('HOST', '127.0.0.1'),
        port=int(os.getenv('PORT', '5000'))
    )
