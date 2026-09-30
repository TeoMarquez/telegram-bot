COMMAND = "service_manager_tags"
DESCRIPTION = "🏷️ Gestionar tags"


async def handler(update, context):
    from .flow import start_tags
    return await start_tags(update, context)
