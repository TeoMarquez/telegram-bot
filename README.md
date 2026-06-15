<div align="center">

# 🤖 Telegram System Monitor Bot

**Bot modular y robusto para monitorear servidores domésticos y Mini-PCs desde Telegram**

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram-Bot%20API-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)

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

## 📂 Estructura del Proyecto

```text
telegram-bot/
├── data/                  # Almacenamiento persistente (estados, JSONs)
├── src/
│   ├── commands/          # Menús y comandos del bot divididos por módulos
│   │   ├── network/       # Módulo de comandos de red (IP pública, etc.)
│   │   ├── watchdog/      # Módulo de control del Watchdog y configuración
│   │   └── __init__.py    # Carga dinámica de categorías y wrappers de UI
│   ├── services/          # Lógica de negocio (Watchdog loop, persistencia)
│   ├── utils/             # Helpers compartidos (Auth, Network, Uptime)
│   ├── bot.py             # Punto de entrada principal (Main)
│   ├── config.py          # Configuración y lectura de variables de entorno
│   └── lifecycle.py       # Eventos de inicio (Startup) y tareas asincrónicas
├── .env                   # Variables sensibles de configuración (ignorado en Git)
├── .gitignore
└── requirements.txt       # Dependencias del proyecto
```

---

## 🛠️ Configuración e Instalación

### Requisitos Previos

- Python **3.10** o superior
- Un token de Bot de Telegram (gestionado vía [@BotFather](https://t.me/BotFather))
- Tu **ID de usuario** de Telegram para la lista de autorización

### 1 · Variables de Entorno

Creá un archivo `.env` en la raíz del proyecto con la siguiente estructura:

```env
BOT_TOKEN = "TU_TELEGRAM_BOT_TOKEN_ACÁ"
AUTHORIZED_USER = "TU_CHAT_ID_NUMÉRICO_ACÁ"
```

### 2 · Instalación y Ejecución

```bash
# Instalá las dependencias necesarias
pip install -r requirements.txt

# Ejecutá el bot
python src/bot.py
```

---

## 📈 Cómo Escalar el Bot (Agregar Nuevos Módulos)

Gracias a la arquitectura de `src/commands/__init__.py`, expandir el bot es sumamente sencillo — **no necesitás tocar el bucle principal de ejecución**.

### Paso 1 — Crear el Comando

Creá un nuevo archivo dentro del módulo correspondiente. Por ejemplo, `src/commands/network/ping.py`:

```python
# src/commands/network/ping.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

COMMAND = "network_ping"
DESCRIPTION = "Realiza un ping de prueba"

async def handler(update, context):
    texto_respuesta = "⚡ Sistema respondiendo correctamente."

    # Recuperamos la categoría para mantener el botón "Volver" consistente
    current_cat = context.user_data.get("current_category", "network")
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Volver al Menú", callback_data=f"menu_{current_cat}")]
    ])

    # IMPORTANTE: Usar siempre effective_message.reply_text
    # para que el Wrapper edite el mensaje en lugar de spamear
    await update.effective_message.reply_text(
        texto_respuesta,
        reply_markup=keyboard
    )
```

### Paso 2 — Registrarlo en la Categoría

Importalo y sumalo a la lista `COMMANDS` del paquete correspondiente:

```python
# src/commands/network/__init__.py
from . import currentip
from . import ping  # <-- Importás tu nuevo archivo

COMMAND = "network"
CATEGORY = "🌐 Network"
DESCRIPTION = "Comandos de red"

COMMANDS = [currentip, ping]  # <-- Lo sumás a la lista y listo!
```

> El despachador central se encargará de mapear los callbacks, inyectar el Wrapper dinámico para evitar spam visual y renderizarlo en el menú principal **automáticamente**.

---

<div align="center">

Made with ❤️ for home servers and Mini-PCs

</div>