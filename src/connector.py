import time
import urllib.error
import urllib.request

# Choose a complex, unguessable topic name (acts as a shared secret)
TOPIC_URL = "https://ntfy.sh/win_32_server_management_1212_3453"


def notify_boot(retries=12, delay=5):
    req = urllib.request.Request(
        TOPIC_URL,
        data=b"i am up",
        headers={"Title": "System Online", "Priority": "default"},
    )
    for _ in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    return True
        except urllib.error.URLError:
            time.sleep(delay)
    return False


if __name__ == "__main__":
    notify_boot()