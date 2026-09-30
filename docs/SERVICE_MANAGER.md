# Integración Telegram ↔ Services Manager

## Estado

La categoría `service_manager` enlaza con la API REST de Services Manager (`/api/v1`).

## Procedencia de la API

La API que consume este bot pertenece al proyecto [Services-Manager](https://github.com/TeoMarquez/Services-Manager). Allí se obtiene el código del servicio REST y su contrato; este repositorio contiene únicamente la integración del bot. Para usarla, ejecutá Services-Manager en el servidor correspondiente y configurá en `.env` la URL base de esa instancia y su token de acceso.

## Configuración

Agregar al `.env` local:

```dotenv
url_api_service_manager=http://127.0.0.1:3000
token_service_manager=...
```

La URL es la base sin `/api/v1`. El cliente añade ese prefijo y envía `Authorization: Bearer ...`. No guardar tokens reales en este documento ni en el repositorio.

## Grafo conversacional acordado

```text
Service Manager
├── Buscar
│   ├── listar servicios visibles no-system
│   ├── buscar por nombre o alias (una consulta unificada)
│   ├── buscar por tag
│   └── servicios de sistema visibles
│       └── resultados en botones inline, 10 por página
│           └── detalle del servicio
│               ├── Gestionar arranque: iniciar, parar, startup-mode
│               └── Gestionar servicio: alias, descripción, tags, visibilidad, baja lógica
├── Nuevo servicio
│   ├── capturar nombre y descripción
│   ├── añadir alias opcional
│   ├── elegir tags existentes (selección múltiple, 10 por página) o crear tag
│   └── crear servicio y luego guardar alias/tags seleccionados
├── Gestionar servicios
│   ├── ver directorio
│   ├── cambiar directorio
│   └── recuperar servicio invisible (confirmar y hacer visible)
├── Gestionar tags
│   ├── crear
│   └── borrar
└── Descubrir servicios (un lote por llamada; continuar mientras active=true)
```

Los flujos con texto usan `ConversationHandler`; navegación, selección de servicios/tags y páginas son botones inline que editan el mensaje actual. Todos los listados del bot muestran 10 elementos por página. La lista de tags se pagina localmente porque `GET /tags` no documenta paginación. Las búsquedas de usuario aplican `visible=true` y `system_service=false`; la opción de servicios de sistema aplica `visible=true` y `system_service=true`. La búsqueda unificada de nombre/alias usa `search` y deduplica por ID antes de paginar. La búsqueda por tags usa `GET /tags` y consulta los servicios mediante `tag_id`, con los filtros de usuario.

Al abrir un resultado, el bot carga la ficha con `GET /api/v1/services/{unit_name}` y sus tags con `GET /api/v1/services/{unit_name}/tags`. La ruta de detalle devuelve `active` como booleano calculado desde systemd; el bot lo presenta como “En ejecución” o “Detenido”. La API no tiene ruta de detalle por ID.

La creación de un tag desde el submenu de modificación crea el tag global y no lo asigna al servicio seleccionado. Dentro del flujo Nuevo servicio, los tags se seleccionan antes de crear; el botón Crear ejecuta `POST /services`, establece inmediatamente `visible=true` y luego asigna alias/tags seleccionados. La baja lógica ejecuta parada, visibilidad false y startup-mode disabled; no elimina filas de la base de datos. Recuperar lista invisibles y, con confirmación, solo establece visibilidad true. Volver al menú raíz desde `/service_manager` y desde una conversación usa el mismo texto y teclado.

## Mapa de archivos

- `src/config.py`: carga URL y token desde `.env`.
- `src/services/service_manager_api.py`: cliente HTTP, bearer token, timeout y wrappers de endpoint.
- `src/commands/service_manager/`: categoría y contratos de sus comandos conversacionales.
- `src/commands/service_manager/flow.py`: estados, teclados inline, paginación y presentación.

## Rutas usadas

| Función | Endpoint |
|---|---|
| Discovery | `POST /api/v1/discovery` |
| Buscar/listar | `GET /api/v1/services` |
| Detalle y estado activo | `GET /api/v1/services/{unit_name}`; incluye `active: true/false` consultado desde systemd |
| Crear servicio | `POST /api/v1/services`, JSON `{"name":"worker","description":"Worker de ejemplo"}`; crea `worker.service` y devuelve `201` |
| Visibilidad | `PUT /api/v1/services/{unit_name}/visibility` |
| Start/stop | `POST /api/v1/services/{unit_name}/start` y `/stop` |
| Startup mode | `PUT /api/v1/services/{unit_name}/startup-mode` |
| Baja lógica | `POST /api/v1/services/{unit_name}/stop`, luego `PUT .../visibility` con `{"visible":false}` y `PUT .../startup-mode` con `{"mode":"disabled"}` |
| Recuperar | `PUT /api/v1/services/{unit_name}/visibility` con `{"visible":true}`; no inicia el servicio |
| Directorio | `GET` y `PUT /api/v1/settings/service-directory` |
| Alias | `PUT /api/v1/services/{unit_name}/alias` |
| Descripción | `PUT /api/v1/services/{unit_name}/description`, JSON `{"description":"..."}`; respuesta `204 No Content` |
| Tags globales | `GET`, `POST`, `DELETE /api/v1/tags` |
| Tags por servicio | `GET /api/v1/services/{unit_name}/tags`; `PUT` asigna y `DELETE` quita `/tags/{tag_name}` |

No se implementa reset porque no forma parte del alcance conversacional solicitado.

## Decisiones y límites

- `per_page=10` para los listados inline; se muestran controles anterior/siguiente cuando corresponde.
- Las páginas de tags se obtienen a partir del listado `GET /tags` y se muestran en bloques de diez botones.
- La creación de servicios llama `POST /services` solo al confirmar, hace visible el nuevo servicio inmediatamente y después guarda alias/tags con llamadas posteriores; informa los fallos parciales sin ocultar que el servicio fue creado.
- Las consultas de servicio visibles excluyen servicios de sistema salvo la opción explícita “Servicios de sistema”; la recuperación pagina `visible=false`.
- “Borrar servicio” es una baja lógica (stop, hide, disable), no llama a DELETE ni borra datos; todos los pasos se intentan y se informan fallos parciales.
- Los callbacks y mensajes de texto internos del `ConversationHandler` usan el mismo control de autorización del bot.
- Valores del API se escapan antes de insertarse en Markdown.
- El directorio debe ser absoluto, existente y carpeta, según validación de la API.
- `startup-mode` solo admite `enabled` y `disabled`.
- Discovery procesa un lote por solicitud; el usuario puede pedir el siguiente mientras el checkpoint devuelva `active=true`.
- El API controla el systemd del servidor que lo aloja; los botones iniciar/parar no son operaciones simuladas.

## Verificación de la implementación inicial

- La sintaxis Python compila y el cargador central construye los handlers con la nueva conversación.
- Falta probar llamadas contra una instancia de Services Manager y recorrer los caminos desde Telegram.
- No se ha ejecutado la suite de pruebas del bot.
