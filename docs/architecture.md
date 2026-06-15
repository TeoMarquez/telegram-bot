# Arquitectura del Sistema: Core & Decisiones de Diseño

Este documento especifica los pilares de diseño, el flujo de datos concurrente y la gestión de estado que rigen el comportamiento del bot de Telegram. Define cómo interactúan los daemons de fondo con el ciclo de vida de la aplicación y la infraestructura del servidor doméstico.

---

## 📌 Tabla de Contenidos

| Sección del Core | Enfoque Técnico / Propósito |
| :--- | :--- |
| 📊 **[Paradigma y Estilo de Programación](#1-paradigma-y-estilo-de-programación)** | Inversión de Control (IoC), separación de capas y *Fail-Safe*. |
| 🗺️ **[Ramificación y Ciclo de Vida del Update](#2-ramificación-y-ciclo-de-vida-del-update)** | Pipeline centralizado y ruteo de eventos con telemetría reactiva. |
| 🛡️ **[Autenticación y Seguridad](#3-autenticación)** | Inyección de decoradores al vuelo y la llave de paso (`-1`). |
| 💾 **[Gestión de Estado y Persistencia](#4-gestión-de-estado-y-persistencia)** | Memoria atómica en caliente, Heartbeat y Logs concurrentes de disco. |
| 📱 **[Interfaz Compacta (UI Wrappers)](#5-interfaz-compacta-ui-wrappers)** | Mutación de la API de Telegram con proxies en caliente (`CustomUpdate`). |
| 📈 **[Watchdog Daemon](#6-watchdog-daemon-monitoreo-y-salud)** | Concurrencia de fondo, telemetría perimetral y prevención de picos de CPU. |
| 💼 **[Decisiones de Negocio](#7-decisiones-de-negocio-e-infraestructura-doméstica)** | Optimización para mini-servidores y entorno de desarrollo mock. |
---

## 1. Paradigma y Estilo de Programación

El proyecto se rige bajo un enfoque **Modular Orientado a la Infraestructura**, combinando programación funcional (decoradores y composición de funciones) con programación orientada a objetos para la extensión de la API de Telegram.

### Principios Clave:
* **Inversión de Control (IoC) Parcial:** Los comandos individuales no manejan su propia seguridad ni deciden cómo renderizarse. Se limitan a exponer su lógica, delegando el control perimetral al cargador central (`src/commands/__init__.py`).
* **Seguridad por Defecto (Fail-Safe):** La arquitectura asume que todo comando es crítico a menos que se configure explícitamente lo contrario.
* **Separación de Capas:** La lógica de negocio pura (interacción con el sistema operativo) está estrictamente aislada de la capa de presentación de Telegram (`src/services/` vs `src/commands/` vs `src/state/`).

---

## 2. Ramificación y Ciclo de Vida del Update

Cuando un evento (Update) llega desde los servidores de Telegram, la arquitectura lo procesa a través de una pipeline centralizada que inyecta telemetría y valida perímetros de seguridad antes de ejecutar la acción final.

### Flujo de un Comando de Texto o Callback:

```text
       [ Servidores de Telegram ]
                   │
                   ▼ (Mecanismo Long Polling)
         [ src/bot.py (Application) ] ────► [ state/heartbeat.py ] ──► tick() cada evento
                   │
         ┌─────────┴─────────┐
         ▼                   ▼
  [ Handlers de Texto ]   [ CallbackQueryHandler ]
  (/network, /nginx)      (Botones del menú)
         │                   │
         └─────────┬─────────┘
                   ▼
       [ utils/auth.py (@authorized_only) ] ───► ¿AUTHORIZED_USER == -1?
                   │                                     │
                   ├───────────────── NO ◄───────────────┤ (Bypass total)
                   ▼                                     ▼
       ¿update.user.id == ID? ──► [NO] ──► (Ignora / Muere en silencio / log_event())
                   │                                     ┤
                  [SI]                                   │
                   ▼ ◄───────────────────────────────────┤
     [ src/commands/__init__.py ]
     (Inyección de CustomUpdate / CustomMessage)
                   │
                   ▼
      [ Handler Final del Comando ] ──► Edita el mensaje existente en la UI
```
---

## 3. Autenticación

En lugar de forzar al desarrollador a recordar añadir un decorador de seguridad arriba de cada nueva función, la infraestructura del core intercepta y envuelve los callbacks durante la inicialización del ciclo de vida del bot.

### La Llave de Paso (`AUTHORIZED_USER = -1`)

El sistema implementa una compuerta lógica basada en el entorno. Si en el `.env` el ID de usuario se configura en `-1`, el cargador desactiva los envoltorios logrando un entorno público inmediato:

```python
# Fragmento del mecanismo en src/commands/__init__.py
if AUTHORIZED_USER != -1:
    for handler in handlers:
        if hasattr(handler, "callback") and handler.callback:
            handler.callback = authorized_only(handler.callback)

```

Para los botones flotantes, el `_callback_dispatcher` es envuelto de la misma manera, garantizando que un usuario no autorizado no pueda disparar acciones secundarias mediante botones remanentes en su historial de chat.

---

## 4. Gestión de Estado y Persistencia
Para evitar sobrecargar la Mini-PC con dependencias complejas, la persistencia y la telemetría interna se dividen en dos arquitecturas livianas:

1. Estado en Caliente (src/state/heartbeat.py)
Encargado de monitorizar la salud interna del hilo principal del bot de manera no bloqueante. Almacena marcas de tiempo en variables de módulo protegidas mediante encapsulamiento por funciones (tick(), is_alive()). Cada vez que la aplicación procesa un update, el despachador ejecuta un tick, actualizando el estado vital del sistema.

2. Motor de Logs Protegido (src/services/log_service.py)
Debido a que múltiples daemons asincrónicos de fondo (Watchdog, Heartbeat loops) e interacciones de usuario escriben en disco de forma simultánea, la persistencia en archivos de texto (logs/bot-YYYY-MM-DD.log) está blindada por exclusión mutua mediante primitivas del sistema operativo:

```python
import threading

_lock = threading.Lock()

def log_event(msg: str):
    file = _get_log_file()
    line = f"{datetime.now()} | {msg}\n"
    
    with _lock:  # Evita condiciones de carrera en escrituras concurrentes de disco
        with open(file, "a", encoding="utf-8") as f:
            f.write(line)
```

---

## 5. Interfaz Compacta (UI Wrappers)

Para emular la experiencia de una Mini-App y evitar el spam visual de los bots conversacionales el core altera el comportamiento nativo de mutación de Telegram mediante un sistema de proxying en caliente.

Se implementan las clases **`CustomUpdate`** y **`CustomMessage`**. Estas interceptan las llamadas al método estándar de respuesta rápida:

```python
class CustomMessage:
    def __init__(self, original_message, query):
        self._message = original_message
        self._query = query

    async def reply_text(self, text, *args, **kwargs):
        # REEMPLAZO DINÁMICO: Cambia la creación de mensaje por la edición del actual
        return await self._query.edit_message_text(text, *args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._message, name)

```

Al heredar dinámicamente mediante `__getattr__`, el desarrollador puede seguir programando comandos utilizando la sintaxis estándar de la librería (`await update.effective_message.reply_text(...)`), pero el bot alterará su comportamiento por debajo, transformando la acción en una actualización estética del mismo panel.

---

## 6. Watchdog Daemon (Monitoreo y Salud)
El Watchdog opera como un ciclo de fondo asincrónico independiente (asyncio.create_task) que se dispara en el startup del sistema (lifecycle.py). Sus responsabilidades son la telemetría local a disco y el control destructivo de fallos.

### Lógica de Control del Heartbeat y Caída Limpia
  
El Watchdog consulta periódicamente al estado global si el hilo de eventos sigue con vida (heartbeat.is_alive(120)). Si el bucle asincrónico principal de Telegram se congela o sufre un Deadlock por llamadas de red bloqueantes, el daemon escribe un log de emergencia y fuerza la muerte del proceso mediante SystemExit(1), delegando la autorecuperación y reinicio limpio al gestor del sistema operativo (Systemd en Linux / Programador de Tareas en Windows).

### Protección contra Picos de CPU en Bucles de Excepción
En bucles infinitos (while True), un error imprevisto en la API de red o en llamadas de psutil puede provocar que el flujo salte directo al bloque except, esquivando el temporizador tradicional. Esto generaría miles de iteraciones por segundo, saturando el procesador del servidor doméstico.

La arquitectura mitiga esto forzando el asyncio.sleep en el bloque de nivel de salida del bucle, garantizando su ejecución obligatoria sin importar el estado del procesamiento previo:

```python
async def watchdog_loop(app):
    while True:
        try:
            if not heartbeat.is_alive(120):
                log_event("WATCHDOG_FAIL | heartbeat timeout")
                raise SystemExit(1)
            # ... telemetría y reportes de Telegram ...
        except Exception as e:
            log_event(f"WATCHDOG_ERROR | {e}")
            raise SystemExit(1)  # Caída controlada ante errores críticos

        # El sleep se ejecuta SÍ O SÍ en el bloque exterior, previniendo picos de CPU si algo falla.
        await asyncio.sleep(get_interval())
```

---

## 7. Decisiones de Negocio e Infraestructura Doméstica

El diseño técnico responde de forma directa a las restricciones físicas y de uso del hardware de despliegue:

- **Optimización para mini-servidor doméstico:** Al correr en hardware local compartido con otros servicios del hogar, el bot minimiza el consumo de ciclos de reloj. Si el bot se configura en modo público (`-1`), el Watchdog inhabilita automáticamente las llamadas de sistema a `psutil`, quedando en estado de hibernación pasiva.
- **Desarrollo Multiplataforma Agnóstico:** Las tareas de administración real requieren comandos Linux avanzados (`sudo systemctl`, `certbot`, escritura en `/etc/nginx/`). Para permitir programar cómodamente en entornos de desarrollo Windows sin romper el arranque, la lógica implementa abstracciones mock que simulan la interacción con las terminales de Linux si detectan sistemas operativos alternativos.
- **Persistencia Liviana sin Base de Datos:** Para mantener el entorno libre de dependencias pesadas (como instancias de PostgreSQL o Docker innecesarios), los estados de configuración se gestionan mediante estructuras JSON atómicas en memoria con persistencia en disco duro local (`data/`), garantizando lecturas a velocidad de memoria y backups triviales.


---