import os

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
