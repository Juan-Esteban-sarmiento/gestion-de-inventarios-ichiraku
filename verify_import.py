import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

print("Attempting to import app...")
try:
    from app import app
    print("SUCCESS: app imported successfully.")
except ImportError as e:
    print(f"ERROR: Import failed: {e}")
except Exception as e:
    print(f"ERROR: Exception during import: {e}")
except NameError as e:
    print(f"ERROR: NameError during import: {e}")
