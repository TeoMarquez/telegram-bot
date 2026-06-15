<div align="center">

# Mi Bot de Telegram (Mini-PC Lab)

Este es un proyecto puramente personal y a medida, diseñado para resolver mis necesidades específicas de control y monitoreo en mi Mini-PC doméstica. Lo armé de forma modular principalmente para experimentar con una interfaz limpia dentro de Telegram (estilo Mini-App) y para que sea fácil meterle mano a medida que me surjan nuevos problemas que automatizar.

> ⚠️ **Nota:** No busca ser una herramienta genérica ni un sistema de monitoreo universal. Es mi espacio de juego y automatización diaria. Sentite libre de forkear o utilizar esta aplicacion como base para tus necesidades

![Telegram](https://img.shields.io/badge/Telegram-Bot%20API-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)
![Status](https://img.shields.io/badge/Status-Active-22c55e?style=for-the-badge)

</div>

---

## ✨ Características Principales

| Característica | Descripción |
|---|---|
| 📱 **Interfaz Compacta** | Menús dinámicos editando el mismo mensaje con `InlineKeyboards`. Sin spam en el chat. |
| 🧩 **Arquitectura Escalable** | Comandos organizados por categorías autónomas. Añadir módulos sin tocar el núcleo. |
| 🔀 **Enrutamiento Centralizado** | Soporte nativo para flujos de conversación complejos que conviven con menús reactivos. |
| 🔒 **Seguridad Integrada** | Restricción de acceso mediante decoradores. Solo usuarios autorizados interactúan con el sistema. |
| 📊 **Watchdog de Sistema** | Bucle asincrónico que reporta métricas clave — Uptime, RAM, CPU — a intervalos configurables. |

---

## 🎛️ Módulos

El sistema ya incluye lógica empaquetada para gestionar:

* **Servidor Nginx:**  Visualización del estado del servicio.
  * Recarga (`reload`) en caliente de configuraciones tras modificar proxies inversos.
* **Asistente SSL Wizard (Certbot):** Generación automatizada de certificados HTTPS mediante Let's Encrypt.
  * Validación automática de registros DNS/IP pública antes de certificar.
* **Monitoreo de Sistema:**
  * Diagnóstico manual de recursos (Uptime, Consumo de RAM y uso de CPU).
  * Reporte dinámico de la dirección IP pública del laboratorio.

---

## 🛠️ Instalación y Configuración Rápida

### 1 · Configurar Entorno
Cloná o creá el archivo `.env` en la raíz del proyecto basándote en el archivo de plantilla:

```bash
cp .env.example .env
```

Editá el .env con tu token de BotFather, tu ID de Telegram (o -1 para desactivar la seguridad en desarrollo) y tu correo para alertas de Certbot.

### 2 · Ejecución
El proyecto cuenta con un Modo Mock Agnóstico automático que simula los servicios de Linux (Nginx/Certbot) si se ejecuta en entornos Windows, facilitando el desarrollo local.

```bash
# Instalar dependencias
pip install -r requirements.txt

# Iniciar el bot
python src/bot.py
```

---

## 📘 Documentación Extendida

Para mantener este archivo limpio, las guías de arquitectura y desarrollo se encuentran centralizadas en la carpeta de documentación interna:

```text
telegram-bot/
├── data/
├── src/
├── docs/
│   ├── development.md
│   ├── architecture.md
```


---

<div align="center">

Made with ❤️ for home servers and Mini-PCs

</div>