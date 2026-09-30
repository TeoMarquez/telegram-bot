COMMAND = "service_manager_search"
DESCRIPTION = "🔎 Buscar servicios"


async def handler(update, context):
    from .flow import start_search
    return await start_search(update, context)
