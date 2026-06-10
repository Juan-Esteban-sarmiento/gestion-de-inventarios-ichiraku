from flask import render_template, request, jsonify, redirect, url_for, session, make_response, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import re
import math
import locale
import io
import os
from io import BytesIO
import csv

from extensions import app, supabase, logger
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.piecharts import Pie
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from utils import login_requerido, to_num, generar_notificaciones_caducidad, generar_notificaciones_stock_bajo, eliminar_notificaciones_caducadas, insertar_informe
# 6. ADMINISTRACION - DASHBOARD E INFORMES
# ==============================================================================

@app.route('/Ad_Inicio', methods=['GET', 'POST'])
@login_requerido(rol='Administrador')
def Ad_Inicio():
    try:
        generar_notificaciones_caducidad()
        generar_notificaciones_stock_bajo()
        eliminar_notificaciones_caducadas()
        
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
                todas_filtradas.append(n)

        if not todas_filtradas:
            notificacion_prueba = {
                "mensaje": "NOTIFICACION DE PRUEBA - Sistema funcionando",
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
            "Ad_templates/Ad_Inicio.html",
            notificaciones=notificaciones,
            restantes=restantes,
            total_notificaciones=total_notificaciones
        ))
        http_response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        http_response.headers['Pragma'] = 'no-cache'
        http_response.headers['Expires'] = '-1'
        return http_response
        
    except Exception as e:
        print(f"Error critico al cargar pagina de inicio: {e}")
        import traceback
        traceback.print_exc()
        return render_template("Ad_templates/Ad_Inicio.html", 
                             notificaciones=[], 
                             restantes=0, 
                             total_notificaciones=0), 500


def obtener_rango_fecha(periodo, fecha_str):
    try:
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d")
        if periodo == "diario":
            inicio = fecha.replace(hour=0, minute=0, second=0)
            fin = fecha.replace(hour=23, minute=59, second=59)
        elif periodo == "semanal":
            inicio = fecha - timedelta(days=fecha.weekday())
            inicio = inicio.replace(hour=0, minute=0, second=0)
            fin = inicio + timedelta(days=6, hours=23, minutes=59, seconds=59)
        elif periodo == "mensual":
            inicio = fecha.replace(day=1, hour=0, minute=0, second=0)
            if fecha.month == 12:
                proximo_mes = fecha.replace(year=fecha.year + 1, month=1, day=1)
            else:
                proximo_mes = fecha.replace(month=fecha.month + 1, day=1)
            fin = proximo_mes - timedelta(seconds=1)
        elif periodo == "anual":
            inicio = fecha.replace(month=1, day=1, hour=0, minute=0, second=0)
            fin = fecha.replace(month=12, day=31, hour=23, minute=59, second=59)
        else:
            inicio = fin = fecha
        return inicio.isoformat(), fin.isoformat()
    except:
        return fecha_str, fecha_str

# NOTE: to_num is imported from utils — the local definition below is kept for
# legacy compatibility with this module's PDF helper functions.
def _to_num_local(val):
    try: return round(float(val), 2)
    except: return 0

# --- HELPER DISENO C: MODERN HYBRID ---
def dibujar_sidebar_premium(canvas, doc):
    """Dibuja la barra lateral negra y el branding vertical del Diseno C"""
    canvas.saveState()
    # 1. Barra lateral negra (#111)
    canvas.setFillColor(colors.HexColor("#111111"))
    canvas.rect(0, 0, 50, letter[1], fill=1, stroke=0)
    
    # 2. Branding Vertical
    canvas.rotate(90)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 14)
    # Posicionamiento vertical (recordar que rotamos 90 grados)
    canvas.drawString(100, -32, "ICHIRAKU RAMEN")
    
    canvas.setFillColor(colors.HexColor("#E63900"))
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawString(240, -32, "| SISTEMA DE GESTION")
    
    canvas.restoreState()

