import os
from utils import is_windows
import json


# Ruta global al archivo de configuración
CONFIG_PATH = os.path.join(os.getcwd(), "data", "config.json")
DEFAULT_DOMAIN = "localhost"

# Definimos las rutas según el Sistema Operativo
if is_windows():
    # En Windows, creamos una carpeta de juguete dentro del proyecto
    NGINX_DIR = os.path.join(os.getcwd(), "data", "nginx_mock")
else:
    # En tu servidor Linux, la ruta real de Nginx
    NGINX_DIR = "/etc/nginx/sites-available"

def init_service():
    """Asegura que el directorio exista (útil para pruebas en Windows)."""
    if not os.path.exists(NGINX_DIR):
        os.makedirs(NGINX_DIR, exist_ok=True)
        # Creamos un par de archivos de prueba si está vacío en Windows
        if is_windows():
            with open(os.path.join(NGINX_DIR, "app_alquileres.conf"), "w") as f:
                f.write("# Mock Nginx Config\nserver {\n    listen 80;\n    server_name alquileres.local;\n}")
            with open(os.path.join(NGINX_DIR, "api_control.conf"), "w") as f:
                f.write("# Mock Nginx Config\nserver {\n    listen 80;\n    server_name api.local;\n}")

# Modificaciones en src/services/nginx_service.py

def list_sites():
    """
    Escanea los archivos .conf y extrae el server_name (dominio) real de cada uno.
    Devuelve una lista de diccionarios: [{'file': 'anime', 'domain': 'deam.teonudes.duckdns.org'}]
    """
    init_service()
    sites_info = []
    try:
        # Buscamos todos los archivos .conf válidos
        files = [f for f in os.listdir(NGINX_DIR) if os.path.isfile(os.path.join(NGINX_DIR, f)) and f.endswith('.conf')]
        
        for file in files:
            file_name_clean = os.path.splitext(file)[0]
            filepath = os.path.join(NGINX_DIR, file)
            domain_found = "No configurado"
            
            # Leemos el archivo para buscar la directiva server_name
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line_clean = line.strip()
                    # Buscamos la línea que define el dominio
                    if line_clean.startswith("server_name") and line_clean.endswith(";"):
                        # Extraemos lo que hay entre 'server_name' y el ';'
                        # Ej: "server_name deam.teonudes.duckdns.org;" -> "deam.teonudes.duckdns.org"
                        domain_found = line_clean.replace("server_name", "").replace(";", "").strip()
                        break # Ya encontramos el dominio de este bloque, pasamos al siguiente archivo
            
            sites_info.append({
                "file": file_name_clean,
                "domain": domain_found
            })
            
        return sites_info
    except Exception as e:
        print(f"Error leyendo configuraciones de Nginx: {e}")
        return []
    
def is_port_in_use(port):
    """Escanea los archivos .conf existentes para ver si el puerto ya fue asignado."""
    init_service()
    port_str = f"127.0.0.1:{port}"
    try:
        files = [f for f in os.listdir(NGINX_DIR) if os.path.isfile(os.path.join(NGINX_DIR, f)) and f.endswith('.conf')]
        for file in files:
            filepath = os.path.join(NGINX_DIR, file)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                # Si el proxy_pass apunta a ese puerto, asumimos que está ocupado
                if port_str in content or f"localhost:{port}" in content:
                    return os.path.splitext(file)[0] # Devolvemos el nombre del sitio que lo usa
    except Exception as e:
        print(f"Error al verificar puertos de Nginx: {e}")
    return None

def add_site(name, domain, port):
    """Crea un nuevo archivo de configuración básico."""
    init_service()
    filename = f"{name}.conf" if not name.endswith(".conf") else name
    filepath = os.path.join(NGINX_DIR, filename)
    
    # Template básico de proxy inverso de Nginx
    config_template = f"""server {{
    listen 80;
    server_name {domain};

    location / {{
        proxy_pass http://127.0.0.1:{port};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }}
}}
"""
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(config_template)
        return True
    except Exception as e:
        print(f"Error creando sitio Nginx: {e}")
        return False

# Agregar al final de src/services/nginx_service.py

def remove_site(filename):
    """Elimina un archivo de configuración de Nginx si existe."""
    init_service()
    # Nos aseguramos de que no metan rutas raras por seguridad (Path Traversal)
    safe_filename = os.path.basename(filename)
    filepath = os.path.join(NGINX_DIR, safe_filename)
    
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
            return True
        except Exception as e:
            print(f"Error al eliminar archivo Nginx: {e}")
            return False
    return False

