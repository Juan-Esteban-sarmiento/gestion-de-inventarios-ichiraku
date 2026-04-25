import os

# Mapeo de reemplazo
replacements = {
    'a': 'a', 'e': 'e', 'i': 'i', 'o': 'o', 'u': 'u',
    'A': 'A', 'E': 'E', 'I': 'I', 'O': 'O', 'U': 'U',
    'n': 'n', 'N': 'N'
}

def clean_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        new_content = content
        for char, replacement in replacements.items():
            new_content = new_content.replace(char, replacement)
        
        if new_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Limpio: {file_path}")
            return True
    except Exception as e:
        print(f"Error en {file_path}: {e}")
    return False

def main():
    target_exts = ('.html', '.js', '.py', '.css')
    root_dir = os.getcwd()
    
    cleaned_count = 0
    for root, dirs, files in os.walk(root_dir):
        # Excluir carpetas sensibles
        if any(x in root for x in ('.venv', '.git', '__pycache__', '.gemini')):
            continue
            
        for file in files:
            if file.endswith(target_exts):
                if clean_file(os.path.join(root, file)):
                    cleaned_count += 1
                    
    print(f"\nTotal de archivos limpiados: {cleaned_count}")

if __name__ == "__main__":
    main()