@app.route('/generar_reporte_personalizado', methods=['POST'])
@login_requerido(rol='Administrador')
def generar_reporte_personalizado():
    try:
        id_l = request.form.get('id_local')
        periodo = request.form.get('periodo', 'diario')
        fecha_base = request.form.get('fecha', datetime.now().strftime("%Y-%m-%d"))
        
        if not id_l: return jsonify({"success": False, "msg": "Debes seleccionar un local para generar el reporte."}), 400
        
        f_ini, f_fin = obtener_rango_fecha(periodo, fecha_base)
        
        # 1. Obtener datos del local
        local_info = supabase.table("locales").select("nombre").eq("id_local", id_l).execute()
        nombre_local = local_info.data[0]["nombre"] if local_info.data else "Desconocido"

        # 2. Obtener Consumo del periodo con detalles
        cons_res = supabase.table("consumo").select("*, consumo_detalle(*, productos(nombre, unidad))")\
            .eq("id_local", id_l).gte("fecha", f_ini).lte("fecha", f_fin).execute()
        consumos = cons_res.data or []

        # 3. Procesar y categorizar: Ventas vs Merma
        resumen_productos = {} # {id_prod: {nombre, unidad, venta: 0, merma: 0}}
        total_ventas_count = 0
        total_merma_items = 0

        for c in consumos:
            is_merma = "[MERMA]" in (c.get("observacion") or "")
            if is_merma:
                total_merma_items += 1
            else:
                total_ventas_count += c.get("cantidad_platos", 0)

            for det in c.get("consumo_detalle", []):
                p = det.get("productos")
                if not p: continue
                pid = det["id_producto"]
                if pid not in resumen_productos:
                    resumen_productos[pid] = {
                        "nombre": p["nombre"],
                        "unidad": p["unidad"],
                        "venta": 0,
                        "merma": 0
                    }
                
                cant = float(det["cantidad_consumida"])
                if is_merma:
                    resumen_productos[pid]["merma"] += cant
                else:
                    resumen_productos[pid]["venta"] += cant

        # Generar PDF con ReportLab - DISENO C
        buffer = io.BytesIO()
        # Margen izquierdo amplio para el sidebar (50 sidebar + 20 espacio)
        doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=70, topMargin=50, bottomMargin=50)
        styles = getSampleStyleSheet()
        
        # Estilos personalizados para Diseno C
        style_title = styles['Title']
        style_title.alignment = 0 # Izquierda
        style_title.fontName = "Helvetica-Bold"
        style_title.fontSize = 22
        style_title.textColor = colors.HexColor("#111111")
        
        style_h2 = styles['Heading2']
        style_h2.textColor = colors.HexColor("#E63900")
        style_h2.fontSize = 14
        style_h2.borderPadding = 5
        
        elements = []
        
        # Titulo y Encabezado
        elements.append(Paragraph(f"INFORME TECNICO DE INVENTARIO", style_title))
        elements.append(Spacer(1, 5))
        
        # Barra de acento rojo bajo el titulo
        elements.append(Table([[""]], colWidths=[480], style=[('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#E63900"))]))
        elements.append(Spacer(1, 15))

        elements.append(Paragraph(f"<b>Sede:</b> {nombre_local.upper()} | <b>Periodo:</b> {periodo.upper()}", styles['Normal']))
        elements.append(Paragraph(f"<b>Rango:</b> {f_ini[:10]} - {f_fin[:10]}", styles['Normal']))
        elements.append(Spacer(1, 25))

        # Resumen Ejecutivo (Con diseno de tarjetas minimalistas)
        elements.append(Paragraph("1. Resumen Ejecutivo (Metricas Clave)", style_h2))
        elements.append(Spacer(1, 10))
        
        resumen_data = [
            ["PLATILLOS VENDIDOS", "MERMA / ERROR", "ESTADO OPERATIVO"],
            [f"{total_ventas_count}", f"{total_merma_items}", "Auditado"]
        ]
        t_res = Table(resumen_data, colWidths=[160, 160, 160])
        t_res.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.grey),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, 1), 16),
            ('TEXTCOLOR', (0, 1), (0, 1), colors.black),
            ('TEXTCOLOR', (1, 1), (1, 1), colors.HexColor("#E63900")),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(t_res)
        elements.append(Spacer(1, 30))

        # Detalle por Producto
        elements.append(Paragraph("2. Consumo Detallado por Insumo", style_h2))
        elements.append(Spacer(1, 12))
        
        data_prod = [["INSUMO", "UNIDAD", "VENTAS", "MERMA", "TOTAL"]]
        
        sorted_products = sorted(resumen_productos.values(), key=lambda x: x['nombre'])
        for p in sorted_products:
            total = p['venta'] + p['merma']
            data_prod.append([
                p['nombre'].upper(),
                p['unidad'],
                round(p['venta'], 2),
                round(p['merma'], 2),
                round(total, 2)
            ])

        t_prod = Table(data_prod, colWidths=[180, 70, 70, 70, 90])
        t_prod.setStyle(TableStyle([
            # Minimal header con subrayado rojo
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor("#E63900")),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            
            # Body clean
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor("#333333")),
            ('ALIGN', (2, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 1), (-1, -1), 0.25, colors.lightgrey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9F9F9")]),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ]))
        elements.append(t_prod)
        elements.append(Spacer(1, 30))

        # Historial de Transacciones
        elements.append(Paragraph("3. Historial de Actividad (Operadores)", style_h2))
        elements.append(Spacer(1, 12))
        
        historial_data = [["FECHA/HORA", "TIPO / DESCRIPCION", "EMPLEADO"]]
        
        for c in sorted(consumos, key=lambda x: x.get('fecha', ''), reverse=True):
            obs = c.get("observacion", "")
            try:
                fecha_str = datetime.fromisoformat(c["fecha"].replace('Z', '+00:00')).strftime("%d/%m %H:%M")
            except:
                fecha_str = "N/A"
                
            # Extraer empleado
            empleado = "Desconocido"
            import re
            match_emp = re.search(r"\[Emp: (.*?)\]", obs)
            if match_emp:
                empleado = match_emp.group(1)
                obs = obs.replace(f"[Emp: {empleado}]", "").strip()
                
            desc = obs
            if len(desc) > 60:
                desc = desc[:57] + "..."
                
            historial_data.append([fecha_str, desc, empleado.upper()])
            
        t_hist = Table(historial_data, colWidths=[90, 270, 120])
        t_hist.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor("#E63900")),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor("#444444")),
            ('GRID', (0, 1), (-1, -1), 0.2, colors.lightgrey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9F9F9")]),
            ('TOPPADDING', (0, 1), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(t_hist)
        
        elements.append(Spacer(1, 40))
        elements.append(Paragraph(f"<i>Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')} - Sistema Ichiraku</i>", styles['Italic']))

        # Build con Sidebar
        doc.build(elements, onFirstPage=dibujar_sidebar_premium, onLaterPages=dibujar_sidebar_premium)
        buffer.seek(0)
        
        filename = f"Informe_{nombre_local}_{fecha_base}_{periodo}.pdf"
        
        # 5. Persistencia en la base de datos para el historial
        try:
            nuevo_informe = {
                "fecha_creacion": datetime.now().isoformat(),
                "tipo": "inventario_premium",
                "fecha_inicio": f_ini[:10],
                "fecha_fin": f_fin[:10],
                "pedidos_ids": {
                    "id_local": id_l,
                    "nombre_local": nombre_local,
                    "periodo": periodo,
                    "fecha_base": fecha_base
                }
            }
            supabase.table("informe").insert(nuevo_informe).execute()
        except Exception as db_e:
            print(f"Error al persistir informe premium: {db_e}")

        response = make_response(buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename={filename}'
        return response
        
    except Exception as e:
        return jsonify({"success": False, "msg": f"Error generando reporte: {str(e)}"}), 500

@app.route('/Ad_Dinformes', methods=['GET'])
@login_requerido(rol='Administrador')
def Ad_Dinformes():
    try:
        ultimo_informe = None
        informes = supabase.table("informe").select("*").order("id_informe", desc=True).limit(1).execute()
        
        if informes.data:
            ultimo_informe = informes.data[0]
        
        locales = supabase.table("locales").select("*").execute().data or []
        today = datetime.now().strftime("%Y-%m-%d")
        
        return render_template("Ad_templates/Ad_Dinformes.html", 
                               ultimo_informe=ultimo_informe, 
                               locales=locales,
                               today=today)
    except Exception as e:
        print("Error al cargar pagina de informes:", e)
        return render_template("Ad_templates/Ad_Dinformes.html", ultimo_informe=None, locales=[], today="")

def crear_informe_consolidado(pedidos, fecha):
    try:
        fecha_inicio = f"{fecha}T00:00:00"
        fecha_fin = f"{fecha}T23:59:59"
        
        informe_existente = supabase.table("informe").select("*") \
            .gte("fecha_creacion", fecha_inicio) \
            .lte("fecha_creacion", fecha_fin) \
            .execute().data
        
        if informe_existente:
            return False
        
        nuevo_informe = {
            "fecha_creacion": datetime.now().isoformat(),
            "tipo": "diario_consolidado",
            "total_pedidos": len(pedidos)
        }
        
        result = supabase.table("informe").insert(nuevo_informe).execute()
        
        if result.data:
            return True
        return False
        
    except Exception as e:
        print("Error al crear informe consolidado:", e)
        return False


def generar_pdf_consolidado(informe_id, pedidos):
    try:
        buffer = io.BytesIO()
        # Margen izquierdo amplio para el sidebar
        doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=75, rightMargin=40, topMargin=50, bottomMargin=50)
        styles = getSampleStyleSheet()
        
        # Estilos personalizados para Diseno C
        style_title = styles['Title']
        style_title.alignment = 0 
        style_title.fontName = "Helvetica-Bold"
        style_title.fontSize = 20
        style_title.textColor = colors.HexColor("#111111")
        
        style_h2 = styles['Heading2']
        style_h2.textColor = colors.HexColor("#E63900")
        style_h2.fontSize = 14
        
        elements = []

        # Titulo principal
        elements.append(Paragraph(f"INFORME DIARIO CONSOLIDADO", style_title))
        elements.append(Spacer(1, 5))
        
        # Barra de acento rojo
        elements.append(Table([[""]], colWidths=[480], style=[('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#E63900"))]))
        elements.append(Spacer(1, 15))
        
        # Informacion del informe
        fecha_actual = datetime.now().strftime('%d de %B, %Y')
        info_data = [
            [Paragraph(f"<b>ID INFORME:</b> #{informe_id}", styles['Normal']),
             Paragraph(f"<b>FECHA GENERACION:</b> {fecha_actual}", styles['Normal'])]
        ]
        info_table = Table(info_data, colWidths=[240, 240])
        info_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 20))

        # ========================
        # PROCESAR DATOS
        # ========================
        total_productos = 0
        categorias_totales = {}
        locales_participantes = set()
        productos_detallados = []
        horas_pedidos = []

        if not isinstance(pedidos, list):
            pedidos = []

        for pedido in pedidos:
            try:
                if not isinstance(pedido, dict):
                    continue
                    
                pedido_id = pedido.get('id_pedido')
                if pedido_id is None:
                    continue

                # Obtener detalles del pedido
                try:
                    detalles = supabase.table("detalle_pedido").select("id_producto, cantidad")\
                        .eq("id_pedido", pedido_id).execute().data or []
                except Exception as e:
                    detalles = []

                # Obtener informacion del local
                local_nombre = "No especificado"

                try:
                    id_inventario = pedido.get("id_inventario")

                    if id_inventario:
                        inventario_result = supabase.table("inventario") \
                            .select("id_local") \
                            .eq("id_inventario", id_inventario) \
                            .execute()

                        if inventario_result.data:
                            id_local = inventario_result.data[0].get("id_local")

                            if id_local:
                                local_result = supabase.table("locales") \
                                    .select("nombre") \
                                    .eq("id_local", id_local) \
                                    .execute()

                                if local_result.data:
                                    local_nombre = local_result.data[0].get("nombre", "No especificado")
                                    locales_participantes.add(local_nombre)

                except Exception as e:
                    print("Error obteniendo local:", e)

                # Obtener fecha y hora
                fecha_pedido_raw = pedido.get("fecha_pedido")
                fecha_pedido_str = fecha_pedido_raw if isinstance(fecha_pedido_raw, str) else datetime.now().isoformat()
                
                try:
                    hora = datetime.fromisoformat(fecha_pedido_str).strftime("%H:%M")
                    horas_pedidos.append(hora)
                except Exception:
                    hora = "N/A"

                # Procesar productos del pedido
                for detalle in detalles:
                    if not isinstance(detalle, dict):
                        continue
                        
                    cantidad_detalle = detalle.get('cantidad', 0)
                    id_producto = detalle.get('id_producto')
                    
                    if not id_producto:
                        continue

                    total_productos += int(cantidad_detalle)
                    
                    try:
                        producto_result = supabase.table("productos").select("nombre, categoria, unidad")\
                            .eq("id_producto", id_producto).execute()
                        
                        if producto_result.data:
                            producto_info = producto_result.data[0]
                            cat = producto_info.get('categoria', 'Sin categoria')
                            categorias_totales[cat] = categorias_totales.get(cat, 0) + cantidad_detalle
                            
                            producto_detalle = {
                                'pedido_id': int(pedido_id) if pedido_id else 0,
                                'local': str(local_nombre),
                                'producto': str(producto_info.get('nombre', 'Desconocido')),
                                'categoria': str(cat),
                                'cantidad': int(cantidad_detalle),
                                'unidad': str(producto_info.get('unidad', 'und')),
                                'hora': str(hora)
                            }
                            productos_detallados.append(producto_detalle)
                    except Exception as e:
                        continue
                        
            except Exception as e:
                continue

        # Calcular metricas
        hora_primero = min(horas_pedidos) if horas_pedidos else "N/A"
        hora_ultimo = max(horas_pedidos) if horas_pedidos else "N/A"

        # ========================
        # RESUMEN EJECUTIVO (MODERN CARDS)
        # ========================
        elements.append(Paragraph("1. Resumen Ejecutivo de Operacion", style_h2))
        elements.append(Spacer(1, 12))
        
        res_data = [
            ["TOTAL PEDIDOS", "PRODUCTOS", "OPERACION", "LOCALES"],
            [f"{len(pedidos)}", f"{total_productos}", f"{hora_primero}-{hora_ultimo}", f"{len(locales_participantes)}"]
        ]
        t_res = Table(res_data, colWidths=[120, 120, 120, 120])
        t_res.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.grey),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, 1), 14),
            ('TEXTCOLOR', (0, 1), (-1, 1), colors.black),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(t_res)
        elements.append(Spacer(1, 25))
        
        if locales_participantes:
            locs = ", ".join(sorted(locales_participantes))
            elements.append(Paragraph(f"<b>Locales impactados:</b> {locs}", styles['Normal']))
            elements.append(Spacer(1, 20))

        elements.append(Spacer(1, 30))

        # ========================
        # DISTRIBUCION POR CATEGORIAS (CLEAN TABLE)
        # ========================
        if categorias_totales:
            elements.append(Paragraph("2. Distribucion General por Categorias", style_h2))
            elements.append(Spacer(1, 12))
            
            categorias_data = [["CATEGORIA", "CANTIDAD", "PORCENTAJE"]]
            total_categorias = sum(categorias_totales.values())
            
            for cat, cant in sorted(categorias_totales.items(), key=lambda x: x[1], reverse=True):
                porc = (cant / total_categorias) * 100 if total_categorias > 0 else 0
                categorias_data.append([cat.upper(), f"{cant} und", f"{porc:.1f}%"])
            
            t_cat = Table(categorias_data, colWidths=[200, 140, 140])
            t_cat.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('LINEBELOW', (0, 0), (-1, 0), 1.5, colors.HexColor("#E63900")),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9F9F9")]),
                ('TOPPADDING', (0, 1), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            ]))
            elements.append(t_cat)
            elements.append(Spacer(1, 30))

        # ========================
        # DETALLE DE PEDIDOS - AGRUPADO POR LOCAL
        # ========================
        if productos_detallados:
            elements.append(Paragraph(
                "<font size=14 color='#000000'><b>DETALLE DE PEDIDOS</b></font>",
                styles['Heading2']
            ))
            elements.append(Spacer(1, 15))

            # Paso 1: agrupar productos por pedido (con local, fecha y hora)
            pedidos_agrupados = {}
            for producto in productos_detallados:
                if not isinstance(producto, dict):
                    continue
                pedido_id = producto.get('pedido_id')
                if pedido_id is None:
                    continue
                if pedido_id not in pedidos_agrupados:
                    pedidos_agrupados[pedido_id] = {
                        'local': producto.get('local', 'No especificado'),
                        'hora': producto.get('hora', 'N/A'),
                        'fecha': producto.get('fecha', ''),
                        'productos': [],
                        'total_cantidad': 0
                    }
                pedidos_agrupados[pedido_id]['productos'].append(producto)
                pedidos_agrupados[pedido_id]['total_cantidad'] += producto.get('cantidad', 0)

            # Paso 2: agrupar pedidos por local
            locales_agrupados = {}
            for pedido_id, info in sorted(pedidos_agrupados.items()):
                local = info['local']
                if local not in locales_agrupados:
                    locales_agrupados[local] = []
                locales_agrupados[local].append((pedido_id, info))

            # Paso 3: renderizar seccion por local
            for local_nombre, pedidos_local in sorted(locales_agrupados.items()):
                num_pedidos = len(pedidos_local)

                # Encabezado del local con fondo rojo
                local_header_data = [[
                    Paragraph(
                        f"<font color='white'><b>LOCAL: {local_nombre.upper()}</b>  —  {num_pedidos} pedido{'s' if num_pedidos != 1 else ''}</font>",
                        styles['Normal']
                    )
                ]]
                local_header_table = Table(local_header_data, colWidths=[480])
                local_header_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#E63900")),
                    ('LEFTPADDING', (0, 0), (-1, -1), 10),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                    ('TOPPADDING', (0, 0), (-1, -1), 7),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
                ]))
                elements.append(local_header_table)
                elements.append(Spacer(1, 8))

                for pedido_id, info in pedidos_local:
                    if not info.get('productos'):
                        continue

                    # Encabezado del pedido con fecha y hora
                    fecha_hora = f"{info.get('fecha', '')} {info['hora']}".strip()
                    elements.append(Paragraph(
                        f"<b>PEDIDO #{pedido_id}</b>  |  Fecha: {fecha_hora}",
                        styles['Normal']
                    ))
                    elements.append(Spacer(1, 4))

                    # Tabla de productos
                    table_data = [["PRODUCTO", "CANTIDAD"]]
                    for p in info['productos']:
                        table_data.append([p['producto'].upper(), f"{p['cantidad']} {p['unidad']}"])

                    pedido_table = Table(table_data, colWidths=[340, 140])
                    pedido_table.setStyle(TableStyle([
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 8),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#666666")),
                        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.lightgrey),
                        ('FONTSIZE', (0, 1), (-1, -1), 8),
                        ('GRID', (0, 1), (-1, -1), 0.1, colors.lightgrey),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#FDFDFD")]),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                        ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ]))
                    elements.append(pedido_table)
                    elements.append(Spacer(1, 12))

                elements.append(Spacer(1, 10))

        # Pie de pagina footer
        elements.append(Spacer(1, 30))
        elements.append(Paragraph(f"<i>Informe Consolidado Ichiraku Ramen - Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}</i>", styles['Italic']))

        # Construir PDF con Sidebar
        doc.build(elements, onFirstPage=dibujar_sidebar_premium, onLaterPages=dibujar_sidebar_premium)
        buffer.seek(0)
        return buffer
        
    except Exception as e:
        print("Error al generar PDF consolidado:", e)
        import traceback
        traceback.print_exc()
        return None

def descargar_informe_consolidado_individual(id_informe):
    try:
        informe_result = supabase.table("informe").select("*").eq("id_informe", id_informe).execute()
        if not informe_result.data:
            return jsonify({"success": False, "msg": "Informe consolidado no encontrado"}), 404
        
        informe = informe_result.data[0]
        fecha_creacion = datetime.fromisoformat(informe["fecha_creacion"])
        fecha = fecha_creacion.date()
        
        # OBTENER PEDIDOS DE ESA FECHA
        todos_pedidos = supabase.table("pedido").select("*").execute().data or []
        
        # FILTRAR PEDIDOS POR FECHA
        pedidos_hoy = []
        for p in todos_pedidos:
            try:
                if isinstance(p, dict) and p.get("fecha_pedido"):
                    fecha_pedido = datetime.fromisoformat(p["fecha_pedido"]).date()
                    if fecha_pedido == fecha:
                        pedidos_hoy.append(p)
            except Exception as e:
                print(f"Error procesando pedido {p}: {e}")
                continue
        
        if not pedidos_hoy:
            return jsonify({"success": False, "msg": "No hay pedidos para esta fecha."})
        
        buffer = generar_pdf_consolidado(id_informe, pedidos_hoy)
        if not buffer:
            return jsonify({"success": False, "msg": "Error al generar el PDF consolidado."})
        
        response = make_response(buffer.read())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=informe_diario_consolidado_{fecha}.pdf'
        return response
        
    except Exception as e:
        print(f"Error al descargar informe consolidado individual {id_informe}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "msg": f"Error: {e}"})


@app.route('/generar_informe_diario', methods=['POST'])
@login_requerido(rol='Administrador')
def generar_informe_diario():
    try:
        hoy = datetime.now().date()
        
        todos_pedidos = supabase.table("pedido").select("*").execute()
        
        if not todos_pedidos.data:
            return jsonify({"success": False, "msg": "No hay pedidos registrados en el sistema."})
        
        pedidos_hoy = [p for p in todos_pedidos.data 
                      if datetime.fromisoformat(p["fecha_pedido"]).date() == hoy]
        
        if not pedidos_hoy:
            return jsonify({"success": False, "msg": "No hay pedidos registrados para hoy."})
        
        fecha_inicio = f"{hoy}T00:00:00"
        fecha_fin = f"{hoy}T23:59:59"
        
        informe_existente = supabase.table("informe").select("*") \
            .gte("fecha_creacion", fecha_inicio) \
            .lte("fecha_creacion", fecha_fin) \
            .eq("tipo", "diario_consolidado") \
            .execute()
        
        # Eliminamos la restriccion de un solo informe por dia para permitir el historial solicitado por el usuario
        
        nuevo_informe = {
            "fecha_creacion": datetime.now().isoformat(),
            "tipo": "diario_consolidado",
            "total_pedidos": len(pedidos_hoy),
            "id_inf_pedido": None
        }
        
        result = supabase.table("informe").insert(nuevo_informe).execute()
        
        if result.data:
            informe_id = result.data[0]['id_informe']
            
            return jsonify({
                "success": True, 
                "msg": f"Informe diario generado exitosamente con {len(pedidos_hoy)} pedidos.",
                "informe_id": informe_id
            })
        else:
            return jsonify({"success": False, "msg": "No se pudo guardar el informe en la base de datos."})
            
    except Exception as e:
        print(f"Error al generar informe diario: {e}")
        return jsonify({"success": False, "msg": f"Error: {str(e)}"})

@app.route('/obtener_ultimo_informe', methods=['GET'])
@login_requerido(rol='Administrador')
def obtener_ultimo_informe():
    try:
        informes = supabase.table("informe").select("*").order("id_informe", desc=True).limit(1).execute()
        
        if informes.data:
            return jsonify({"success": True, "informe": informes.data[0]})
        else:
            return jsonify({"success": False, "msg": "No hay informes generados."})
            
    except Exception as e:
        print("Error al obtener ultimo informe:", e)
        return jsonify({"success": False, "msg": f"Error: {e}"})

@app.route('/buscar_informe', methods=['POST'])
@login_requerido(rol='Administrador')
def buscar_informe():
    try:
        data = request.get_json()
        id_informe, fecha = data.get("id_informe"), data.get("fecha")
        if id_informe:
            informes = supabase.table("informe").select("*").eq("id_informe", id_informe).execute().data
        elif fecha:
            informes = supabase.table("informe").select("*") \
                .gte("fecha_creacion", f"{fecha}T00:00:00") \
                .lte("fecha_creacion", f"{fecha}T23:59:59") \
                .execute().data
        else:
            return jsonify({"success": False, "msg": "Debes ingresar un ID o una fecha."})
        return jsonify({"success": True, "informes": informes}) if informes else jsonify({"success": False, "msg": "No se encontraron informes."})
    except Exception as e:
        print("Error al buscar informe:", e)
        return jsonify({"success": False, "msg": f"Error: {e}"})
    
@app.route('/descargar_informe_diario_consolidado', methods=['GET'])
@login_requerido(rol='Administrador')
def descargar_informe_diario_consolidado():
    try:
        hoy = datetime.now().date()
        
        fecha_inicio = f"{hoy}T00:00:00"
        fecha_fin = f"{hoy}T23:59:59"
        
        informe = supabase.table("informe").select("*") \
            .gte("fecha_creacion", fecha_inicio) \
            .lte("fecha_creacion", fecha_fin) \
            .eq("tipo", "diario_consolidado") \
            .single().execute().data
        
        if not informe:
            return jsonify({"success": False, "msg": "No hay informe diario generado para hoy."})
        
        pedidos_hoy = supabase.table("pedido").select("*").execute().data
        pedidos_hoy = [p for p in pedidos_hoy if datetime.fromisoformat(p["fecha_pedido"]).date() == hoy]
        
        buffer = generar_pdf_consolidado(informe['id_informe'], pedidos_hoy)
        if not buffer:
            return jsonify({"success": False, "msg": "Error al generar el PDF."})
        
        response = make_response(buffer.read())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=informe_diario_{hoy}.pdf'
        return response
        
    except Exception as e:
        print("Error al descargar informe diario:", e)
        return jsonify({"success": False, "msg": f"Error: {e}"})


def re_generar_reporte_premium(id_l, periodo, fecha_base):
    # Esta funcion replica la logica de generar_reporte_personalizado sin persistir de nuevo
    try:
        f_ini, f_fin = obtener_rango_fecha(periodo, fecha_base)
        local_info = supabase.table("locales").select("nombre").eq("id_local", id_l).execute()
        nombre_local = local_info.data[0]["nombre"] if local_info.data else "Desconocido"
        cons_res = supabase.table("consumo").select("*, consumo_detalle(*, productos(nombre, unidad))")\
            .eq("id_local", id_l).gte("fecha", f_ini).lte("fecha", f_fin).execute()
        consumos = cons_res.data or []
        resumen_productos = {}
        total_ventas_count = 0
        total_merma_items = 0
        for c in consumos:
            observacion = (c.get("observacion") or "").lower()
            is_merma = (
                "[merma]" in observacion or
                "merma" in observacion
            )
            if is_merma: total_merma_items += 1
            else: total_ventas_count += c.get("cantidad_platos", 0)
            for det in c.get("consumo_detalle", []):
                p = det.get("productos")
                if not p: continue
                pid = det["id_producto"]
                if pid not in resumen_productos:
                    resumen_productos[pid] = {"nombre": p["nombre"], "unidad": p["unidad"], "venta": 0, "merma": 0}
                cant = float(det["cantidad_consumida"])
                if is_merma: resumen_productos[pid]["merma"] += cant
                else: resumen_productos[pid]["venta"] += cant
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=70, topMargin=50, bottomMargin=50)
        styles = getSampleStyleSheet()
        style_title = styles['Title']
        style_title.alignment = 0
        style_title.fontName = "Helvetica-Bold"
        style_title.fontSize = 22
        style_title.textColor = colors.HexColor("#111111")
        style_h2 = styles['Heading2']
        style_h2.textColor = colors.HexColor("#E63900")
        style_h2.fontSize = 14
        elements = []
        elements.append(Paragraph(f"INFORME TECNICO DE INVENTARIO", style_title))
        elements.append(Spacer(1, 5))
        elements.append(Table([[""]], colWidths=[480], style=[('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#E63900"))]))
        elements.append(Spacer(1, 15))
        elements.append(Paragraph(f"<b>Sede:</b> {nombre_local.upper()} | <b>Periodo:</b> {periodo.upper()}", styles['Normal']))
        elements.append(Paragraph(f"<b>Rango:</b> {f_ini[:10]} - {f_fin[:10]}", styles['Normal']))
        elements.append(Spacer(1, 25))
        elements.append(Paragraph("1. Resumen Ejecutivo (Metricas Clave)", style_h2))
        elements.append(Spacer(1, 10))
        resumen_data = [["PLANTILLAS VENDIDAS", "MERMA / ERROR", "ESTADO OPERATIVO"], [f"{total_ventas_count}", f"{total_merma_items}", "Auditado (H)"]]
        t_res = Table(resumen_data, colWidths=[160, 160, 160])
        t_res.setStyle(TableStyle([('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'), ('FONTSIZE', (0, 0), (-1, 0), 9), ('TEXTCOLOR', (0, 0), (-1, 0), colors.grey), ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('BOTTOMPADDING', (0, 0), (-1, 0), 10), ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'), ('FONTSIZE', (0, 1), (-1, 1), 16), ('TEXTCOLOR', (0, 1), (0, 1), colors.black), ('TEXTCOLOR', (1, 1), (1, 1), colors.HexColor("#E63900")), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
        elements.append(t_res)
        elements.append(Spacer(1, 30))
        elements.append(Paragraph("2. Consumo Detallado por Insumo", style_h2))
        elements.append(Spacer(1, 12))
        data_prod = [["INSUMO", "UNIDAD", "VENTAS", "MERMA", "TOTAL"]]
        sorted_products = sorted(resumen_productos.values(), key=lambda x: x['nombre'])
        for p in sorted_products:
            total = p['venta'] + p['merma']
            data_prod.append([p['nombre'].upper(), p['unidad'], int(p['venta']), int(p['merma']), int(total)])
        t_prod = Table(data_prod, colWidths=[180, 70, 70, 70, 90])
        t_prod.setStyle(TableStyle([('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'), ('FONTSIZE', (0, 0), (-1, 0), 9), ('TEXTCOLOR', (0, 0), (-1, 0), colors.black), ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor("#E63900")), ('BOTTOMPADDING', (0, 0), (-1, 0), 8), ('FONTSIZE', (0, 1), (-1, -1), 9), ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor("#333333")), ('ALIGN', (2, 0), (-1, -1), 'CENTER'), ('GRID', (0, 1), (-1, -1), 0.25, colors.lightgrey), ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9F9F9")]), ('TOPPADDING', (0, 1), (-1, -1), 6), ('BOTTOMPADDING', (0, 1), (-1, -1), 6)]))
        elements.append(t_prod)
        elements.append(Spacer(1, 40))
        elements.append(Paragraph(f"<i>Re-generado el {datetime.now().strftime('%d/%m/%Y %H:%M')} - Historial Ichiraku</i>", styles['Italic']))
        doc.build(elements, onFirstPage=dibujar_sidebar_premium, onLaterPages=dibujar_sidebar_premium)
        buffer.seek(0)
        response = make_response(buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=Informe_Historial_{fecha_base}.pdf'
        return response
    except Exception as e:
        return jsonify({"success": False, "msg": f"Error re-generando: {str(e)}"}), 500

def re_generar_reporte_rango(tipo, fecha_inicio, fecha_fin):
    try:
        informes = supabase.table("informe").select("*").gte("fecha_creacion", fecha_inicio).lte("fecha_creacion", fecha_fin).order("fecha_creacion", desc=True).execute()
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=40, rightMargin=40, topMargin=80, bottomMargin=50)
        styles = getSampleStyleSheet()
        elements = []
        titulo = f"INFORME {tipo.upper()} CONSOLIDADO (HISTORIAL)"
        elements.append(Paragraph(f"<font size=18 color='#000000'><b>{titulo}</b></font>", styles['Normal']))
        elements.append(Spacer(1, 20))
        elements.append(Paragraph(f"Periodo: {fecha_inicio} al {fecha_fin}", styles['Normal']))
        elements.append(Paragraph(f"Total informes base: {len(informes.data)}", styles['Normal']))
        # Aqui podriamos agregar mas detalle si fuera necesario, similar a descargar_informes_rango
        doc.build(elements)
        buffer.seek(0)
        response = make_response(buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=Informe_Consolidado_H.pdf'
        return response
    except Exception as e:
        return jsonify({"success": False, "msg": f"Error re-generando rango: {str(e)}"}), 500

@app.route('/descargar_informe/<int:id_informe>', methods=['GET'])
@login_requerido(rol='Administrador')
def descargar_informe(id_informe):
    try:
        informe_result = supabase.table("informe").select("*").eq("id_informe", id_informe).execute()
        if not informe_result.data:
            return jsonify({"success": False, "msg": "Informe no encontrado"}), 404
        
        informe = informe_result.data[0]
        tipo = informe.get("tipo", "")
        
        if tipo == "diario_consolidado":
            return descargar_informe_consolidado_individual(id_informe)
        
        if tipo == "inventario_premium":
            # Extraer parametros del metadata (pedidos_ids)
            metadata = informe.get("pedidos_ids")
            if not metadata:
                return jsonify({"success": False, "msg": "Metadata del informe no encontrada"}), 404
            
            # Simulamos un request.form para reutilizar la logica o simplemente llamamos a la logica core
            # Para mayor seguridad, reconstruimos el reporte con los datos guardados
            id_l = metadata.get("id_local")
            periodo = metadata.get("periodo", "diario")
            fecha_base = metadata.get("fecha_base", datetime.now().strftime("%Y-%m-%d"))
            
            # Llamamos a una funcion interna para generar el PDF (debemos extraerla de generar_reporte_personalizado)
            # O simplemente replicamos la logica aqui brevemente
            return re_generar_reporte_premium(id_l, periodo, fecha_base)

        if tipo.startswith("consolidado_"):
            subtipo = tipo.replace("consolidado_", "")
            f_ini = informe.get("fecha_inicio")
            f_fin = informe.get("fecha_fin")
            return re_generar_reporte_rango(subtipo, f_ini, f_fin)

        if not informe.get("id_inf_pedido"):
            return jsonify({"success": False, "msg": "Este informe no tiene un tipo valido asociado"}), 404
        
        pedido_result = supabase.table("pedido").select("*").eq("id_pedido", informe["id_inf_pedido"]).execute()
        if not pedido_result.data:
            return jsonify({"success": False, "msg": "Pedido no encontrado"}), 404
        
        pedido = pedido_result.data[0]
        
        inventario_result = supabase.table("inventario").select("id_local").eq("id_inventario", pedido["id_inventario"]).execute()
        if not inventario_result.data:
            return jsonify({"success": False, "msg": "Inventario no encontrado"}), 404
        
        inventario = inventario_result.data[0]
        
        local_result = supabase.table("locales").select("nombre, direccion").eq("id_local", inventario["id_local"]).execute()
        if not local_result.data:
            return jsonify({"success": False, "msg": "Local no encontrado"}), 404
        
        local = local_result.data[0]
        
        detalles = supabase.table("detalle_pedido").select("id_producto, cantidad").eq("id_pedido", pedido["id_pedido"]).execute().data
        productos = supabase.table("productos").select("id_producto, nombre, unidad, categoria").execute().data
        mapa_productos = {p["id_producto"]: p for p in productos}

        data_productos = []
        categorias_count = {}
        for d in detalles:
            prod = mapa_productos.get(d["id_producto"], {})
            data_productos.append([
                d["id_producto"],
                prod.get("nombre", "Desconocido"),
                d["cantidad"],
                prod.get("unidad", "-")
            ])
            cat = prod.get("categoria", "Sin categoria")
            categorias_count[cat] = categorias_count.get(cat, 0) + d["cantidad"]

        buffer = io.BytesIO()
        # Margen izquierdo amplio para el sidebar
        doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=75, rightMargin=40, topMargin=50, bottomMargin=50)
        styles = getSampleStyleSheet()
        
        # Estilos Diseno C
        style_title = styles['Title']
        style_title.alignment = 0
        style_title.fontSize = 20
        style_title.textColor = colors.HexColor("#111111")
        
        style_h2 = styles['Heading2']
        style_h2.textColor = colors.HexColor("#E63900")
        style_h2.fontSize = 14
        
        elements = []

        # Titulo y acento rojo
        elements.append(Paragraph(f"INFORME DE PEDIDO", style_title))
        elements.append(Spacer(1, 4))
        elements.append(Table([[""]], colWidths=[480], style=[('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#E63900"))]))
        elements.append(Spacer(1, 15))

        try:
            fecha_formateada = datetime.fromisoformat(informe["fecha_creacion"]).strftime("%d/%m/%Y - %I:%M %p")
        except:
            fecha_formateada = informe.get("fecha_creacion", "Sin fecha")

        info_table_data = [
            [Paragraph(f"<b>ID INFORME:</b> #{informe['id_informe']}", styles['Normal']),
             Paragraph(f"<b>FECHA:</b> {fecha_formateada}", styles['Normal'])],
            [Paragraph(f"<b>LOCAL:</b> {local['nombre'].upper()}", styles['Normal']),
             Paragraph(f"<b>REF PEDIDO:</b> #{informe['id_inf_pedido']}", styles['Normal'])]
        ]
        t = Table(info_table_data, colWidths=[240, 240])
        t.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 20))

        if data_productos:
            elements.append(Paragraph("1. Productos del Pedido", style_h2))
            elements.append(Spacer(1, 10))
            
            table_data = [["ID PROD", "NOMBRE", "CANTIDAD", "UNIDAD"]] + data_productos
            dt = Table(table_data, colWidths=[80, 200, 100, 100])
            dt.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("LINEBELOW", (0, 0), (-1, 0), 1.5, colors.HexColor("#E63900")),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("GRID", (0, 1), (-1, -1), 0.1, colors.grey),
                ("ALIGN", (2, 0), (-1, -1), "CENTER"),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9F9F9")]),
            ]))
            elements.append(dt)
            elements.append(Spacer(1, 25))

        if categorias_count:
            elements.append(Paragraph("2. Distribucion por Categoria", style_h2))
            elements.append(Spacer(1, 10))
            drawing = Drawing(300, 200)
            pie = Pie()
            pie.x = 65
            pie.y = 15
            pie.width = 170
            pie.height = 170
            pie.data = list(categorias_count.values())
            pie.labels = list(categorias_count.keys())
            pie.slices.strokeWidth = 0.5
            drawing.add(pie)
            elements.append(drawing)

        # Footer
        elements.append(Spacer(1, 30))
        elements.append(Paragraph(f"<i>Informe de Pedido Ichiraku Ramen - Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}</i>", styles['Italic']))

        # Build con Sidebar
        doc.build(elements, onFirstPage=dibujar_sidebar_premium, onLaterPages=dibujar_sidebar_premium)
        buffer.seek(0)
        response = make_response(buffer.read())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=informe_{id_informe}.pdf'
        return response
        
    except Exception as e:
        print(f"Error al generar PDF para informe {id_informe}: {e}")
        return jsonify({"success": False, "msg": f"Error al generar informe PDF: {e}"})

@app.route('/descargar_informes_rango', methods=['POST'])
@login_requerido(rol='Administrador')
def descargar_informes_rango():
    try:
        data = request.get_json()
        tipo = data.get("tipo")
        fecha_inicio = data.get("fecha_inicio")
        fecha_fin = data.get("fecha_fin")
        
        if not tipo:
            return jsonify({"success": False, "msg": "Tipo de informe no especificado."})
        
        if not fecha_inicio or not fecha_fin:
            return jsonify({"success": False, "msg": "Fechas de rango no especificadas."})

        informes = supabase.table("informe") \
            .select("*") \
            .gte("fecha_creacion", fecha_inicio) \
            .lte("fecha_creacion", fecha_fin) \
            .order("fecha_creacion", desc=True) \
            .execute()

        if not informes.data:
            return jsonify({"success": False, "msg": "No se encontraron informes en el rango especificado."})

        # Persistencia en la base de datos para el historial
        try:
            nuevo_rango = {
                "fecha_creacion": datetime.now().isoformat(),
                "tipo": f"consolidado_{tipo}",
                "fecha_inicio": fecha_inicio[:10],
                "fecha_fin": fecha_fin[:10],
                "total_pedidos": len(informes.data),
                "pedidos_ids": {"subtipo": tipo}
            }
            supabase.table("informe").insert(nuevo_rango).execute()
        except Exception as db_e:
            print(f"Error al persistir informe de rango: {db_e}")

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=75, rightMargin=40, topMargin=50, bottomMargin=50)
        styles = getSampleStyleSheet()
        
        style_title = styles['Title']
        style_title.alignment = 0 
        style_title.fontName = "Helvetica-Bold"
        style_title.fontSize = 20
        style_title.textColor = colors.HexColor("#111111")
        
        style_h2 = styles['Heading2']
        style_h2.textColor = colors.HexColor("#E63900")
        style_h2.fontSize = 14
        
        elements = []

        if tipo == "semana":
            titulo = "INFORME SEMANAL CONSOLIDADO"
        elif tipo == "mes":
            titulo = "INFORME MENSUAL CONSOLIDADO"
        elif tipo == "anio":
            titulo = "INFORME ANUAL CONSOLIDADO"
        else:
            titulo = "INFORME CONSOLIDADO"

        elements.append(Paragraph(titulo, style_title))
        elements.append(Spacer(1, 5))
        
        elements.append(Table([[""]], colWidths=[480], style=[('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#E63900"))]))
        elements.append(Spacer(1, 15))
        
        fecha_inicio_obj = datetime.fromisoformat(fecha_inicio.replace('T', ' '))
        fecha_fin_obj = datetime.fromisoformat(fecha_fin.replace('T', ' '))
        
        info_data = [
            [Paragraph(f"<b>PERIODO:</b> {fecha_inicio_obj.strftime('%d/%m/%Y')} - {fecha_fin_obj.strftime('%d/%m/%Y')}", styles['Normal']),
             Paragraph(f"<b>FECHA GENERACION:</b> {datetime.now().strftime('%d de %B, %Y')}", styles['Normal'])]
        ]
        info_table = Table(info_data, colWidths=[240, 240])
        info_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 20))

        # Fetch data based on the exact date range using the pedido table
        fecha_inicio_str = fecha_inicio_obj.strftime('%Y-%m-%d 00:00:00')
        fecha_fin_str = fecha_fin_obj.strftime('%Y-%m-%d 23:59:59')
        
        pedidos_rango = supabase.table("pedido").select("*") \
            .gte("fecha_pedido", fecha_inicio_str) \
            .lte("fecha_pedido", fecha_fin_str).execute().data or []

        total_pedidos = len(pedidos_rango)
        total_productos = 0
        categorias_totales = {}
        locales_participantes = set()
        productos_detallados = []
        fechas_pedidos = set()

        for pedido in pedidos_rango:
            pedido_id = pedido.get('id_pedido')
            if not pedido_id: continue
            
            try:
                fecha_pedido_obj = datetime.fromisoformat(pedido.get("fecha_pedido", datetime.now().isoformat()))
                fechas_pedidos.add(fecha_pedido_obj.date())
                fecha_str = fecha_pedido_obj.strftime("%d/%m/%Y")
                hora_str = fecha_pedido_obj.strftime("%H:%M")
            except:
                fecha_str = "N/A"
                hora_str = "N/A"

            detalles = supabase.table("detalle_pedido").select("id_producto, cantidad") \
                .eq("id_pedido", pedido_id).execute().data or []
            
            local_nombre = "No especificado"
            
            try:
                id_inventario = pedido.get("id_inventario")

                if id_inventario:

                    inventario_result = supabase.table("inventario") \
                        .select("id_local") \
                        .eq("id_inventario", id_inventario) \
                        .execute()

                    if inventario_result.data:

                        id_local = inventario_result.data[0].get("id_local")

                        if id_local:

                            local_result = supabase.table("locales") \
                                .select("nombre") \
                                .eq("id_local", id_local) \
                                .execute()

                            if local_result.data:
                                local_nombre = local_result.data[0].get(
                                    "nombre",
                                    "No especificado"
                                )

                            locales_participantes.add(local_nombre)

            except Exception as e:
                print("ERROR OBTENIENDO LOCAL:", e)
                
            for detalle in detalles:
                if not isinstance(detalle, dict): continue
                cantidad_detalle = detalle.get('cantidad', 0)
                id_producto = detalle.get('id_producto')
                if not id_producto: continue

                total_productos += int(cantidad_detalle)
                
                try:
                    producto_result = supabase.table("productos").select("nombre, categoria, unidad") \
                        .eq("id_producto", id_producto).execute()
                    
                    if producto_result.data:
                        producto_info = producto_result.data[0]
                        cat = producto_info.get('categoria', 'Sin categoria')
                        categorias_totales[cat] = categorias_totales.get(cat, 0) + cantidad_detalle
                        
                        productos_detallados.append({
                            'pedido_id': int(pedido_id),
                            'local': str(local_nombre),
                            'producto': str(producto_info.get('nombre', 'Desconocido')),
                            'categoria': str(cat),
                            'cantidad': int(cantidad_detalle),
                            'unidad': str(producto_info.get('unidad', 'und')),
                            'fecha': fecha_str,
                            'hora': hora_str
                        })
                except:
                    continue

        elements.append(Paragraph("1. Resumen Ejecutivo de Operacion", style_h2))
        elements.append(Spacer(1, 12))
        
        res_data = [
            ["TOTAL PEDIDOS", "PRODUCTOS", "DIAS ACTIVOS", "LOCALES"],
            [f"{total_pedidos}", f"{total_productos}", f"{len(fechas_pedidos)}", f"{len(locales_participantes)}"]
        ]
        t_res = Table(res_data, colWidths=[120, 120, 120, 120])
        t_res.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.grey),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, 1), 14),
            ('TEXTCOLOR', (0, 1), (-1, 1), colors.black),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(t_res)
        elements.append(Spacer(1, 25))
        
        if locales_participantes:
            locs = ", ".join(sorted(locales_participantes))
            elements.append(Paragraph(f"<b>Locales impactados:</b> {locs}", styles['Normal']))
            elements.append(Spacer(1, 20))

        elements.append(Spacer(1, 30))

        if categorias_totales:
            elements.append(Paragraph("2. Distribucion General por Categorias", style_h2))
            elements.append(Spacer(1, 12))
            
            categorias_data = [["CATEGORIA", "CANTIDAD", "PORCENTAJE"]]
            total_categorias = sum(categorias_totales.values())
            
            for cat, cant in sorted(categorias_totales.items(), key=lambda x: x[1], reverse=True):
                porc = (cant / total_categorias) * 100 if total_categorias > 0 else 0
                categorias_data.append([cat.upper(), f"{cant} und", f"{porc:.1f}%"])
            
            t_cat = Table(categorias_data, colWidths=[200, 140, 140])
            t_cat.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('LINEBELOW', (0, 0), (-1, 0), 1.5, colors.HexColor("#E63900")),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9F9F9")]),
                ('TOPPADDING', (0, 1), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            ]))
            elements.append(t_cat)
            elements.append(Spacer(1, 30))

        if productos_detallados:
            elements.append(Paragraph(
                "<font size=14 color='#000000'><b>DETALLE DE PEDIDOS</b></font>", 
                styles['Heading2']
            ))
            elements.append(Spacer(1, 15))

            pedidos_agrupados = {}
            for producto in productos_detallados:
                pedido_id = producto.get('pedido_id')
                if pedido_id not in pedidos_agrupados:
                    pedidos_agrupados[pedido_id] = {
                        'local': producto.get('local', 'No especificado'),
                        'hora': producto.get('hora', 'N/A'),
                        'fecha': producto.get('fecha', ''),
                        'productos': [],
                        'total_cantidad': 0
                    }
                pedidos_agrupados[pedido_id]['productos'].append(producto)
                pedidos_agrupados[pedido_id]['total_cantidad'] += producto.get('cantidad', 0)

            locales_agrupados = {}
            for pedido_id, info in sorted(pedidos_agrupados.items()):
                local = info['local']
                if local not in locales_agrupados:
                    locales_agrupados[local] = []
                locales_agrupados[local].append((pedido_id, info))

            for local_nombre, pedidos_local in sorted(locales_agrupados.items()):
                num_pedidos = len(pedidos_local)

                local_header_data = [[
                    Paragraph(
                        f"<font color='white'><b>LOCAL: {local_nombre.upper()}</b>  —  {num_pedidos} pedido{'s' if num_pedidos != 1 else ''}</font>",
                        styles['Normal']
                    )
                ]]
                local_header_table = Table(local_header_data, colWidths=[480])
                local_header_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#E63900")),
                    ('LEFTPADDING', (0, 0), (-1, -1), 10),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                    ('TOPPADDING', (0, 0), (-1, -1), 7),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
                ]))
                elements.append(local_header_table)
                elements.append(Spacer(1, 8))

                for pedido_id, info in pedidos_local:
                    if not info.get('productos'):
                        continue

                    fecha_hora = f"{info.get('fecha', '')} {info['hora']}".strip()
                    elements.append(Paragraph(
                        f"<b>PEDIDO #{pedido_id}</b>  |  Fecha: {fecha_hora}",
                        styles['Normal']
                    ))
                    elements.append(Spacer(1, 4))

                    table_data = [["PRODUCTO", "CANTIDAD"]]
                    for p in info['productos']:
                        table_data.append([p['producto'].upper(), f"{p['cantidad']} {p['unidad']}"])

                    pedido_table = Table(table_data, colWidths=[340, 140])
                    pedido_table.setStyle(TableStyle([
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 8),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#666666")),
                        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.lightgrey),
                        ('FONTSIZE', (0, 1), (-1, -1), 8),
                        ('GRID', (0, 1), (-1, -1), 0.1, colors.lightgrey),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#FDFDFD")]),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                        ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ]))
                    elements.append(pedido_table)
                    elements.append(Spacer(1, 12))

                elements.append(Spacer(1, 10))

        elements.append(Spacer(1, 30))
        elements.append(Paragraph(f"<i>Informe Consolidado Ichiraku Ramen - Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}</i>", styles['Italic']))

        doc.build(elements, onFirstPage=dibujar_sidebar_premium, onLaterPages=dibujar_sidebar_premium)
        buffer.seek(0)

        response = make_response(buffer.read())
        response.headers["Content-Type"] = "application/pdf"
        response.headers["Content-Disposition"] = f"attachment; filename=informe_{tipo}_{datetime.now().strftime('%Y%m%d')}.pdf"
        return response
        
    except Exception as e:
        print(f"Error al generar informe: {e}")
        return jsonify({"success": False, "msg": str(e)})

# ==============================================================================
