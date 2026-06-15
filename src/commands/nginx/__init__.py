# src/commands/nginx/__init__.py
from . import list_subs, add, remove, domain, reload_cmd, ssl_cmd, ssl_wizard

COMMAND = "nginx"
CATEGORY = "⚙️ Nginx"
DESCRIPTION = "Administración de proxy inverso"

COMMANDS = [list_subs, add, remove, domain, reload_cmd, ssl_wizard]
CONVERSATIONS = [add.CONVERSATION, remove.CONVERSATION, domain.CONVERSATION, ssl_wizard.CONVERSATION]
CONVERSATION_COMMANDS = [add, remove, domain, ssl_wizard]
EXTRA_HANDLERS = [ssl_cmd.CALLBACK_HANDLER]