def _ensure_config_exists():
    """Función interna para asegurar que data/config.json exista con valores base."""
    # Nos aseguramos de que la carpeta 'data' exista por las dudas
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    
    if not os.path.exists(CONFIG_PATH):
        try:
            initial_data = {"base_domain": DEFAULT_DOMAIN}
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(initial_data, f, indent=4, ensure_ascii=False)
            print(f"✅ Archivo config.json creado automáticamente en: {CONFIG_PATH}")
        except Exception as e:
            print(f"Error al crear config.json por defecto: {e}")

def get_base_domain():
    """Lee el dominio base. Si el archivo no existe, lo crea con un valor genérico."""
    _ensure_config_exists()
    
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("base_domain", DEFAULT_DOMAIN)
    except Exception as e:
        print(f"Error leyendo config.json: {e}")
        return DEFAULT_DOMAIN

def set_base_domain(new_domain):
    """Guarda un nuevo dominio base en el archivo JSON."""
    _ensure_config_exists()
    try:
        # Leemos lo que haya para no pisar otras posibles configuraciones futuras
        data = {}
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = {}

        data["base_domain"] = new_domain.strip().lower()

        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error escribiendo en config.json: {e}")
        return False
    
import subprocess
from utils import is_windows

# ... (todo tu código anterior) ...

def reload_nginx():
    """
    Primero testea la configuración de Nginx (nginx -t) y si está OK,
    aplica una recarga en caliente (nginx -s reload).
    Devuelve (True, "Mensaje de éxito") o (False, "Detalle del error").
    """
    if is_windows():
        return True, "Mock Windows: Nginx testeado y recargado con éxito (Simulado)."

    try:
        # 1. Testear sintaxis de los archivos
        # stdout=subprocess.PIPE y stderr=subprocess.PIPE capturan la salida de la terminal
        test_run = subprocess.run(["sudo", "nginx", "-t"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if test_run.returncode != 0:
            # Si el código de salida no es 0, Nginx detectó un error crítico en algún .conf
            error_msg = test_run.stderr or test_run.stdout
            return False, f"Error de sintaxis en Nginx:\n`{error_msg.strip()}`"

        # 2. Si el testeo pasó, recargamos de forma segura
        reload_run = subprocess.run(["sudo", "nginx", "-s", "reload"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if reload_run.returncode == 0:
            return True, "Nginx se recargó correctamente y los cambios están activos."
        else:
            error_msg = reload_run.stderr or reload_run.stdout
            return False, f"Falló el reload:\n`{error_msg.strip()}`"

    except Exception as e:
        print(f"Error crítico al ejecutar comandos de Nginx: {e}")
        return False, f"Error interno del sistema operativo: {e}"

def generate_ssl(domain):
    """
    Ejecuta Certbot de forma no interactiva para generar e instalar el certificado SSL
    en el dominio especificado.
    Devuelve (True, "Mensaje") o (False, "Error").
    """
    if is_windows():
        return True, f"Mock Windows: Certificado SSL generado con éxito para `{domain}` (Simulado)."

    # Configura acá el mail que querés asociar a Let's Encrypt para que te avise si vence (opcional)
    # Si no querés poner tu mail real, podés dejar uno genérico, pero es útil por seguridad.
    admin_email = "tu_mail_de_registro@gmail.com" 

    try:
        # Comando para meter SSL de forma automática y silenciosa usando el plugin de Nginx
        cmd = [
            "sudo", "certbot", "--nginx",
            "-d", domain,
            "--non-interactive",
            "--agree-tos",
            "-m", admin_email,
            "--redirect" # Fuerza a que todo el tráfico HTTP vaya por HTTPS de una
        ]

        # Ejecutamos y capturamos la salida
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if process.returncode == 0:
            return True, f"¡Certificado SSL instalado correctamente en `{domain}`! Redirección HTTPS activa."
        else:
            error_msg = process.stderr or process.stdout
            return False, f"Certbot falló con el siguiente error:\n`{error_msg.strip()}`"

    except Exception as e:
        print(f"Error crítico al ejecutar Certbot: {e}")
        return False, f"Error interno del sistema al ejecutar Certbot: {e}"