from datetime import datetime

START_TIME = datetime.now()


def get_uptime():

    return str(
        datetime.now() - START_TIME
    ).split(".")[0]