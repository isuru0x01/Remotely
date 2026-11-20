import json
import os
import sys
import time
import urllib.error
import urllib.request

# Safe encoding handling on Windows terminals
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def get_base_dir():
    """Return the directory containing the executable or script."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def load_config():
    """
    Search for config.json in several potential locations:
    1. Path specified by REMOTELY_CONFIG_PATH environment variable
    2. Directory containing the executable/script
    3. Parent directory of the script (e.g., project root)
    4. Current working directory
    """
    candidates = []
    env_config_path = os.environ.get("REMOTELY_CONFIG_PATH")
    if env_config_path:
        candidates.append(env_config_path)

    base_dir = get_base_dir()
    candidates.append(os.path.join(base_dir, "config.json"))
    candidates.append(os.path.join(base_dir, "..", "config.json"))
    candidates.append(os.path.join(os.getcwd(), "config.json"))

    for path in candidates:
        norm_path = os.path.normpath(path)
        if os.path.isfile(norm_path):
            try:
                with open(norm_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(
                    f"[!] Warning: Failed to parse config file at {norm_path}: {e}",
                    file=sys.stderr,
                )
    return {}


def get_topic_url():
    """
    Resolve the topic URL with the following precedence:
    1. REMOTELY_TOPIC_URL environment variable
    2. NTFY_TOPIC_URL environment variable
    3. 'topic_url' (or 'TOPIC_URL') in config.json
    """
    url = os.environ.get("REMOTELY_TOPIC_URL") or os.environ.get("NTFY_TOPIC_URL")
    if url:
        return url.strip()

    config = load_config()
    url = config.get("topic_url") or config.get("TOPIC_URL")
    if url:
        return url.strip()

    return None


def _send_single_notification(data_bytes, title, target_url, priority, tags=None):
    """Publish a single HTTP POST request to ntfy.sh."""
    headers = {
        "Title": title,
        "Priority": priority,
        "User-Agent": "remotely/1.0",
        "X-Sender": "remotely-agent",
    }
    if tags:
        headers["Tags"] = tags

    req = urllib.request.Request(
        target_url,
        data=data_bytes,
        headers=headers,
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.status == 200
    except urllib.error.URLError as e:
        print(f"[!] Failed to send notification: {e}", file=sys.stderr)
        return False


def send_notification(
    message, title="Notification", topic_url=None, priority="default", tags=None
):
    """
    Send a notification message to the configured ntfy topic.
    Automatically splits long messages (> 3800 bytes) into parts to prevent ntfy 413 (Payload Too Large).

    Args:
        message: String or bytes payload to publish.
        title: Notification header title.
        topic_url: The ntfy topic URL. Defaults to configured topic.
        priority: Notification priority (e.g., 'low', 'default', 'high').
        tags: Optional comma-separated ntfy tags/emojis.

    Returns:
        bool: True if publishing succeeded, False otherwise.
    """
    target_url = topic_url or get_topic_url()
    if not target_url:
        print("[!] Error: No topic URL configured.", file=sys.stderr)
        return False

    if not isinstance(message, str):
        message = str(message)

    raw_bytes = message.encode("utf-8")
    MAX_CHUNK_BYTES = 3800

    # Short message: send directly
    if len(raw_bytes) <= MAX_CHUNK_BYTES:
        return _send_single_notification(
            raw_bytes, title, target_url, priority, tags
        )

    # Long message: split safely by lines
    chunks = []
    lines = message.split("\n")
    current_chunk = []
    current_bytes = 0

    for line in lines:
        line_bytes = len((line + "\n").encode("utf-8"))
        if current_bytes + line_bytes > MAX_CHUNK_BYTES and current_chunk:
            chunks.append("\n".join(current_chunk))
            current_chunk = [line]
            current_bytes = line_bytes
        else:
            current_chunk.append(line)
            current_bytes += line_bytes

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    total_chunks = len(chunks)
    all_ok = True
    for i, chunk in enumerate(chunks, start=1):
        chunk_title = (
            f"{title} (Part {i}/{total_chunks})" if total_chunks > 1 else title
        )
        ok = _send_single_notification(
            chunk.encode("utf-8"), chunk_title, target_url, priority, tags
        )
        if not ok:
            all_ok = False
        time.sleep(0.3)  # brief throttle between chunks

    return all_ok


def notify_boot(topic_url=None, retries=12, delay=5):
    """Send an initial boot/online beacon to the configured ntfy topic."""
    for _ in range(retries):
        if send_notification(
            "i am up",
            title="System Online",
            topic_url=topic_url,
            tags="computer,white_check_mark",
        ):
            return True
        time.sleep(delay)
    return False


def default_message_handler(event):
    """Default callback that prints received messages with timestamp and title."""
    timestamp = time.strftime(
        "%Y-%m-%d %H:%M:%S", time.localtime(event.get("time", time.time()))
    )
    title = event.get("title")
    message = event.get("message", "")
    prefix = f"[{timestamp}]"
    if title:
        prefix += f" {title}:"
    print(f"{prefix} {message}")


def poll_messages(topic_url=None, since="latest"):
    """
    Poll recent messages from the topic without holding an open connection.

    Args:
        topic_url: The ntfy topic URL.
        since: Timestamp, duration (e.g. '10m'), message ID, 'all', or 'latest'.

    Returns:
        A list of message dictionaries.
    """
    target_url = topic_url or get_topic_url()
    if not target_url:
        print("[!] Error: No topic URL configured.", file=sys.stderr)
        return []

    poll_url = f"{target_url.rstrip('/')}/json?poll=1&since={since}"
    req = urllib.request.Request(
        poll_url, headers={"User-Agent": "remotely/1.0"}
    )

    messages = []
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8").strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                    if event.get("event") == "message":
                        messages.append(event)
                except json.JSONDecodeError:
                    continue
    except urllib.error.URLError as e:
        print(f"[!] Polling failed: {e}", file=sys.stderr)
    return messages


def listen_for_messages(topic_url=None, on_message=None, reconnect_delay=5):
    """
    Stream incoming messages continuously from the ntfy topic.

    Args:
        topic_url: The ntfy topic URL. Defaults to configured topic.
        on_message: Callback function invoked with event dict when a message arrives.
        reconnect_delay: Seconds to wait before reconnecting if connection drops.
    """
    target_url = topic_url or get_topic_url()
    if not target_url:
        print("[!] Error: No topic URL configured.", file=sys.stderr)
        return

    handler = on_message or default_message_handler
    last_id = None

    print(f"[+] Subscribing to: {target_url}")
    while True:
        stream_url = f"{target_url.rstrip('/')}/json"
        if last_id:
            stream_url += f"?since={last_id}"

        req = urllib.request.Request(
            stream_url, headers={"User-Agent": "remotely/1.0"}
        )

        try:
            # Socket timeout of 60s allows detecting dropped connections;
            # ntfy sends keepalive pulses every ~45s.
            with urllib.request.urlopen(req, timeout=60) as response:
                print("[+] Connection established, listening for messages...")
                for raw_line in response:
                    line = raw_line.decode("utf-8").strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    event_type = event.get("event")
                    if event_type == "message":
                        last_id = event.get("id")
                        handler(event)
                    elif event_type == "open":
                        pass
                    elif event_type == "keepalive":
                        pass

        except (urllib.error.URLError, TimeoutError, OSError) as e:
            print(
                f"[!] Connection interrupted ({e}). Reconnecting in {reconnect_delay}s...",
                file=sys.stderr,
            )
            time.sleep(reconnect_delay)


if __name__ == "__main__":
    notify_boot()
    try:
        listen_for_messages()
    except KeyboardInterrupt:
        print("\n[*] Stopped.")
