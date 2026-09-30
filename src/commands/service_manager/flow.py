"""Inline menus and conversational workflows for Services Manager."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.helpers import escape_markdown
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from config import AUTHORIZED_USER
from services import service_manager_api as api
from utils import authorized_only

ROOT, SEARCH_MENU, SEARCH_INPUT, SEARCH_RESULTS, SERVICE_DETAIL, MANAGE_MENU, \
    STARTUP_MODE, DIRECTORY_INPUT, TAGS_MENU, TAG_CREATE_INPUT, DISCOVERY, \
    SERVICE_START_MENU, SERVICE_MANAGE_MENU, SERVICE_TAG_MENU, TAG_LIST, \
    ALIAS_INPUT, DESCRIPTION_INPUT, NEW_SERVICE_NAME, NEW_SERVICE_DESCRIPTION, \
    NEW_SERVICE_OPTIONS, NEW_SERVICE_ALIAS, RECOVER_RESULTS, RECOVER_CONFIRM, \
    DELETE_CONFIRM = range(24)

PAGE_SIZE = 10


def _keyboard(rows):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data=data) for label, data in row]
        for row in rows
        if row
    ])


def menu_keyboard():
    return _keyboard([
        [("🔎 Buscar", "sm:start:search"), ("⚙️ Gestionar servicios", "sm:start:manage")],
        [("➕ Nuevo servicio", "sm:start:create")],
        [("🏷️ Gestionar tags", "sm:start:tags")],
        [("🔄 Descubrir servicios", "sm:start:discovery")],
    ])


_root_markup = menu_keyboard


def menu_text():
    return "🧰 *Service Manager*\n\nElegí una opción:"


def _back_root():
    return _keyboard([[("⬅️ Volver al menú", "sm:back:root")]])


def _back_search():
    return _keyboard([[("⬅️ Volver a búsquedas", "sm:back:search")]])


def _back_manage():
    return _keyboard([[("⬅️ Volver a gestión", "sm:back:manage")]])


def _back_tags():
    return _keyboard([[("⬅️ Volver a tags", "sm:back:tags")]])


async def _show(update, text, markup=None):
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")
    else:
        await update.effective_message.reply_text(text, reply_markup=markup, parse_mode="Markdown")


async def _answer(update):
    if update.callback_query:
        await update.callback_query.answer()


def _service_text(service, tags=(), note=None):
    description = escape_markdown(service.get("description") or "Sin descripción")
    alias = escape_markdown(service.get("alias") or "Sin alias")
    tag_names = escape_markdown(", ".join(tag.get("name", str(tag)) for tag in tags) or "Sin tags")
    unit_name = escape_markdown(service["unit_name"])
    active = service.get("active")
    if active is True:
        status = "En ejecución"
    elif active is False:
        status = "Detenido"
    else:
        status = str(service.get("status") or "No disponible")
    status = escape_markdown(status)
    text = (
        f"🧩 *{unit_name}*\n\n"
        f"🆔 ID: `{service['id']}`\n"
        f"🏷️ Alias: {alias}\n"
        f"📝 Descripción: {description}\n"
        f"📡 Presente: {'Sí' if service.get('present') else 'No'}\n"
        f"👁️ Visible: {'Sí' if service.get('visible') else 'No'}\n"
        f"🧰 Tipo: {'Sistema' if service.get('system_service') else 'Usuario'}\n"
        f"🔖 Tags: {tag_names}\n"
        f"⚙️ Estado: {status}\n"
    )
    if note:
        text = f"{escape_markdown(note)}\n\n{text}"
    return text


def _service_page_markup(items, page, total_pages, *, kind):
    callback = "sm:recover:open" if kind == "recover" else "sm:open"
    rows = [[(f"🧩 {item['unit_name']} · #{item['id']}", f"{callback}:{item['id']}")] for item in items]
    nav = []
    if page > 1:
        nav.append(("⬅️ Anterior", "sm:page:prev"))
    if page < total_pages:
        nav.append(("Siguiente ➡️", "sm:page:next"))
    if nav:
        rows.append(nav)
    if kind == "recover":
        rows.append([("⬅️ Volver a gestión", "sm:back:manage")])
    else:
        rows.append([("⬅️ Volver a búsquedas", "sm:back:search")])
    return _keyboard(rows)


def _search_menu_markup():
    return _keyboard([
        [("📋 Listar servicios", "sm:search:list"), ("🔎 Buscar nombre o alias", "sm:search:query")],
        [("🔖 Buscar por tags", "sm:search:tags"), ("🖥️ Servicios de sistema", "sm:search:system")],
        [("⬅️ Volver al menú", "sm:back:root")],
    ])


def _manage_menu_markup():
    return _keyboard([
        [("📂 Ver directorio", "sm:manage:directory:view")],
        [("📁 Cambiar directorio", "sm:manage:directory:change")],
        [("♻️ Recuperar servicio", "sm:manage:recover")],
        [("⬅️ Volver al menú", "sm:back:root")],
    ])


def _tags_menu_markup():
    return _keyboard([
        [("➕ Nuevo tag", "sm:tag:create"), ("🗑️ Borrar tag", "sm:tag:delete")],
        [("⬅️ Volver al menú", "sm:back:root")],
    ])


def _service_detail_markup():
    return _keyboard([
        [("🚀 Gestionar arranque", "sm:service:start-menu")],
        [("🛠️ Gestionar servicio", "sm:service:manage-menu")],
        [("⬅️ Volver a resultados", "sm:back:results"), ("🏠 Menú", "sm:back:root")],
    ])


def _start_menu_markup():
    return _keyboard([
        [("▶️ Iniciar servicio", "sm:service:action:start"), ("⏹️ Parar servicio", "sm:service:action:stop")],
        [("🚦 Cambiar startup-mode", "sm:service:startup")],
        [("⬅️ Volver", "sm:back:service-detail")],
    ])


def _service_manage_menu_markup():
    return _keyboard([
        [("🏷️ Añadir alias", "sm:service:alias")],
        [("📝 Añadir descripción", "sm:service:description")],
        [("🔖 Modificar tags", "sm:service:tags")],
        [("👁️ Cambiar visibilidad", "sm:service:visibility")],
        [("🗑️ Borrar servicio", "sm:service:delete")],
        [("⬅️ Volver", "sm:back:service-detail")],
    ])


def _service_tag_menu_markup():
    return _keyboard([
        [("➕ Añadir tag", "sm:service:tag-add"), ("➖ Eliminar tags", "sm:service:tag-remove")],
        [("✨ Crear nuevo tag", "sm:service:tag-create")],
        [("⬅️ Volver", "sm:back:service-manage")],
    ])


def _new_service_options_markup(context):
    alias = context.user_data.get("sm_create_alias")
    tags = context.user_data.get("sm_create_tag_names", [])
    alias_label = "✏️ Cambiar alias" if alias else "🏷️ Añadir alias"
    tag_label = f"🔖 Añadir tags ({len(tags)})"
    return _keyboard([
        [(alias_label, "sm:new-service:alias")],
        [(tag_label, "sm:new-service:tags")],
        [("✅ Crear servicio", "sm:new-service:create")],
        [("⬅️ Volver al menú", "sm:back:root")],
    ])


def _new_service_options_text(context):
    alias = context.user_data.get("sm_create_alias")
    tags = context.user_data.get("sm_create_tag_names", [])
    details = [
        f"🧩 Nombre: `{escape_markdown(context.user_data.get('sm_create_name', ''))}`",
        f"📝 Descripción: {escape_markdown(context.user_data.get('sm_create_description', ''))}",
        f"🏷️ Alias: {escape_markdown(alias or 'Sin alias')}",
        f"🔖 Tags: {escape_markdown(', '.join(tags) or 'Sin tags')}",
    ]
    return "🆕 *Preparar nuevo servicio*\n\n" + "\n".join(details) + "\n\nPodés añadir un alias y tags antes de crearlo."


def _directory_menu_text(path=None):
    current = f"\n\n📂 Directorio actual: `{escape_markdown(path)}`" if path else ""
    return f"⚙️ *Directorio de servicios*{current}\n\nElegí una opción:"


async def start_search(update, context):
    await _answer(update)
    context.user_data["current_category"] = "service_manager"
    await _show(update, "🔎 *Buscar servicios*\n\nElegí el criterio de búsqueda:", _search_menu_markup())
    return SEARCH_MENU


async def start_manage(update, context):
    await _answer(update)
    context.user_data["current_category"] = "service_manager"
    await _show(update, "⚙️ *Gestionar servicios*\n\nElegí una operación:", _manage_menu_markup())
    return MANAGE_MENU


async def start_create_service(update, context):
    await _answer(update)
    context.user_data["current_category"] = "service_manager"
    context.user_data["sm_create_name"] = ""
    context.user_data["sm_create_description"] = ""
    context.user_data["sm_create_alias"] = ""
    context.user_data["sm_create_tag_names"] = []
    await _show(update, "🆕 *Nuevo servicio*\n\nEscribí el nombre del servicio (sin `.service`):", _back_root())
    return NEW_SERVICE_NAME


async def _new_service_name_input(update, context):
    name = update.effective_message.text.strip()
    if name.endswith(".service"):
        name = name[:-len(".service")]
    if not name:
        await _show(update, "El nombre no puede quedar vacío. Escribilo nuevamente:", _back_root())
        return NEW_SERVICE_NAME
    context.user_data["sm_create_name"] = name
    await _show(update, "📝 Escribí la descripción del servicio:", _back_root())
    return NEW_SERVICE_DESCRIPTION


async def _new_service_description_input(update, context):
    description = update.effective_message.text.strip()
    if not description:
        await _show(update, "La descripción no puede quedar vacía. Escribila nuevamente:", _back_root())
        return NEW_SERVICE_DESCRIPTION
    context.user_data["sm_create_description"] = description
    await _show(update, _new_service_options_text(context), _new_service_options_markup(context))
    return NEW_SERVICE_OPTIONS


async def _new_service_option(update, context):
    await _answer(update)
    action = update.callback_query.data.rsplit(":", 1)[1]
    if action == "alias":
        await _show(update, "🏷️ Escribí el alias del nuevo servicio:", _back_new_service_options())
        return NEW_SERVICE_ALIAS
    if action == "tags":
        try:
            tags = await api.get_tags()
            await _render_tag_list(update, context, "new_service", tags, 1)
            return TAG_LIST
        except api.ServiceManagerAPIError as exc:
            await _show(update, f"❌ No se pudieron cargar los tags.\n\n{escape_markdown(str(exc))}", _new_service_options_markup(context))
            return NEW_SERVICE_OPTIONS
    return await _create_new_service(update, context)


def _back_new_service_options():
    return _keyboard([[ ("⬅️ Volver", "sm:new-service:options") ]])


async def _new_service_alias_input(update, context):
    alias = update.effective_message.text.strip()
    if not alias:
        await _show(update, "El alias no puede quedar vacío. Escribilo nuevamente:", _back_new_service_options())
        return NEW_SERVICE_ALIAS
    context.user_data["sm_create_alias"] = alias
    await _show(update, _new_service_options_text(context), _new_service_options_markup(context))
    return NEW_SERVICE_OPTIONS


async def _back_new_service_options_handler(update, context):
    await _answer(update)
    await _show(update, _new_service_options_text(context), _new_service_options_markup(context))
    return NEW_SERVICE_OPTIONS


async def _new_service_create_tag(update, context):
    await _answer(update)
    context.user_data["sm_tag_create_origin"] = "new_service"
    await _show(update, "✏️ Escribí el nombre del tag nuevo. Se creará y quedará seleccionado para el servicio.", _keyboard([
        [("⬅️ Volver", "sm:tagcreate:back")],
    ]))
    return TAG_CREATE_INPUT


async def _create_new_service(update, context):
    name = context.user_data["sm_create_name"]
    description = context.user_data["sm_create_description"]
    tags = context.user_data.get("sm_create_tag_names", [])
    alias = context.user_data.get("sm_create_alias")
    try:
        created = await api.create_service(name, description)
    except api.ServiceManagerAPIError as exc:
        await _show(update, f"❌ No se pudo crear el servicio.\n\n{escape_markdown(str(exc))}", _new_service_options_markup(context))
        return NEW_SERVICE_OPTIONS

    created = created if isinstance(created, dict) else {}
    returned_name = created.get("unit_name") or created.get("name") or name
    unit_name = returned_name if str(returned_name).endswith(".service") else f"{returned_name}.service"
    failures = []
    visible = False
    try:
        await api.set_visibility(unit_name, True)
        visible = True
    except api.ServiceManagerAPIError as exc:
        failures.append(f"visibilidad: {exc}")
    if alias:
        try:
            await api.set_alias(unit_name, alias)
        except api.ServiceManagerAPIError as exc:
            failures.append(f"alias: {exc}")
    for tag_name in tags:
        try:
            await api.add_service_tag(unit_name, tag_name)
        except api.ServiceManagerAPIError as exc:
            failures.append(f"tag {tag_name}: {exc}")

    text = f"✅ *Servicio creado*\n\n🧩 `{escape_markdown(unit_name)}`"
    if visible:
        text += "\n👁️ Servicio visible."
    if alias and not any(item.startswith("alias:") for item in failures):
        text += f"\n🏷️ Alias: {escape_markdown(alias)}"
    if tags:
        succeeded_tags = [tag for tag in tags if not any(item.startswith(f"tag {tag}:") for item in failures)]
        text += f"\n🔖 Tags asociados: {escape_markdown(', '.join(succeeded_tags) or 'ninguno')}"
    if failures:
        text += "\n\n⚠️ El servicio se creó, pero hubo problemas al guardar algunos datos:\n"
        text += "\n".join(f"• {escape_markdown(error)}" for error in failures)
    context.user_data["sm_create_name"] = ""
    await _show(update, f"{text}\n\n{menu_text()}", menu_keyboard())
    return ROOT


async def start_tags(update, context):
    await _answer(update)
    context.user_data["current_category"] = "service_manager"
    await _show(update, "🏷️ *Gestionar tags*\n\nElegí una operación:", _tags_menu_markup())
    return TAGS_MENU


async def start_discovery(update, context):
    await _answer(update)
    context.user_data["current_category"] = "service_manager"
    try:
        progress = await api.discover()
        active = progress.get("active", False)
        text = (
            "🔄 *Discovery procesado*\n\n"
            f"• Lote: {progress.get('discovered', 0)} servicios\n"
            f"• Nuevos: {progress.get('added', 0)}\n"
            f"• Actualizados: {progress.get('refreshed', 0)}\n"
            f"• Marcados ausentes: {progress.get('marked_missing', 0)}\n"
            f"• Estado: {'En curso' if active else 'Completado'}"
        )
        markup = _keyboard([
            [("🔄 Procesar siguiente lote", "sm:discovery:continue")] if active else [],
            [("⬅️ Volver al menú", "sm:back:root")],
        ])
    except api.ServiceManagerAPIError as exc:
        text, markup = f"❌ *No se pudo ejecutar discovery*\n\n{escape_markdown(str(exc))}", _back_root()
    await _show(update, text, markup)
    return DISCOVERY


async def _search_choice(update, context):
    await _answer(update)
    choice = update.callback_query.data.rsplit(":", 1)[1]
    context.user_data["sm_list_mode"] = "public" if choice == "list" else choice
    context.user_data["sm_page"] = 1
    if choice in ("list", "system"):
        try:
            await _render_services(update, context)
            return SEARCH_RESULTS
        except api.ServiceManagerAPIError as exc:
            await _show(update, f"❌ {escape_markdown(str(exc))}", _search_menu_markup())
            return SEARCH_MENU
    if choice == "tags":
        try:
            tags = await api.get_tags()
            if not tags:
                await _show(update, "🏷️ No hay tags para buscar.", _search_menu_markup())
                return SEARCH_MENU
            await _render_tag_list(update, context, "search", tags, 1)
            return TAG_LIST
        except api.ServiceManagerAPIError as exc:
            await _show(update, f"❌ {escape_markdown(str(exc))}", _search_menu_markup())
            return SEARCH_MENU
    await _show(update, "✏️ Escribí el nombre o alias del servicio que querés buscar.", _back_search())
    return SEARCH_INPUT


async def _receive_search(update, context):
    term = update.effective_message.text.strip()
    kind = context.user_data.get("sm_list_mode")
    if not term:
        await _show(update, "Escribí un valor para buscar.", _back_search())
        return SEARCH_INPUT
    context.user_data["sm_term"] = term
    context.user_data["sm_page"] = 1
    context.user_data.pop("sm_tag_id", None)
    try:
        await _render_services(update, context)
        return SEARCH_RESULTS
    except api.ServiceManagerAPIError as exc:
        await _show(update, f"❌ No se pudo buscar.\n\n{escape_markdown(str(exc))}", _back_search())
        return SEARCH_INPUT


async def _render_services(update, context):
    requested_page = context.user_data.get("sm_page", 1)
    mode = context.user_data.get("sm_list_mode", "public")
    filters = {"page": requested_page, "per_page": PAGE_SIZE}
    if mode in ("public", "query", "tags"):
        filters.update(visible=True, system_service=False)
    elif mode == "system":
        filters.update(visible=True, system_service=True)
    elif mode == "recover":
        filters.update(visible=False)
    if mode == "query":
        filters["search"] = context.user_data.get("sm_term")
    elif mode == "tags":
        filters["tag_id"] = context.user_data.get("sm_tag_id")
    if mode == "query":
        # Name and alias share `search`; collect and uniquify the union before slicing pages.
        first_page = await api.list_services(**{**filters, "page": 1})
        unique_all = []
        seen_all = set()
        for api_page in range(1, max(1, first_page.get("total_pages", 1)) + 1):
            response = first_page if api_page == 1 else await api.list_services(
                **{**filters, "page": api_page}
            )
            for item in response["items"]:
                identity = item.get("id", item.get("unit_name"))
                if identity not in seen_all:
                    seen_all.add(identity)
                    unique_all.append(item)
        total_pages = max(1, (len(unique_all) + PAGE_SIZE - 1) // PAGE_SIZE)
        page_number = min(requested_page, total_pages)
        context.user_data["sm_page"] = page_number
        result = {
            "items": unique_all[(page_number - 1) * PAGE_SIZE:page_number * PAGE_SIZE],
            "page": page_number,
            "total_pages": total_pages,
            "total_items": len(unique_all),
        }
    else:
        result = await api.list_services(**filters)
    unique_items = []
    seen = set()
    for item in result["items"]:
        identity = item.get("id", item.get("unit_name"))
        if identity not in seen:
            seen.add(identity)
            unique_items.append(item)
    items = unique_items
    context.user_data["sm_current_items"] = items
    if not items:
        markup = _back_manage() if mode == "recover" else _back_search()
        label = "No hay servicios invisibles para recuperar." if mode == "recover" else "No se encontraron servicios."
        notice = context.user_data.pop("sm_services_notice", None)
        prefix = f"{escape_markdown(notice)}\n\n" if notice else ""
        await _show(update, f"{prefix}🔎 {label}", markup)
        return
    kind = "recover" if mode == "recover" else "search"
    heading = "Servicios invisibles" if mode == "recover" else "Servicios de sistema" if mode == "system" else "Servicios"
    notice = context.user_data.pop("sm_services_notice", None)
    text = (
        f"📋 *{heading}* · página {result['page']} de {max(result['total_pages'], 1)}\n"
        f"{result['total_items']} servicio(s).\n\nTocá un servicio para ver sus datos."
    )
    if notice:
        text = f"{escape_markdown(notice)}\n\n{text}"
    await _show(
        update,
        text,
        _service_page_markup(items, result["page"], result["total_pages"], kind=kind),
    )


async def _page_services(update, context):
    await _answer(update)
    page = context.user_data.get("sm_page", 1)
    context.user_data["sm_page"] = max(1, page + (1 if update.callback_query.data.endswith("next") else -1))
    try:
        await _render_services(update, context)
    except api.ServiceManagerAPIError as exc:
        mode = context.user_data.get("sm_list_mode")
        await _show(update, f"❌ {escape_markdown(str(exc))}", _back_manage() if mode == "recover" else _back_search())
    return RECOVER_RESULTS if context.user_data.get("sm_list_mode") == "recover" else SEARCH_RESULTS


async def _open_service(update, context):
    await _answer(update)
    service_id = int(update.callback_query.data.rsplit(":", 1)[1])
    item = next((row for row in context.user_data.get("sm_current_items", []) if row["id"] == service_id), None)
    if not item:
        is_recovery = context.user_data.get("sm_list_mode") == "recover"
        await _show(update, "⚠️ Ese resultado ya no está en la página actual.", _back_manage() if is_recovery else _back_search())
        return RECOVER_RESULTS if is_recovery else SEARCH_RESULTS
    try:
        mode = context.user_data.get("sm_list_mode", "public")
        filters = {"visible": True, "system_service": False}
        if mode == "system":
            filters = {"visible": True, "system_service": True}
        elif mode == "recover":
            filters = {"visible": False}
        service = await api.get_service(item["unit_name"], **filters)
        if not service:
            raise api.ServiceManagerAPIError("El servicio ya no aparece en la API.")
        tags = await api.get_service_tags(service["unit_name"])
        context.user_data["sm_selected_service"] = service
        context.user_data["sm_selected_tags"] = tags
        context.user_data["sm_result_origin"] = mode
        await _show(update, _service_text(service, tags), _service_detail_markup())
        return SERVICE_DETAIL
    except api.ServiceManagerAPIError as exc:
        await _show(update, f"❌ No se pudo cargar el servicio.\n\n{escape_markdown(str(exc))}", _back_manage() if context.user_data.get("sm_list_mode") == "recover" else _back_search())
        return RECOVER_RESULTS if context.user_data.get("sm_list_mode") == "recover" else SEARCH_RESULTS


async def _open_recovery_candidate(update, context):
    await _answer(update)
    service_id = int(update.callback_query.data.rsplit(":", 1)[1])
    service = next((row for row in context.user_data.get("sm_current_items", []) if row["id"] == service_id), None)
    if not service:
        await _show(update, "⚠️ Ese servicio ya no está en la página actual.", _back_manage())
        return RECOVER_RESULTS
    context.user_data["sm_recovery_candidate"] = service
    await _show(update, f"♻️ ¿Querés recuperar *{escape_markdown(service['unit_name'])}*?\n\nSolo se hará visible; no se iniciará.", _keyboard([
        [("✅ Sí, recuperar", "sm:recover:yes"), ("❌ No", "sm:recover:no")],
    ]))
    return RECOVER_CONFIRM


async def _recover_service_choice(update, context):
    await _answer(update)
    if update.callback_query.data.endswith(":no"):
        try:
            await _render_services(update, context)
        except api.ServiceManagerAPIError as exc:
            await _show(update, f"❌ {escape_markdown(str(exc))}", _back_manage())
        return RECOVER_RESULTS
    service = context.user_data.get("sm_recovery_candidate")
    if not service:
        await _show(update, "⚠️ No hay un servicio seleccionado para recuperar.", _manage_menu_markup())
        return MANAGE_MENU
    try:
        await api.set_visibility(service["unit_name"], True)
    except api.ServiceManagerAPIError as exc:
        await _show(update, f"❌ No se pudo recuperar el servicio.\n\n{escape_markdown(str(exc))}", _keyboard([
            [("✅ Reintentar", "sm:recover:yes"), ("❌ No", "sm:recover:no")],
        ]))
        return RECOVER_CONFIRM
    context.user_data["sm_services_notice"] = f"✅ {service['unit_name']} ahora está visible. No se inició."
    context.user_data["sm_page"] = 1
    try:
        await _render_services(update, context)
    except api.ServiceManagerAPIError as exc:
        await _show(update, f"✅ Servicio recuperado, pero no se pudo actualizar el listado.\n\n{escape_markdown(str(exc))}", _back_manage())
    return RECOVER_RESULTS


async def _show_selected_detail(update, context, note=None):
    service = context.user_data.get("sm_selected_service")
    if not service:
        await _show(update, "⚠️ No hay un servicio seleccionado.", _search_menu_markup())
        return
    try:
        refreshed = await api.get_service(service["unit_name"])
        if refreshed:
            service = refreshed
            context.user_data["sm_selected_service"] = service
        tags = await api.get_service_tags(service["unit_name"])
        context.user_data["sm_selected_tags"] = tags
    except api.ServiceManagerAPIError:
        tags = context.user_data.get("sm_selected_tags", [])
    await _show(update, _service_text(service, tags, note), _service_detail_markup())


async def _service_detail_choice(update, context):
    await _answer(update)
    action = update.callback_query.data
    if action == "sm:service:start-menu":
        await _show(update, "🚀 *Gestionar arranque*", _start_menu_markup())
        return SERVICE_START_MENU
    await _show(update, "🛠️ *Gestionar servicio*", _service_manage_menu_markup())
    return SERVICE_MANAGE_MENU


async def _start_service_action(update, context):
    await _answer(update)
    action = update.callback_query.data.rsplit(":", 1)[1]
    service = context.user_data["sm_selected_service"]
    try:
        result = await api.control_service(service["unit_name"], action)
        active = result.get("active") if isinstance(result, dict) else None
        state = "en ejecución" if active is True else "detenido" if active is False else "actualizado"
        await _show_selected_detail(update, context, f"✅ Servicio {state}.")
        return SERVICE_DETAIL
    except api.ServiceManagerAPIError as exc:
        await _show(update, f"❌ No se pudo {('iniciar' if action == 'start' else 'parar')} el servicio.\n\n{escape_markdown(str(exc))}", _start_menu_markup())
        return SERVICE_START_MENU


async def _startup_menu(update, context):
    await _answer(update)
    service = context.user_data["sm_selected_service"]
    unit_name = escape_markdown(service["unit_name"])
    await _show(update, f"🚦 Elegí el startup-mode para *{unit_name}*:", _keyboard([
        [("✅ enabled", "sm:service:startup:enabled"), ("⏸️ disabled", "sm:service:startup:disabled")],
        [("⬅️ Volver", "sm:back:start-menu")],
    ]))
    return STARTUP_MODE


async def _service_manage_choice(update, context):
    await _answer(update)
    action = update.callback_query.data.rsplit(":", 1)[1]
    if action == "delete":
        service = context.user_data["sm_selected_service"]
        await _show(update, f"🗑️ ¿Borrar lógicamente *{escape_markdown(service['unit_name'])}*?\n\nSe intentará detenerlo, ocultarlo y desactivar su inicio automático. El registro no se eliminará de la base de datos.", _keyboard([
            [("✅ Sí, borrar", "sm:service:delete:yes"), ("❌ No", "sm:service:delete:no")],
        ]))
        return DELETE_CONFIRM
    if action == "tags":
        await _show(update, "🔖 *Modificar tags del servicio*", _service_tag_menu_markup())
        return SERVICE_TAG_MENU
    if action == "visibility":
        service = context.user_data["sm_selected_service"]
        visible = not bool(service.get("visible", False))
        try:
            await api.set_visibility(service["unit_name"], visible)
            message = "👁️ Servicio visible." if visible else "🙈 Servicio oculto."
            await _show_selected_detail(update, context, message)
            return SERVICE_DETAIL
        except api.ServiceManagerAPIError as exc:
            await _show(update, f"❌ No se pudo cambiar la visibilidad.\n\n{escape_markdown(str(exc))}", _service_manage_menu_markup())
            return SERVICE_MANAGE_MENU
    field = "alias" if action == "alias" else "description"
    context.user_data["sm_edit_field"] = field
    prompt = "Escribí el nuevo alias:" if field == "alias" else "Escribí la descripción nueva:"
    state = ALIAS_INPUT if field == "alias" else DESCRIPTION_INPUT
    await _show(update, f"✏️ {prompt}", _keyboard([[("⬅️ Volver", "sm:back:service-manage")]]))
    return state


async def _save_service_text(update, context):
    text = update.effective_message.text.strip()
    field = context.user_data["sm_edit_field"]
    service = context.user_data["sm_selected_service"]
    if not text:
        await _show(update, "El valor no puede quedar vacío. Escribilo nuevamente:", _keyboard([
            [("⬅️ Volver", "sm:back:service-manage")],
        ]))
        return ALIAS_INPUT if field == "alias" else DESCRIPTION_INPUT
    try:
        if field == "alias":
            await api.set_alias(service["unit_name"], text)
            note = "✅ Alias actualizado."
        else:
            await api.set_description(service["unit_name"], text)
            note = "✅ Descripción actualizada."
        await _show_selected_detail(update, context, note)
        return SERVICE_DETAIL
    except api.ServiceManagerAPIError as exc:
        await _show(update, f"❌ No se pudo actualizar.\n\n{escape_markdown(str(exc))}\n\nEscribí el valor nuevamente:", _keyboard([
            [("⬅️ Volver", "sm:back:service-manage")],
        ]))
        return ALIAS_INPUT if field == "alias" else DESCRIPTION_INPUT


async def _service_tag_choice(update, context):
    await _answer(update)
    action = update.callback_query.data.rsplit(":", 1)[1]
    service = context.user_data["sm_selected_service"]
    if action == "tag-add":
        action = "add"
    elif action == "tag-remove":
        action = "remove"
    if action in ("add", "remove"):
        try:
            tags = await (api.get_tags() if action == "add" else api.get_service_tags(service["unit_name"]))
            if not tags:
                await _show(update, "🏷️ No hay tags para esta operación.", _service_tag_menu_markup())
                return SERVICE_TAG_MENU
            await _render_tag_list(update, context, "add_service" if action == "add" else "remove_service", tags, 1)
            return TAG_LIST
        except api.ServiceManagerAPIError as exc:
            await _show(update, f"❌ {escape_markdown(str(exc))}", _service_tag_menu_markup())
            return SERVICE_TAG_MENU
    context.user_data["sm_tag_create_origin"] = "service"
    await _show(update, "✏️ Escribí el nombre del tag nuevo. Se creará sin asociarlo al servicio.", _keyboard([
        [("⬅️ Volver", "sm:tagcreate:back")],
    ]))
    return TAG_CREATE_INPUT


async def _back_to_results(update, context):
    await _answer(update)
    try:
        await _render_services(update, context)
    except api.ServiceManagerAPIError as exc:
        await _show(update, f"❌ {escape_markdown(str(exc))}", _back_search())
    return RECOVER_RESULTS if context.user_data.get("sm_list_mode") == "recover" else SEARCH_RESULTS


async def _delete_service_choice(update, context):
    await _answer(update)
    if update.callback_query.data.endswith(":no"):
        await _show(update, "🛠️ *Gestionar servicio*", _service_manage_menu_markup())
        return SERVICE_MANAGE_MENU

    service = context.user_data.get("sm_selected_service")
    if not service:
        await _show(update, "⚠️ No hay un servicio seleccionado.", _search_menu_markup())
        return SEARCH_MENU

    steps = [
        ("Servicio detenido", lambda: api.control_service(service["unit_name"], "stop")),
        ("Servicio oculto", lambda: api.set_visibility(service["unit_name"], False)),
        ("Inicio automático desactivado", lambda: api.set_startup_mode(service["unit_name"], "disabled")),
    ]
    completed, failures = [], []
    for label, operation in steps:
        try:
            await operation()
            completed.append(label)
        except api.ServiceManagerAPIError as exc:
            failures.append(f"{label}: {exc}")

    text = f"🗑️ *Baja lógica de {escape_markdown(service['unit_name'])}*\n\n"
    if completed:
        text += "✅ " + "\n✅ ".join(completed) + "\n"
    if failures:
        text += "\n⚠️ No se completaron todos los pasos:\n" + "\n".join(
            f"• {escape_markdown(failure)}" for failure in failures
        )
    else:
        text += "\nEl registro se conserva y puede recuperarse desde Gestionar servicios."
    await _show(update, f"{text}\n\n{menu_text()}", menu_keyboard())
    return ROOT


async def _manage_choice(update, context):
    await _answer(update)
    operation = update.callback_query.data.rsplit(":", 1)[1]
    if operation == "recover":
        context.user_data["sm_list_mode"] = "recover"
        context.user_data["sm_page"] = 1
        try:
            await _render_services(update, context)
        except api.ServiceManagerAPIError as exc:
            await _show(update, f"❌ {escape_markdown(str(exc))}", _manage_menu_markup())
            return MANAGE_MENU
        return RECOVER_RESULTS
    if operation == "view":
        try:
            current = await api.get_service_directory()
            context.user_data["sm_current_directory"] = current.get("path", "")
            await _show(
                update,
                _directory_menu_text(current.get("path", "")),
                _manage_menu_markup(),
            )
            return MANAGE_MENU
        except api.ServiceManagerAPIError as exc:
            await _show(update, f"❌ {escape_markdown(str(exc))}", _manage_menu_markup())
            return MANAGE_MENU
    try:
        current = await api.get_service_directory()
        context.user_data["sm_current_directory"] = current.get("path", "")
    except api.ServiceManagerAPIError:
        context.user_data["sm_current_directory"] = ""
    await _show(update, "✏️ Escribí la ruta absoluta existente para el directorio de servicios.", _back_manage())
    return DIRECTORY_INPUT


async def _startup_choice(update, context):
    await _answer(update)
    mode = update.callback_query.data.rsplit(":", 1)[1]
    service = context.user_data["sm_selected_service"]
    try:
        result = await api.set_startup_mode(service["unit_name"], mode)
        observed = result.get("startup_mode", mode) if isinstance(result, dict) else mode
        observed = str(observed).lower()
        await _show_selected_detail(update, context, f"✅ Startup-mode actualizado a `{escape_markdown(observed)}`.")
        return SERVICE_DETAIL
    except api.ServiceManagerAPIError as exc:
        await _show(update, f"❌ No se pudo cambiar startup-mode.\n\n{escape_markdown(str(exc))}", _start_menu_markup())
        return SERVICE_START_MENU


async def _directory_input(update, context):
    path = update.effective_message.text.strip()
    try:
        result = await api.set_service_directory(path)
        await _show(update, f"✅ Directorio actualizado:\n`{escape_markdown(result.get('path', path))}`", _manage_menu_markup())
        return MANAGE_MENU
    except api.ServiceManagerAPIError as exc:
        await _show(update, f"❌ No se pudo cambiar el directorio.\n\n{escape_markdown(str(exc))}\n\nProbá con una ruta absoluta existente:", _back_manage())
        return DIRECTORY_INPUT


async def _render_tag_list(update, context, mode, tags, page=1, note=None):
    context.user_data["sm_tag_list_mode"] = mode
    context.user_data["sm_tag_items"] = tags
    pages = max(1, (len(tags) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(max(page, 1), pages)
    context.user_data["sm_tag_page"] = page
    visible = tags[(page - 1) * PAGE_SIZE:page * PAGE_SIZE]
    selected_names = context.user_data.get("sm_create_tag_names", []) if mode == "new_service" else []
    rows = [[(
        f"{'✅' if tag['name'] in selected_names else '🏷️'} {tag['name']}",
        f"sm:tag:pick:{tag['id']}",
    )] for tag in visible]
    navigation = []
    if page > 1:
        navigation.append(("⬅️ Anterior", "sm:tagpage:prev"))
    if page < pages:
        navigation.append(("Siguiente ➡️", "sm:tagpage:next"))
    if navigation:
        rows.append(navigation)
    if mode == "new_service":
        rows.append([("✨ Nuevo tag", "sm:new-service:tag:create")])
    rows.append([("⬅️ Volver", "sm:taglist:back")])
    captions = {
        "search": "Elegí un tag para buscar servicios",
        "add_service": "Elegí el tag que querés asociar",
        "remove_service": "Elegí el tag que querés quitar",
        "delete_global": "Elegí el tag que querés borrar globalmente",
        "new_service": "Elegí los tags para el nuevo servicio",
    }
    title = f"🏷️ *{captions[mode]}* · página {page}/{pages}"
    if note:
        title = f"{escape_markdown(note)}\n\n{title}"
    await _show(update, title, _keyboard(rows))


async def _tag_page(update, context):
    await _answer(update)
    page = context.user_data.get("sm_tag_page", 1)
    page += 1 if update.callback_query.data.endswith("next") else -1
    await _render_tag_list(
        update, context, context.user_data["sm_tag_list_mode"],
        context.user_data.get("sm_tag_items", []), page,
    )
    return TAG_LIST


async def _tag_list_back(update, context):
    await _answer(update)
    mode = context.user_data.get("sm_tag_list_mode")
    if mode == "search":
        await _show(update, "🔎 *Buscar servicios*\n\nElegí el criterio de búsqueda:", _search_menu_markup())
        return SEARCH_MENU
    if mode in ("add_service", "remove_service"):
        await _show(update, "🔖 *Modificar tags del servicio*", _service_tag_menu_markup())
        return SERVICE_TAG_MENU
    if mode == "new_service":
        await _show(update, _new_service_options_text(context), _new_service_options_markup(context))
        return NEW_SERVICE_OPTIONS
    await _show(update, "🏷️ *Gestionar tags*\n\nElegí una operación:", _tags_menu_markup())
    return TAGS_MENU


async def _tag_pick(update, context):
    await _answer(update)
    tag_id = int(update.callback_query.data.rsplit(":", 1)[1])
    mode = context.user_data.get("sm_tag_list_mode")
    tags = context.user_data.get("sm_tag_items", [])
    tag = next((item for item in tags if item["id"] == tag_id), None)
    if not tag:
        return await _tag_list_back(update, context)
    if mode == "new_service":
        selected = context.user_data.setdefault("sm_create_tag_names", [])
        if tag["name"] in selected:
            selected.remove(tag["name"])
        else:
            selected.append(tag["name"])
        await _render_tag_list(
            update, context, mode, tags, context.user_data.get("sm_tag_page", 1)
        )
        return TAG_LIST
    if mode == "search":
        context.user_data["sm_tag_id"] = tag_id
        context.user_data["sm_list_mode"] = "tags"
        context.user_data.pop("sm_term", None)
        context.user_data["sm_page"] = 1
        try:
            await _render_services(update, context)
            return SEARCH_RESULTS
        except api.ServiceManagerAPIError as exc:
            await _show(update, f"❌ {escape_markdown(str(exc))}", _search_menu_markup())
            return SEARCH_MENU

    service = context.user_data.get("sm_selected_service")
    if mode in ("add_service", "remove_service") and not service:
        await _show(update, "⚠️ No hay un servicio seleccionado.", _root_markup())
        return ROOT
    try:
        if mode == "add_service":
            await api.add_service_tag(service["unit_name"], tag["name"])
            await _show(update, f"✅ Tag *{escape_markdown(tag['name'])}* asociado al servicio.", _service_tag_menu_markup())
            return SERVICE_TAG_MENU
        if mode == "remove_service":
            await api.remove_service_tag(service["unit_name"], tag["name"])
            remaining = await api.get_service_tags(service["unit_name"])
            if remaining:
                page = min(context.user_data.get("sm_tag_page", 1), max(1, (len(remaining) + PAGE_SIZE - 1) // PAGE_SIZE))
                await _render_tag_list(update, context, mode, remaining, page, f"Tag {tag['name']} quitado.")
                return TAG_LIST
            await _show(update, f"✅ Tag *{escape_markdown(tag['name'])}* quitado. No quedan tags asociados.", _service_tag_menu_markup())
            return SERVICE_TAG_MENU
        await api.delete_tag(tag["name"])
        remaining = await api.get_tags()
        if remaining:
            page = min(context.user_data.get("sm_tag_page", 1), max(1, (len(remaining) + PAGE_SIZE - 1) // PAGE_SIZE))
            await _render_tag_list(update, context, mode, remaining, page, f"Tag {tag['name']} eliminado.")
            return TAG_LIST
        await _show(update, "✅ Tag eliminado. No quedan tags.", _tags_menu_markup())
        return TAGS_MENU
    except api.ServiceManagerAPIError as exc:
        markup = _service_tag_menu_markup() if mode in ("add_service", "remove_service") else _tags_menu_markup()
        await _show(update, f"❌ No se pudo completar la operación.\n\n{escape_markdown(str(exc))}", markup)
        return SERVICE_TAG_MENU if mode in ("add_service", "remove_service") else TAGS_MENU


async def _tags_choice(update, context):
    await _answer(update)
    action = update.callback_query.data.rsplit(":", 1)[1]
    if action == "create":
        context.user_data["sm_tag_create_origin"] = "global"
        await _show(update, "✏️ Escribí el nombre del nuevo tag.", _keyboard([[("⬅️ Volver", "sm:tagcreate:back")]]))
        return TAG_CREATE_INPUT
    try:
        all_tags = await api.get_tags()
        if not all_tags:
            await _show(update, "🏷️ No hay tags para borrar.", _tags_menu_markup())
            return TAGS_MENU
        await _render_tag_list(update, context, "delete_global", all_tags)
        return TAG_LIST
    except api.ServiceManagerAPIError as exc:
        await _show(update, f"❌ {escape_markdown(str(exc))}", _tags_menu_markup())
        return TAGS_MENU


async def _create_tag_input(update, context):
    name = update.effective_message.text.strip()
    try:
        tag = await api.create_tag(name)
        origin = context.user_data.get("sm_tag_create_origin", "global")
        if origin == "new_service":
            created_name = tag.get("name", name) if isinstance(tag, dict) else name
            selected = context.user_data.setdefault("sm_create_tag_names", [])
            if created_name not in selected:
                selected.append(created_name)
            try:
                all_tags = await api.get_tags()
            except api.ServiceManagerAPIError:
                all_tags = context.user_data.get("sm_tag_items", [])
                if isinstance(tag, dict) and tag.get("id") and not any(item.get("id") == tag["id"] for item in all_tags):
                    all_tags = [*all_tags, tag]
            await _render_tag_list(update, context, "new_service", all_tags, 1, f"Tag {created_name} creado y seleccionado.")
            return TAG_LIST
        markup = _service_tag_menu_markup() if origin == "service" else _tags_menu_markup()
        tag_name = tag.get("name", name) if isinstance(tag, dict) else name
        tag_id = tag.get("id", "—") if isinstance(tag, dict) else "—"
        await _show(update, f"✅ Tag creado: *{escape_markdown(tag_name)}* · ID `{tag_id}`. No se asoció a ningún servicio.", markup)
        return SERVICE_TAG_MENU if origin == "service" else TAGS_MENU
    except api.ServiceManagerAPIError as exc:
        await _show(update, f"❌ No se pudo crear el tag.\n\n{escape_markdown(str(exc))}\n\nEscribí otro nombre:", _keyboard([[("⬅️ Volver", "sm:tagcreate:back")]]))
        return TAG_CREATE_INPUT


async def _back_root_handler(update, context):
    await _answer(update)
    await _show(update, menu_text(), menu_keyboard())
    return ROOT


async def _back_search_handler(update, context):
    await _answer(update)
    await _show(update, "🔎 *Buscar servicios*\n\nElegí el criterio de búsqueda:", _search_menu_markup())
    return SEARCH_MENU


async def _back_manage_handler(update, context):
    await _answer(update)
    await _show(update, "⚙️ *Gestionar servicios*\n\nElegí una operación:", _manage_menu_markup())
    return MANAGE_MENU


async def _back_tags_handler(update, context):
    await _answer(update)
    await _show(update, "🏷️ *Gestionar tags*\n\nElegí una operación:", _tags_menu_markup())
    return TAGS_MENU


async def _back_service_detail_handler(update, context):
    await _answer(update)
    await _show_selected_detail(update, context)
    return SERVICE_DETAIL


async def _back_service_manage_handler(update, context):
    await _answer(update)
    await _show(update, "🛠️ *Gestionar servicio*", _service_manage_menu_markup())
    return SERVICE_MANAGE_MENU


async def _back_start_menu_handler(update, context):
    await _answer(update)
    await _show(update, "🚀 *Gestionar arranque*", _start_menu_markup())
    return SERVICE_START_MENU


async def _back_tag_create_handler(update, context):
    await _answer(update)
    if context.user_data.get("sm_tag_create_origin") == "service":
        await _show(update, "🔖 *Modificar tags del servicio*", _service_tag_menu_markup())
        return SERVICE_TAG_MENU
    if context.user_data.get("sm_tag_create_origin") == "new_service":
        tags = context.user_data.get("sm_tag_items", [])
        await _render_tag_list(update, context, "new_service", tags, context.user_data.get("sm_tag_page", 1))
        return TAG_LIST
    await _show(update, "🏷️ *Gestionar tags*\n\nElegí una operación:", _tags_menu_markup())
    return TAGS_MENU


async def _cancel(update, context):
    await _answer(update)
    await _show(update, f"❌ Flujo cancelado.\n\n{menu_text()}", menu_keyboard())
    return ROOT


CONVERSATION = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(start_search, pattern=r"^sm:start:search$"),
        CallbackQueryHandler(start_manage, pattern=r"^sm:start:manage$"),
        CallbackQueryHandler(start_create_service, pattern=r"^sm:start:create$"),
        CallbackQueryHandler(start_tags, pattern=r"^sm:start:tags$"),
        CallbackQueryHandler(start_discovery, pattern=r"^sm:start:discovery$"),
        CallbackQueryHandler(start_search, pattern=r"^service_manager_search$"),
        CallbackQueryHandler(start_manage, pattern=r"^service_manager_services$"),
        CallbackQueryHandler(start_create_service, pattern=r"^service_manager_create$"),
        CallbackQueryHandler(start_tags, pattern=r"^service_manager_tags$"),
        CallbackQueryHandler(start_discovery, pattern=r"^service_manager_discovery$"),
    ],
    states={
        ROOT: [
            CallbackQueryHandler(start_search, pattern=r"^sm:start:search$"),
            CallbackQueryHandler(start_manage, pattern=r"^sm:start:manage$"),
            CallbackQueryHandler(start_create_service, pattern=r"^sm:start:create$"),
            CallbackQueryHandler(start_tags, pattern=r"^sm:start:tags$"),
            CallbackQueryHandler(start_discovery, pattern=r"^sm:start:discovery$"),
        ],
        SEARCH_MENU: [
            CallbackQueryHandler(_search_choice, pattern=r"^sm:search:(list|query|tags|system)$"),
            CallbackQueryHandler(_back_root_handler, pattern=r"^sm:back:root$"),
        ],
        SEARCH_INPUT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, _receive_search),
            CallbackQueryHandler(_back_search_handler, pattern=r"^sm:back:search$"),
        ],
        SEARCH_RESULTS: [
            CallbackQueryHandler(_open_service, pattern=r"^sm:open:\d+$"),
            CallbackQueryHandler(_page_services, pattern=r"^sm:page:(prev|next)$"),
            CallbackQueryHandler(_back_search_handler, pattern=r"^sm:back:search$"),
        ],
        SERVICE_DETAIL: [
            CallbackQueryHandler(_back_to_results, pattern=r"^sm:back:results$"),
            CallbackQueryHandler(_back_root_handler, pattern=r"^sm:back:root$"),
            CallbackQueryHandler(_service_detail_choice, pattern=r"^sm:service:(start-menu|manage-menu)$"),
        ],
        MANAGE_MENU: [
            CallbackQueryHandler(_manage_choice, pattern=r"^sm:manage:(directory:(view|change)|recover)$"),
            CallbackQueryHandler(_back_root_handler, pattern=r"^sm:back:root$"),
        ],
        SERVICE_START_MENU: [
            CallbackQueryHandler(_start_service_action, pattern=r"^sm:service:action:(start|stop)$"),
            CallbackQueryHandler(_startup_menu, pattern=r"^sm:service:startup$"),
            CallbackQueryHandler(_back_service_detail_handler, pattern=r"^sm:back:service-detail$"),
        ],
        SERVICE_MANAGE_MENU: [
            CallbackQueryHandler(_service_manage_choice, pattern=r"^sm:service:(alias|description|tags|visibility|delete)$"),
            CallbackQueryHandler(_back_service_detail_handler, pattern=r"^sm:back:service-detail$"),
        ],
        DELETE_CONFIRM: [
            CallbackQueryHandler(_delete_service_choice, pattern=r"^sm:service:delete:(yes|no)$"),
        ],
        SERVICE_TAG_MENU: [
            CallbackQueryHandler(_service_tag_choice, pattern=r"^sm:service:tag-(add|remove|create)$"),
            CallbackQueryHandler(_back_service_manage_handler, pattern=r"^sm:back:service-manage$"),
        ],
        STARTUP_MODE: [
            CallbackQueryHandler(_startup_choice, pattern=r"^sm:service:startup:(enabled|disabled)$"),
            CallbackQueryHandler(_back_start_menu_handler, pattern=r"^sm:back:start-menu$"),
        ],
        ALIAS_INPUT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, _save_service_text),
            CallbackQueryHandler(_back_service_manage_handler, pattern=r"^sm:back:service-manage$"),
        ],
        DESCRIPTION_INPUT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, _save_service_text),
            CallbackQueryHandler(_back_service_manage_handler, pattern=r"^sm:back:service-manage$"),
        ],
        DIRECTORY_INPUT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, _directory_input),
            CallbackQueryHandler(_back_manage_handler, pattern=r"^sm:back:manage$"),
        ],
        TAGS_MENU: [
            CallbackQueryHandler(_tags_choice, pattern=r"^sm:tag:(create|delete)$"),
            CallbackQueryHandler(_back_root_handler, pattern=r"^sm:back:root$"),
        ],
        TAG_LIST: [
            CallbackQueryHandler(_tag_pick, pattern=r"^sm:tag:pick:\d+$"),
            CallbackQueryHandler(_new_service_create_tag, pattern=r"^sm:new-service:tag:create$"),
            CallbackQueryHandler(_tag_page, pattern=r"^sm:tagpage:(prev|next)$"),
            CallbackQueryHandler(_tag_list_back, pattern=r"^sm:taglist:back$"),
        ],
        TAG_CREATE_INPUT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, _create_tag_input),
            CallbackQueryHandler(_back_tag_create_handler, pattern=r"^sm:tagcreate:back$"),
        ],
        DISCOVERY: [
            CallbackQueryHandler(start_discovery, pattern=r"^sm:discovery:continue$"),
            CallbackQueryHandler(_back_root_handler, pattern=r"^sm:back:root$"),
        ],
        NEW_SERVICE_NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, _new_service_name_input),
            CallbackQueryHandler(_back_root_handler, pattern=r"^sm:back:root$"),
        ],
        NEW_SERVICE_DESCRIPTION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, _new_service_description_input),
            CallbackQueryHandler(_back_root_handler, pattern=r"^sm:back:root$"),
        ],
        NEW_SERVICE_OPTIONS: [
            CallbackQueryHandler(_new_service_option, pattern=r"^sm:new-service:(alias|tags|create)$"),
            CallbackQueryHandler(_back_root_handler, pattern=r"^sm:back:root$"),
        ],
        NEW_SERVICE_ALIAS: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, _new_service_alias_input),
            CallbackQueryHandler(_back_new_service_options_handler, pattern=r"^sm:new-service:options$"),
        ],
        RECOVER_RESULTS: [
            CallbackQueryHandler(_open_recovery_candidate, pattern=r"^sm:recover:open:\d+$"),
            CallbackQueryHandler(_page_services, pattern=r"^sm:page:(prev|next)$"),
            CallbackQueryHandler(_back_manage_handler, pattern=r"^sm:back:manage$"),
        ],
        RECOVER_CONFIRM: [
            CallbackQueryHandler(_recover_service_choice, pattern=r"^sm:recover:(yes|no)$"),
        ],
    },
    fallbacks=[
        CommandHandler("cancelar", _cancel),
        CallbackQueryHandler(_cancel, pattern=r"^sm:cancel$"),
    ],
    per_chat=True,
    per_user=True,
    allow_reentry=True,
)

# Core authorization wraps flat handlers; protect handlers nested inside this conversation too.
if AUTHORIZED_USER != -1:
    nested_handlers = [*CONVERSATION.entry_points, *CONVERSATION.fallbacks]
    nested_handlers.extend(handler for state_handlers in CONVERSATION.states.values() for handler in state_handlers)
    for nested_handler in nested_handlers:
        if getattr(nested_handler, "callback", None):
            nested_handler.callback = authorized_only(nested_handler.callback)
