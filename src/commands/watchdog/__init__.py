# commands/watchdog/init.py

from . import on
from . import off
from . import status
from . import set_interval

COMMAND = "watchdog"
CATEGORY = "🐶 Watchdog"
DESCRIPTION = "Monitoreo del sistema"

COMMANDS = [on, off, status, set_interval]

CONVERSATION_COMMANDS = [set_interval]
CONVERSATIONS = [set_interval.CONVERSATION]
