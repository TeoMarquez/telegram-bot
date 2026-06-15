from functools import wraps

from config import AUTHORIZED_USER


def authorized_only(func):

    @wraps(func)
    async def wrapper(update, context):

        if update.effective_user.id != AUTHORIZED_USER:
            return

        return await func(update, context)

    return wrapper