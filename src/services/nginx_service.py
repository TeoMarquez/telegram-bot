import os
import json
import subprocess
from utils import is_windows
from config import ADMIN_EMAIL

CONFIG_PATH = os.path.join(os.getcwd(), "data", "config.json")
DEFAULT_DOMAIN = "localhost"

if is_windows():
    NGINX_DIR = os.path.join(os.getcwd(), "data", "nginx_mock")
else:
    NGINX_DIR = "/etc/nginx/sites-enabled"

def init_service():
    if not os.path.exists(NGINX_DIR):
        os.makedirs(NGINX_DIR, exist_ok=True)
        if is_windows():
            with open(os.path.join(NGINX_DIR, "app_alquileres.conf"), "w") as f:
                f.write("# Mock Nginx Config\nserver {\n    listen 80;\n    server_name alquileres.local;\n}")
            with open(os.path.join(NGINX_DIR, "api_control.conf"), "w") as f:
                f.write("# Mock Nginx Config\nserver {\n    listen 80;\n    server_name api.local;\n}")

def list_sites():
    init_service()
    sites_info = []
    try:
        files = [
            f for f in os.listdir(NGINX_DIR) 
            if os.path.isfile(os.path.join(NGINX_DIR, f)) and not f.startswith('.')
        ]
        
        for file in files:
            file_name_clean = os.path.splitext(file)[0]
            filepath = os.path.join(NGINX_DIR, file)
            
            domains_found = set()
            
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line_clean = line.strip()
                    if line_clean.startswith("server_name") and line_clean.endswith(";"):
                        domain = line_clean.replace("server_name", "").replace(";", "").strip()
                        if domain:
                            domains_found.add(domain.split()[0])
            
            domain_display = ", ".join(domains_found) if domains_found else "No configurado"
            
            sites_info.append({
                "file": file,  
                "domain": domain_display
            })
            
        return sites_info
    except Exception as e:
        print(f"Error leyendo configuraciones de Nginx: {e}")
        return []
    
def is_port_in_use(port):
    init_service()
    port_str = f"127.0.0.1:{port}"
    try:
        files = [f for f in os.listdir(NGINX_DIR) if os.path.isfile(os.path.join(NGINX_DIR, f)) and not f.startswith('.')]
        for file in files:
            filepath = os.path.join(NGINX_DIR, file)
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                if port_str in content or f"localhost:{port}" in content:
                    return file
    except Exception as e:
        print(f"Error al verificar puertos de Nginx: {e}")
    return None

def add_site(name, domain, port):
    init_service()
    filename = f"{name}.conf" if not name.endswith(".conf") else name
    filepath = os.path.join(NGINX_DIR, filename)
    
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

def remove_site(filename):
    init_service()
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
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    if not os.path.exists(CONFIG_PATH):
        try:
            initial_data = {"base_domain": DEFAULT_DOMAIN}
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(initial_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error al crear config.json por defecto: {e}")

def get_base_domain():
    _ensure_config_exists()
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("base_domain", DEFAULT_DOMAIN)
    except Exception as e:
        print(f"Error leyendo config.json: {e}")
        return DEFAULT_DOMAIN

def set_base_domain(new_domain):
    _ensure_config_exists()
    try:
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

def reload_nginx():
    if is_windows():
        return True, "Mock Windows: Nginx testeado y recargado con exito (Simulado)."

    try:
        test_run = subprocess.run(["sudo", "nginx", "-t"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if test_run.returncode != 0:
            error_msg = test_run.stderr or test_run.stdout
            return False, f"Error de sintaxis en Nginx:\n`{error_msg.strip()}`"

        reload_run = subprocess.run(["sudo", "nginx", "-s", "reload"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if reload_run.returncode == 0:
            return True, "Nginx se recargo correctamente y los cambios estan activos."
        else:
            error_msg = reload_run.stderr or reload_run.stdout
            return False, f"Fallo el reload:\n`{error_msg.strip()}`"
    except Exception as e:
        print(f"Error critico al ejecutar comandos de Nginx: {e}")
        return False, f"Error interno del sistema operativo: {e}"

def generate_ssl(domain):
    if is_windows():
        return True, f"Mock Windows: Certificado SSL generado con exito para `{domain}` (Simulado)."

    admin_email = ADMIN_EMAIL
    try:
        cmd = [
            "sudo", "certbot", "--nginx",
            "-d", domain,
            "--non-interactive",
            "--agree-tos",
            "-m", admin_email,
            "--redirect"
        ]
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if process.returncode == 0:
            return True, f"Certificado SSL instalado correctamente en `{domain}`! Redireccion HTTPS activa."
        else:
            error_msg = process.stderr or process.stdout
            return False, f"Certbot fallo con el siguiente error:\n`{error_msg.strip()}`"
    except Exception as e:
        print(f"Error critico al ejecutar Certbot: {e}")
        return False, f"Error interno del sistema al ejecutar Certbot: {e}"

def get_uncertified_sites():
    all_sites = list_sites()
    uncertified = []
    
    for site in all_sites:
        file_base = site.get("file")
        filename = f"{file_base}.conf" if not file_base.endswith(".conf") else file_base
        filepath = os.path.join(NGINX_DIR, filename)
        
        if not os.path.exists(filepath):
            continue
            
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                clean_content = content.lower()
                if "443" not in clean_content and "ssl" not in clean_content:
                    uncertified.append(site)
        except Exception as e:
            print(f"Error leyendo {filename}: {e}")
            
    return uncertified