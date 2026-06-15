# state/heartbeat.py

import time

_LAST_TICK = time.time()

def tick():
    global _LAST_TICK
    _LAST_TICK = time.time()

def last_tick():
    return _LAST_TICK

def is_alive(timeout=120):
    return (time.time() - _LAST_TICK) <= timeout