COMMAND = "service_manager_discovery"
DESCRIPTION = "🔄 Descubrir servicios"


async def handler(update, context):
    from .flow import start_discovery
    return await start_discovery(update, context)
