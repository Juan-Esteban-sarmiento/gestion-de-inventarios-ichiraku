import os
import re

def split_app():
    with open('app.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Find boundaries
    boundaries = []
    for i, line in enumerate(lines):
        if line.startswith('# =============================================================================='):
            boundaries.append(i)

    # Looking at the line numbers we found:
    # 0, 175, 177, 359, 361, 708, 710, 1407, 1409, 2943, 2945
    # Let's map sections carefully based on previous analysis.
    # 0-175: CONFIGURACION E IMPORTACIONES (extensions.py)
    # 177-359: UTILIDADES Y FILTROS + NOTIFICACIONES (utils.py)
    # 361-708: AUTENTICACION Y PERFIL DE USUARIO (routes/auth_routes.py)
    # 710-1407: ADMINISTRACION - GESTION DE PRODUCTOS (routes/admin_routes.py)
    # 1409-2943: ADMINISTRACION - DASHBOARD E INFORMES (routes/dashboard_routes.py)
    # 2945-end: OPERACIONES DE EMPLEADOS (routes/employee_routes.py)

    sections = {}
    current_section = "config"
    sections[current_section] = []

    for i, line in enumerate(lines):
        if "1. CONFIGURACION E IMPORTACIONES" in line:
            current_section = "config"
        elif "2. UTILIDADES Y FILTROS" in line:
            current_section = "utils"
        elif "4. AUTENTICACION Y PERFIL DE USUARIO" in line:
            current_section = "auth"
        elif "5. ADMINISTRACION - GESTION DE PRODUCTOS, EMPLEADOS E INVENTARIO" in line:
            current_section = "admin"
        elif "6. ADMINISTRACION - DASHBOARD E INFORMES" in line:
            current_section = "dashboard"
        elif "7. OPERACIONES DE EMPLEADOS" in line:
            current_section = "employee"
        
        sections.setdefault(current_section, []).append(line)

    # We will create extensions.py
    # Extensions needs Flask app init, supabase init, and basic imports.
    # We will just write the config section to extensions.py
    with open('extensions.py', 'w', encoding='utf-8') as f:
        f.writelines(sections['config'])

    # Write utils
    with open('utils.py', 'w', encoding='utf-8') as f:
        f.write('from extensions import app, supabase, logger\n')
        f.write('from flask import session, jsonify, request, redirect, url_for, flash\n')
        f.write('import functools\n')
        f.write('from datetime import datetime\n')
        f.writelines(sections['utils'])

    # Setup routes folder
    os.makedirs('routes', exist_ok=True)
    with open('routes/__init__.py', 'w', encoding='utf-8') as f:
        f.write('# Routes package\n')

    # Common imports for route files
    common_imports = """
from flask import render_template, request, jsonify, redirect, url_for, session, make_response, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import re
import math
from io import BytesIO
import csv

from extensions import app, supabase, logger, ALLOWED_EXTENSIONS
from utils import login_requerido, is_valid_session, check_active_session, assign_session_token, to_num, generar_notificaciones_stock_caducidad, eliminar_notificacion
"""

    with open('routes/auth_routes.py', 'w', encoding='utf-8') as f:
        f.write(common_imports)
        f.writelines(sections['auth'])

    with open('routes/admin_routes.py', 'w', encoding='utf-8') as f:
        f.write(common_imports)
        f.writelines(sections['admin'])

    with open('routes/dashboard_routes.py', 'w', encoding='utf-8') as f:
        f.write(common_imports)
        f.writelines(sections['dashboard'])

    with open('routes/employee_routes.py', 'w', encoding='utf-8') as f:
        f.write(common_imports)
        f.writelines(sections['employee'])

    # Create new app.py
    new_app = """
# ==============================================================================
# MAIN APPLICATION ENTRY POINT
# ==============================================================================

# 1. Initialize extensions (Flask app, Supabase client, etc.)
from extensions import app, supabase, logger

# 2. Import utilities and filters (registers template filters and background tasks)
import utils

# 3. Import routes to register them with the app
import routes.auth_routes
import routes.admin_routes
import routes.dashboard_routes
import routes.employee_routes

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
"""
    # Wait, we need to import os in new_app.py
    new_app = "import os\n" + new_app
    
    with open('new_app.py', 'w', encoding='utf-8') as f:
        f.write(new_app)

    print("Refactoring complete. Files generated.")

if __name__ == '__main__':
    split_app()
