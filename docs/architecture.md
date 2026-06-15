# Arquitectura del Sistema: Core & Decisiones de Diseño
---

## 📌 Tabla de Contenidos

| Sección del Core | Enfoque Técnico / Propósito |
| :--- | :--- |
| 📊 **[Paradigma y Estilo de Programación](#paradigma-y-estilo-de-programación)** | Inversión de Control (IoC), separación de capas y *Fail-Safe*. |
| 🗺️ **[Ramificación y Ciclo de Vida](#ramificación-y-ciclo-de-vida-del-update)** | Pipeline centralizado del flujo de un *Update* (Texto y Callbacks). |
| 🛡️ **[Autenticación y Seguridad](#autenticación-y-seguridad)** | Inyección de decoradores al vuelo y la llave de paso (`-1`). |
| 📱 **[Interfaz Compacta (UI Wrappers)](#interfaz-compacta-ui-wrappers)** | Mutación de la API de Telegram con proxies en caliente (`CustomUpdate`). |
| 📈 **[Watchdog Daemon](#watchdog-daemon-concurrencia-protegida)** | Concurrencia de fondo protegida contra bucles infinitos de CPU. |
| 💼 **[Decisiones de Negocio](#decisiones-de-negocio-e-infraestructura-doméstica)** | Optimización para mini-servidores y entorno de desarrollo mock. |

---


---
## Paradigma y Estilo de Programación

El proyecto se rige bajo un enfoque **Modular Orientado a la Infraestructura**, combinando programación funcional (decoradores y composición de funciones) con programación orientada a objetos para la extensión de la API de Telegram.

### Principios Clave:
* **Inversión de Control (IoC) Parcial:** Los comandos individuales no manejan su propia seguridad ni deciden cómo renderizarse. Se limitan a exponer su lógica, delegando el control perimetral al cargador central (`src/commands/__init__.py`).
* **Seguridad por Defecto (Fail-Safe):** La arquitectura asume que todo comando es crítico a menos que se configure explícitamente lo contrario.
* **Separación de Capas:** La lógica de negocio pura (interacción con el sistema operativo) está estrictamente aislada de la capa de presentación de Telegram (`src/services/` vs `src/commands/`).

---

## Ramificación y Ciclo de Vida del Update

Cuando un evento (Update) llega desde los servidores de Telegram, la arquitectura lo procesa a través de una pipeline centralizada antes de ejecutar la acción final.

### Flujo de un Comando de Texto o Callback:

```text
       [ Servidores de Telegram ]
                   │
                   ▼ (Mecanismo Long Polling)
         [ src/bot.py (Application) ]
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
       ¿update.user.id == ID? ──► [NO] ──► (Ignora / Muere en silencio)
                   │                                     ┤
                 [SI]                                    │
                   ▼ ◄───────────────────────────────────┤
     [ src/commands/__init__.py ]
     (Inyección de CustomUpdate / CustomMessage)
                   │
                   ▼
      [ Handler Final del Comando ] ──► Edita el mensaje existente en la UI

```

---

## Autenticación

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

## Interfaz Compacta (UI Wrappers)

Para emular la experiencia de una Mini-App y evitar el spam visual de los bots conversacionales el core altera el comportamiento nativo de mutación de Telegram mediante un sistema de proxying en caliente.

Se implementan las clases **`CustomUpdate`** y **`CustomMessage`**. Estas interceptan las llamadas al método estándar de respuesta rápida:

```python
class CustomMessage:
    def __init__(self, original_message, query):
        self._message = original_message
        self._query = query

    async def reply_text(self, text, *args, **kwargs):
        # 🔄 REEMPLAZO DINÁMICO: Cambia la creación de mensaje por la edición del actual
        return await self._query.edit_message_text(text, *args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._message, name)

```

Al heredar dinámicamente mediante `__getattr__`, el desarrollador puede seguir programando comandos utilizando la sintaxis estándar de la librería (`await update.effective_message.reply_text(...)`), pero el bot alterará su comportamiento por debajo, transformando la acción en una actualización estética del mismo panel.

---

## Watchdog Daemon (Concurrencia Protegida)

El Watchdog opera como un hilo de fondo asincrónico independiente (`asyncio.create_task`) que se dispara en el startup del sistema (`lifecycle.py`).

### Protección contra Ciclos de Bucle Infinitos en CPU

En bucles infinitos (`while True`) asincrónicos, un error imprevisto en la API de red o en las llamadas a nivel de sistema (`psutil`) puede provocar que el flujo salte directo al bloque `except`, esquivando el temporizador tradicional. Esto generaría miles de iteraciones por segundo, saturando el procesador.

La arquitectura mitiga esto forzando el `asyncio.sleep` en el bloque de nivel de salida del bucle, garantizando su ejecución sin importar el estado del procesamiento previo:

```python
async def watchdog_loop(app):
    while True:
        try:
            if is_enabled() and AUTHORIZED_USER != -1:
                # ...
                pass
        except Exception as e:
            print(f"Watchdog error: {e}")

        # El sleep se ejecuta SI O SI, previniendo que el hilo sature el servidor doméstico si algo falla.
        await asyncio.sleep(get_interval())

```

---

## Decisiones de Negocio e Infraestructura Doméstica

El diseño técnico responde de forma directa a las restricciones físicas y de uso del hardware de despliegue:

- **Optimización para mini-servidor doméstico:** Al correr en hardware local compartido con otros servicios del hogar, el bot minimiza el consumo de ciclos de reloj. Si el bot se configura en modo público (`-1`), el Watchdog inhabilita automáticamente las llamadas de sistema a `psutil`, quedando en estado de hibernación pasiva.
- **Desarrollo Multiplataforma Agnóstico:** Las tareas de administración real requieren comandos Linux avanzados (`sudo systemctl`, `certbot`, escritura en `/etc/nginx/`). Para permitir programar cómodamente en entornos de desarrollo Windows sin romper el arranque, la lógica implementa abstracciones mock que simulan la interacción con las terminales de Linux si detectan sistemas operativos alternativos.
- **Persistencia Liviana sin Base de Datos:** Para mantener el entorno libre de dependencias pesadas (como instancias de PostgreSQL o Docker innecesarios), los estados de configuración se gestionan mediante estructuras JSON atómicas en memoria con persistencia en disco duro local (`data/`), garantizando lecturas a velocidad de memoria y backups triviales.


---