# src/commands/nginx/__init__.py
from . import list_subs, add, remove, domain, reload_cmd

COMMAND = "nginx"
CATEGORY = "⚙️ Nginx"
DESCRIPTION = "Administración de proxy inverso"

COMMANDS = [list_subs, add, remove, domain, reload_cmd]
CONVERSATIONS = [add.CONVERSATION, remove.CONVERSATION, domain.CONVERSATION]
CONVERSATION_COMMANDS = [add, remove, domain]