import subprocess
import time

def wait_for_internet():
    while True:
        try:
            subprocess.check_output(
                "ping -n 1 8.8.8.8" if is_windows() else "ping -c 1 8.8.8.8",
                shell=True
            )
            return

        except Exception:
            time.sleep(5)


def is_windows():
    import platform
    return platform.system() == "Windows"


def get_public_ip():
    return subprocess.check_output(
        "curl -s ifconfig.me",
        shell=True
    ).decode().strip()