import sys
import os

# Dummy class para reportlab
class Dummy:
    pass

sys.modules['reportlab'] = Dummy()
sys.modules['reportlab.platypus'] = Dummy()
sys.modules['reportlab.lib'] = Dummy()
sys.modules['reportlab.lib.pagesizes'] = Dummy()
sys.modules['reportlab.lib.styles'] = Dummy()
sys.modules['reportlab.lib.colors'] = Dummy()

class SimpleDocTemplate: pass
class Table: pass
class TableStyle: pass
class Paragraph: pass
class Spacer: pass
class Image: pass
class getSampleStyleSheet:
    def __call__(self): return {}

sys.modules['reportlab.platypus'].SimpleDocTemplate = SimpleDocTemplate
sys.modules['reportlab.platypus'].Table = Table
sys.modules['reportlab.platypus'].TableStyle = TableStyle
sys.modules['reportlab.platypus'].Paragraph = Paragraph
sys.modules['reportlab.platypus'].Spacer = Spacer
sys.modules['reportlab.platypus'].Image = Image
sys.modules['reportlab.lib.styles'].getSampleStyleSheet = getSampleStyleSheet

import extensions
print(extensions.supabase.table("pedido").select("*").limit(1).execute().data)
