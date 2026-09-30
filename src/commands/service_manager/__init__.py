"""Telegram category for the Services Manager API."""

from . import search, services, tags, discovery, flow

COMMAND = "service_manager"
CATEGORY = "🧰 Service Manager"
DESCRIPTION = "Buscar y gestionar servicios Linux"

COMMANDS = [search, services, tags, discovery]
CONVERSATIONS = [flow.CONVERSATION]
CONVERSATION_COMMANDS = COMMANDS


def render_menu_keyboard():
    return flow.menu_keyboard()


def render_menu_text():
    return flow.menu_text()
