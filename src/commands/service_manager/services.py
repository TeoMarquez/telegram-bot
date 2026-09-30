COMMAND = "service_manager_services"
DESCRIPTION = "⚙️ Gestionar servicios"


async def handler(update, context):
    from .flow import start_manage
    return await start_manage(update, context)
