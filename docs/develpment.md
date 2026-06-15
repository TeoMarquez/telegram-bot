# 📈 Guía de Desarrollo & Contrato de Skills (AI-Friendly)

Este documento sirve como manual práctico de desarrollo y como especificación de contexto estricta (`skills.md`) para agentes de Inteligencia Artificial. Define las reglas, firmas y convenciones arquitectónicas necesarias para extender las capacidades del bot sin alterar el núcleo de ejecución.

---

## 📌 Índice de Desarrollo

| Sección de Guía | Propósito del Contrato |
| :--- | :--- |
| 🏗️ **[Arquitectura del Core](#arquitectura-del-core)** | Cómo arranca el despachador y qué espera de cada módulo. |
| 🗂️ **[Exposición de la API Interna](#exposición-de-la-api-interna-ownership)** | Contratos de exportación y aplanamiento de rutas (*Ownership*). |
| ⚡ **[Comandos Simples (Menús Reactivos)](#comandos-simples-menús-reactivos)** | Estructura estándar para botones con edición de mensaje integrada. |
| 🔄 **[Flujos Avanzados e Interceptores](#flujos-avanzados-e-interceptores)** | Diseño de `Conversations` por estados y registro de `EXTRA_HANDLERS`. |
| 🧪 **[Entorno de Testing Local](#entorno-de-testing-local-modo-mock)** | Abstracción multiplataforma para desarrollo ágil en Windows. |
| 🚨 **[Errores Comunes](#errores-comunes)** | Diagnóstico rápido de los fallos más frecuentes al extender el bot. |

---

## Arquitectura del Core

### Flujo de arranque del despachador

Al iniciar, `src/commands/__init__.py` descubre y registra todos los módulos automáticamente siguiendo este orden:

```
bot.py arranca
    └── lifecycle.py importa commands
        └── commands/__init__.py itera cada sub-paquete de categoría
            ├── Lee COMMANDS → construye COMMAND_MAP { cmd.COMMAND: cmd.handler }
            ├── Lee CONVERSATIONS → registra cada ConversationHandler en el dispatcher
            ├── Lee CONVERSATION_COMMANDS → marca módulos con flujo propio (acepta módulos, no strings)
            └── Lee EXTRA_HANDLERS → registra handlers libres directamente en el dispatcher
```

**Lo que esto implica para cualquier módulo nuevo:**

- El core ejecuta `cmd.handler` de forma ciega sobre todo lo que esté en `COMMANDS`. Si el atributo no existe, el bot no arranca.
- `CONVERSATION_COMMANDS` recibe los **módulos** (objetos Python), no strings con el nombre del comando. El enrutador los compara por identidad de objeto.
- `EXTRA_HANDLERS` recibe **instancias** de handlers ya configuradas, no módulos completos.

### Tabla de contratos por tipo de módulo

Referencia rápida de qué debe exportar cada tipo de archivo antes de integrarlo al ecosistema:

| Atributo | Comando simple | Módulo conversacional | Módulo auxiliar |
| :--- | :---: | :---: | :---: |
| `COMMAND` | ✅ | ✅ | ❌ |
| `DESCRIPTION` | ✅ | ✅ | ❌ |
| `handler` | ✅ | ✅ | ❌ |
| `CONVERSATION` | ❌ | ✅ | ❌ |
| `CALLBACK_HANDLER` | ❌ | ❌ | ✅ |

| Array en `__init__.py` | Comando simple | Módulo conversacional | Módulo auxiliar |
| :--- | :---: | :---: | :---: |
| `COMMANDS` | ✅ | ✅ | ❌ |
| `CONVERSATIONS` | ❌ | ✅ | ❌ |
| `CONVERSATION_COMMANDS` | ❌ | ✅ | ❌ |
| `EXTRA_HANDLERS` | ❌ | ❌ | ✅ |

---

## Exposición de la API Interna (Ownership)

El proyecto utiliza los archivos `__init__.py` para aplanar las rutas de importación, centralizar el *ownership* de los módulos y exponer una interfaz limpia ("Facade") hacia el resto de la aplicación, evitando la fuga de dependencias internas.

### 1. Capa de Servicios (`src/services/__init__.py`)
Registra y expone los daemons de fondo y gestores de infraestructura del sistema operativo:
```python
from . import watchdog_service
from . import nginx_service
```

### 2. Capa de Utilidades (`src/utils/__init__.py`)

Centraliza los helpers públicos utilizando la directiva `__all__` para garantizar exportaciones limpias de funciones del paquete hacia el exterior:

```python
from .auth import authorized_only
from .network import (
    wait_for_internet,
    is_windows,
    get_public_ip
)
from .uptime import get_uptime

__all__ = [
    "authorized_only",
    "wait_for_internet",
    "is_windows",
    "get_public_ip",
    "get_uptime"
]
```

**Regla para IA:** Cualquier comando nuevo debe importar estas funciones directamente desde la raíz del paquete (ej: `from utils import get_uptime`). Prohibido perforar módulos internos de forma manual (ej: `from utils.network import ...` está prohibido).

---

## Comandos Simples (Menús Reactivos)

Los comandos simples se ejecutan mediante eventos de botones flotantes (`CallbackQuery`). Gracias a la infraestructura centralizada en `src/commands/__init__.py`, **no requieren decoradores de seguridad manuales**. El núcleo se encarga del ruteo, la inyección del wrapper de interfaz y la validación perimetral.

### 📄 Contrato Estándar (`src/commands/mi_categoria/mi_comando.py`)

```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Constantes obligatorias para que el core indexe el comando automáticamente
COMMAND = "categoria_mi_comando"  # Debe coincidir con el callback_data del botón
DESCRIPTION = "Ejecuta una acción y responde limpiamente"

async def handler(update, context):
    texto_respuesta = "🤖 Acción ejecutada con éxito en el servidor."

    # Recuperar la categoría para mantener la navegación del botón "Volver"
    current_cat = context.user_data.get("current_category", "mi_categoria")
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Volver al Menú", callback_data=f"menu_{current_cat}")]
    ])

    # ⚠️ REGLA DE ORO: Usar siempre update.effective_message.reply_text
    # El Core intercepta este método para EDITAR la burbuja actual en vez de spamear.
    await update.effective_message.reply_text(
        texto_respuesta,
        reply_markup=keyboard
    )
```

### 🏷️ Registro en la Categoría (`src/commands/mi_categoria/__init__.py`)

Para que el comando exista en el ecosistema, simplemente se importa y se añade a la lista expuesta:

```python
from . import mi_comando

COMMAND = "mi_categoria"
CATEGORY = "🛠️ Mi Categoría"
DESCRIPTION = "Descripción general del menú"

COMMANDS = [mi_comando]  # <-- El despachador dinámico lee este array de módulos
```

---

## Flujos Avanzados e Interceptores

Cuando un módulo requiere interacciones complejas que rompen la lógica lineal de los menús (como diálogos por pasos guiados por texto, flujos conversacionales interactivos o captura de archivos), la categoría debe declarar variables extendidas en su archivo descriptor de paquete.

### 1. Diálogos Secuenciales (`CONVERSATIONS`)

#### Contrato del módulo conversacional

Un módulo conversacional **sigue siendo un comando simple a ojos del core**: debe tener obligatoriamente `COMMAND`, `DESCRIPTION` y `handler`. La diferencia es que además exporta una instancia `CONVERSATION` de tipo `ConversationHandler`.

Reglas críticas que no son negociables:

* **`handler` es obligatorio**: El core itera `COMMANDS` y ejecuta `cmd.handler` de forma ciega. Si falta en el archivo, el bot crashea en el arranque con un `AttributeError`.
* **`handler` actúa como el punto de entrada (`entry_point`) del flujo**: Es la función que dispara el primer paso del diálogo y devuelve el estado inicial (`int`).
* **El `entry_point` del `CONVERSATION` debe ser un `CallbackQueryHandler`**, no un `CommandHandler`, debido a que el flujo lo inicia el botón de un menú (que dispara un `callback_data`), no un comando de texto escrito en la barra del chat.
* **El `callback_data` del `entry_point` debe coincidir exactamente con `COMMAND`**: El core usa ese valor exacto para mapear el ruteo inicial. Usar `pattern=f"^{COMMAND}$"` garantiza esto sin hardcodear strings.
* **`CONVERSATION` en mayúsculas** — Así lo consume el cargador dinámico.

```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, ConversationHandler, ContextTypes

COMMAND = "mi_categoria_mi_flujo"
DESCRIPTION = "Descripción del flujo asistido"

ESTADO_UNO = 0  # Definir estados secuenciales como constantes enteras

async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Punto de entrada: lanza el primer paso del flujo mutando el panel."""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Opción A", callback_data="opcion_a")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")],
    ])
    await update.effective_message.reply_text("¿Qué querés hacer?", reply_markup=keyboard)
    return ESTADO_UNO

async def opcion_elegida(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    # ... lógica de procesamiento ...
    return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await update.effective_message.reply_text("❌ Flujo cancelado correctamente.")
    return ConversationHandler.END

CONVERSATION = ConversationHandler(
    entry_points=[CallbackQueryHandler(handler, pattern=f"^{COMMAND}$")],
    states={
        ESTADO_UNO: [
            CallbackQueryHandler(opcion_elegida, pattern="^opcion_"),
            CallbackQueryHandler(cancelar, pattern="^cancelar$"),
        ]
    },
    fallbacks=[CallbackQueryHandler(handler, pattern=f"^{COMMAND}$")],
)
```

#### Registro en la categoría

Los módulos conversacionales se registran en los **tres arrays obligatorios** del `__init__.py` de su categoría, más `EXTRA_HANDLERS` si el módulo además inyecta interceptores libres:

* **`COMMANDS`**: Expone el botón en la interfaz visual de navegación del menú.
* **`CONVERSATIONS`**: Registra la instancia del `ConversationHandler` en el despachador de la aplicación de Telegram.
* **`CONVERSATION_COMMANDS`**: Le avisa al enrutador central que este módulo gestiona un flujo secuencial autónomo. Recibe **módulos crudos** (objetos Python), NO strings.

```python
from . import mi_flujo

COMMAND = "mi_categoria"
CATEGORY = "🛠️ Mi Categoría"
DESCRIPTION = "Descripción general del menú"

COMMANDS = [mi_flujo]                    # Aparece como botón en el menú
CONVERSATIONS = [mi_flujo.CONVERSATION]  # Registra la lógica por estados
CONVERSATION_COMMANDS = [mi_flujo]       # Objetos módulo, NO strings
```

**Referencia real:** Ver `src/commands/nginx/__init__.py` para la implementación completa con múltiples flujos conversacionales coexistiendo en una misma categoría.

### 2. Captura Global de Eventos (`EXTRA_HANDLERS`)

Permite inyectar interceptores directos que no forman parte de la botonera tradicional (como capturar texto libre, escuchar imágenes, o atrapar un patrón de botones dinámicos usando expresiones regulares desde cualquier submódulo).

#### Contrato de Módulos Auxiliares (`src/commands/nginx/ssl_cmd.py`)

A diferencia de los comandos comunes, estos sub-módulos no necesitan las constantes `COMMAND` o `DESCRIPTION` porque no se listan en el panel principal, pero sí **deben exponer una instancia cruda del Handler de Telegram** (`CALLBACK_HANDLER`) para que el despachador del paquete lo inyecte.

```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler
from services import nginx_service

async def _callback_handler(update, context):
    query = update.callback_query
    await query.answer()

    data = query.data
    domain = data.replace("ssl_gen_", "")

    if not domain or domain == data:
        await query.edit_message_text("❌ No se pudo determinar un dominio válido para certificar.")
        return

    await query.edit_message_text(
        f"⏳ *Solicitando certificado SSL para `{domain}`...*\n"
        f"Esto puede demorar unos segundos mientras Let's Encrypt valida el dominio.",
        parse_mode="Markdown"
    )

    exito_ssl, resultado_ssl = nginx_service.generate_ssl(domain)

    current_cat = context.user_data.get("current_category", "nginx")
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Volver al Menú", callback_data=f"menu_{current_cat}")]
    ])

    if exito_ssl:
        exito_reload, msg_reload = nginx_service.reload_nginx()
        if exito_reload:
            texto_final = f"🔒 *¡HTTPS Activo!*\n\n{resultado_ssl}\n\nNginx se recargó correctamente."
        else:
            texto_final = f"⚠️ *SSL generado pero Nginx falló al recargar:*\n\n{msg_reload}"
    else:
        texto_final = f"❌ *Error de Certificación:*\n\n{resultado_ssl}\n\n_Asegurate de que el dominio apunte correctamente a la IP pública._"

    await query.edit_message_text(
        texto_final,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

# Instancia explícita expuesta para el cargador dinámico
CALLBACK_HANDLER = CallbackQueryHandler(_callback_handler, pattern="^ssl_gen_")
```

#### Registro en la categoría

```python
from . import ssl_cmd

COMMAND = "nginx"
CATEGORY = "🌐 Servidor Nginx"
DESCRIPTION = "Gestión de proxies inversos y certificados"

COMMANDS = []

# El despachador central itera este array y registra las instancias en la app
EXTRA_HANDLERS = [ssl_cmd.CALLBACK_HANDLER]  # Instancias, NO módulos completos
```

---

## Entorno de Testing Local (Modo Mock)

Para desarrollar y testear módulos que interactúan con comandos nativos de Linux de forma segura en entornos de desarrollo locales (como Windows), el sistema implementa una abstracción inteligente que simula las respuestas de terminal.

### Uso del Helper de Entorno

Antes de ejecutar comandos de sistema directo (`subprocess.run`), se debe verificar el entorno usando el helper unificado de `utils`:

```python
from utils import is_windows

async def handler(update, context):
    if is_windows():
        # MOCK DE DESARROLLO: Evita que el bot crashee fuera de Linux en testing local
        texto = "⚠️ Entorno Windows detectado. Simulando respuesta de infraestructura..."
        await update.effective_message.reply_text(texto)
        return

    # LÓGICA DE PRODUCCIÓN: Comandos reales ejecutados en la Mini-PC con Linux
    # ... Lógica nativa (ej: systemctl reload nginx) ...
```

Este contrato garantiza el desacoplamiento total del hardware de testing respecto al entorno de despliegue final en producción.

---

## Errores Comunes

Diagnóstico rápido de los fallos más frecuentes al extender el bot. Cada uno tiene una causa raíz única y un fix específico.

---

### `AttributeError: module '...' has no attribute 'handler'`

**Cuándo aparece:** Al arrancar el bot (`python src/bot.py`), antes de que Telegram reciba ninguna conexión.

**Causa:** Un módulo fue agregado a `COMMANDS` en el `__init__.py` de su categoría pero no define la función `handler`. El core itera `COMMANDS` y ejecuta `cmd.handler` de forma ciega sobre todos los elementos del array.

**Fix:** Agregar la función `handler` al módulo. En módulos conversacionales, `handler` es la función que lanza el primer estado del flujo:

```python
# ❌ Mal — el módulo no tiene handler
async def start(update, context):
    ...

# ✅ Bien — renombrar a handler o agregar el alias
async def handler(update, context):  # el core busca este nombre exacto
    ...
```

---

### El menú muestra solo el nombre de la categoría y nada más

**Cuándo aparece:** Al tocar un botón de categoría en Telegram, el bot responde con algo como "🎯 Selector" y ningún botón de acción.

**Causa:** El módulo no está incluido en el array `COMMANDS` del `__init__.py` de su categoría. El core renderiza el menú leyendo ese array — si está vacío o el módulo fue omitido, muestra solo el encabezado de la categoría.

**Fix:** Verificar que el módulo esté importado y listado en `COMMANDS`:

```python
# ❌ Mal — COMMANDS vacío, el módulo no aparece en el menú
from . import mi_flujo
COMMANDS = []

# ✅ Bien — el módulo aparece como botón en el menú de la categoría
from . import mi_flujo
COMMANDS = [mi_flujo]
```

---

### El flujo conversacional no responde / los botones no hacen nada

**Cuándo aparece:** El menú muestra el botón correctamente, el usuario lo toca, aparece el primer mensaje del flujo, pero al tocar las opciones no pasa nada o el bot queda en silencio.

**Causa más común:** `CONVERSATION_COMMANDS` recibe strings en lugar de módulos. El enrutador central compara por identidad de objeto — si recibe `["mi_flujo"]` en vez de `[mi_flujo]`, no reconoce el módulo como dueño del flujo y el `ConversationHandler` nunca llega a interceptar los `callback_data` de los estados intermedios.

**Fix:**

```python
# ❌ Mal — strings, el enrutador no los reconoce
CONVERSATION_COMMANDS = ["mi_flujo", "otro_flujo"]

# ✅ Bien — módulos importados como objetos Python
CONVERSATION_COMMANDS = [mi_flujo, otro_flujo]
```

**Segunda causa posible:** El `entry_point` del `CONVERSATION` usa `CommandHandler` en vez de `CallbackQueryHandler`. En ese caso el flujo solo se dispara con `/comando` escrito en el chat, nunca desde un botón del menú:

```python
# ❌ Mal — solo funciona con /elegir escrito en el chat
entry_points=[CommandHandler("elegir", handler)]

# ✅ Bien — se dispara desde el botón del menú via callback_data
entry_points=[CallbackQueryHandler(handler, pattern=f"^{COMMAND}$")]
```