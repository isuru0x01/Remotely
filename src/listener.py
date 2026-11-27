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

# Ensure current directory is in sys.path for direct script execution
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from connector import (
    get_computer_id,
    get_topic_url,
    listen_for_messages,
    send_notification,
)

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
SELECTED_MODEL = None


def get_running_models(host=OLLAMA_HOST):
    """
    Check for models actively loaded and running in memory on Ollama (/api/ps).

    Returns:
        list[str]: Names of currently running models in memory.
    """
    try:
        req = urllib.request.Request(
            f"{host}/api/ps", headers={"User-Agent": "remotely/1.0"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return [
                m.get("name") or m.get("model") for m in data.get("models", [])
            ]
    except Exception as e:
        print(f"[!] Warning: Querying {host}/api/ps failed: {e}", file=sys.stderr)
        return []


def get_available_models(host=OLLAMA_HOST):
    """
    Get all installed/available models from Ollama (/api/tags).

    Returns:
        list[str]: Names of installed models.
    """
    try:
        req = urllib.request.Request(
            f"{host}/api/tags", headers={"User-Agent": "remotely/1.0"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return [
                m.get("name") or m.get("model") for m in data.get("models", [])
            ]
    except Exception as e:
        print(
            f"[!] Warning: Querying {host}/api/tags failed: {e}", file=sys.stderr
        )
        return []


def pull_model(model_name, host=OLLAMA_HOST):
    """
    Pull a new model from the Ollama library/registry.
    Streams progress so network reads do not time out during download.

    Returns:
        tuple (success: bool, message: str)
    """
    payload = json.dumps({"name": model_name, "stream": True}).encode("utf-8")
    req = urllib.request.Request(
        f"{host}/api/pull",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "remotely/1.0",
        },
    )

    last_status = None
    try:
        # Timeout per read chunk (streaming lines)
        with urllib.request.urlopen(req, timeout=120) as resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8").strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if "error" in data:
                    return False, data["error"]

                status = data.get("status", "")
                if status and status != last_status:
                    last_status = status
                    print(f"[*] Ollama pull [{model_name}]: {status}")

            return True, "Model successfully downloaded from Ollama."
    except Exception as e:
        return False, str(e)


def load_model(model_name, host=OLLAMA_HOST):
    """
    Load a model into memory on Ollama using /api/generate with keep_alive.

    Returns:
        tuple (success: bool, message: str)
    """
    payload = json.dumps(
        {"model": model_name, "keep_alive": "30m"}
    ).encode("utf-8")

    req = urllib.request.Request(
        f"{host}/api/generate",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "remotely/1.0",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            if "error" in result:
                return False, result["error"]
            return True, f"Model '{model_name}' successfully loaded into memory."
    except Exception as e:
        return False, str(e)


def start_model(model_name):
    """
    Select and run a model on Ollama.
    If the model is not found locally, automatically pulls it from the Ollama registry.
    Sets the model as the active SELECTED_MODEL.

    Returns:
        bool: True if started successfully, False otherwise.
    """
    global SELECTED_MODEL
    comp_id = get_computer_id()
    model_name = model_name.strip()
    if not model_name:
        notice = f"Usage: {comp_id}/start_model <model_name>"
        print(f"[!] {notice}")
        send_notification(notice, title=f"[{comp_id}] Model Error")
        return False

    print(f"\n[*] [ID: {comp_id}] /start_model requested for: '{model_name}'")

    available = get_available_models()
    is_installed = any(
        m == model_name
        or m.split(":")[0] == model_name
        or m == f"{model_name}:latest"
        for m in available
    )

    # 1. Pull model if not available locally
    if not is_installed:
        msg = (
            f"Model '{model_name}' not found locally on computer [{comp_id}]. "
            "Pulling from Ollama registry... this may take some time."
        )
        print(f"[*] {msg}")
        send_notification(
            msg, title=f"[{comp_id}] Pulling Model: {model_name}", priority="low"
        )

        success, err = pull_model(model_name)
        if not success:
            fail_msg = f"Failed to pull model '{model_name}': {err}"
            print(f"[!] {fail_msg}")
            send_notification(
                fail_msg, title=f"[{comp_id}] Model Pull Failed", priority="high"
            )
            return False

        print(f"[+] Successfully pulled '{model_name}'.")

    # 2. Warm up / load into memory
    print(f"[*] Loading '{model_name}' into memory...")
    send_notification(
        f"Loading '{model_name}' into memory...",
        title=f"[{comp_id}] Loading Model",
        priority="low",
    )

    loaded, load_err = load_model(model_name)
    if not loaded:
        fail_msg = f"Failed to load model '{model_name}': {load_err}"
        print(f"[!] {fail_msg}")
        send_notification(
            fail_msg, title=f"[{comp_id}] Model Load Failed", priority="high"
        )
        return False

    SELECTED_MODEL = model_name
    success_msg = (
        f"Model '{model_name}' is now active on computer [{comp_id}] and ready for tasks."
    )
    print(f"[✓] {success_msg}\n")
    send_notification(
        success_msg, title=f"[{comp_id}] Active Model: {model_name}", priority="default"
    )
    return True


def send_models_list():
    """
    Format and send the list of available/installed models to ntfy.sh
    when no models are currently running in memory.
    """
    comp_id = get_computer_id()
    available = get_available_models()
    if available:
        model_lines = "\n".join(f"• {m}" for m in available)
        msg = (
            f"Computer [{comp_id}]: No models currently active in memory.\n\n"
            f"Available installed models:\n{model_lines}\n\n"
            f"To select and run a model, send:\n"
            f"{comp_id}/start_model <model_name>"
        )
        print(f"[!] {msg}")
        send_notification(
            msg, title=f"[{comp_id}] No Running Models", priority="default"
        )
    else:
        msg = (
            f"Computer [{comp_id}]: No models running or installed on Ollama ({OLLAMA_HOST}).\n"
            f"To download and run a model, send: {comp_id}/start_model <model_name>"
        )
        print(f"[!] {msg}")
        send_notification(msg, title=f"[{comp_id}] No Models Found", priority="high")
    return available


def redirect_to_model(prompt, model_name, host=OLLAMA_HOST):
    """
    Send prompt to the specified model via Ollama generate API.

    Args:
        prompt: Task instruction or question to send.
        model_name: Target model name.
        host: Base URL of Ollama service.

    Returns:
        str: Model response text or error message.
    """
    payload = json.dumps(
        {"model": model_name, "prompt": prompt, "stream": False}
    ).encode("utf-8")

    req = urllib.request.Request(
        f"{host}/api/generate",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "remotely/1.0",
        },
    )

    try:
        # Generous timeout for local model generation (up to 5 minutes)
        with urllib.request.urlopen(req, timeout=300) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result.get("response", "").strip()
    except TimeoutError:
        return f"[Error: Inference timed out after 300s on model '{model_name}']"
    except Exception as e:
        return f"[Error invoking model '{model_name}': {e}]"


def handle_task(task_text):
    """
    Detect selected or running model and forward the /task prompt to it.
    If no model is currently running or selected, list available models
    and instruct how to start one via /start_model.
    """
    global SELECTED_MODEL
    comp_id = get_computer_id()
    print(f"\n[*] [ID: {comp_id}] Processing /task: {task_text}")

    selected_model = SELECTED_MODEL
    if not selected_model:
        running = get_running_models()
        if running:
            selected_model = running[0]

    if not selected_model:
        print("[!] No models are currently running or selected.")
        send_models_list()
        return

    print(f"[+] Directing to active model: {selected_model}")

    send_notification(
        f"Processing with [{selected_model}] on [{comp_id}]...",
        title=f"[{comp_id}] Task in Progress",
        priority="low",
    )

    # Query the model
    response = redirect_to_model(task_text, selected_model)
    print(f"[+] Response from {selected_model}:\n{response}\n")

    # Send response back to the ntfy topic (chunks automatically if long)
    send_notification(
        response, title=f"[{comp_id}] Task Result ({selected_model})", priority="default"
    )


def is_bot_echo(title):
    """Filter out responses generated by remotely itself to prevent notification loops."""
    if not title:
        return False
    clean_title = title.strip()
    # Strip leading computer ID tag e.g. "[43434343] Task Result" -> "Task Result"
    if clean_title.startswith("[") and "]" in clean_title:
        clean_title = clean_title.split("]", 1)[1].strip()

    bot_titles = (
        "Task Result",
        "Task in Progress",
        "Loading Model",
        "Pulling Model",
        "Active Model",
        "No Running Models",
        "No Models Found",
        "System Online",
        "Running Models",
        "Model Error",
        "Task Error",
        "Model Pull Failed",
        "Model Load Failed",
        "Remotely Online",
    )
    return any(clean_title.startswith(prefix) for prefix in bot_titles)


def parse_targeted_command(raw_text, my_id):
    """
    Check if an incoming message targets this specific computer ID or is a broadcast.

    Supports formats:
      - 43434343/task <instruction>
      - 43434343/start_model <name>
      - 43434343/models
      - 43434343 /task <instruction>
      - 43434343: /task <instruction>
      - all/task <instruction> (broadcast to all)
      - /task <instruction> (broadcast to all)

    Returns:
        tuple (is_for_me: bool, command_text: str)
    """
    text = raw_text.strip()
    if not text:
        return False, ""

    # Pattern 1: {id}/<command> (e.g. "43434343/task Hello")
    if "/" in text:
        prefix, rest = text.split("/", 1)
        prefix = prefix.strip().rstrip(":")
        rest = "/" + rest.strip()
        if prefix.lower() == "all" or prefix == my_id:
            return True, rest
        elif prefix.isalnum() and len(prefix) >= 4:
            # Explicitly addressed to another computer ID
            return False, ""

    # Pattern 2: {id} <command> (e.g. "43434343 /task Hello" or "43434343 task Hello")
    parts = text.split(None, 1)
    if len(parts) >= 2:
        prefix = parts[0].strip().rstrip(":")
        rest = parts[1].strip()
        if not rest.startswith("/"):
            rest = "/" + rest

        if prefix.lower() == "all" or prefix == my_id:
            return True, rest
        elif prefix.isalnum() and len(prefix) >= 4:
            # Explicitly addressed to another computer ID
            return False, ""

    # Pattern 3: Direct command without prefix (e.g. "/task Hello")
    if text.startswith("/"):
        return True, text

    return False, text


def message_handler(event):
    """
    Handle incoming ntfy events:
    - Filters out bot responses.
    - Matches computer ID prefix (e.g. 43434343/task ...)
    - Dispatches '/start_model', '/task', and '/models' commands.
    """
    title = event.get("title") or ""
    if is_bot_echo(title):
        return

    raw_message = event.get("message", "").strip()
    my_id = get_computer_id()

    is_for_me, command = parse_targeted_command(raw_message, my_id)
    if not is_for_me:
        # Message was targeted to another computer, quietly ignore
        return

    timestamp = time.strftime(
        "%Y-%m-%d %H:%M:%S", time.localtime(event.get("time", time.time()))
    )

    print(f"[{timestamp}] [Computer ID: {my_id}] Received command: {command!r}")

    if command.startswith("/start_model"):
        model_name = command[len("/start_model") :].strip()
        start_model(model_name)

    elif command.startswith("/task"):
        task_prompt = command[len("/task") :].strip()
        if not task_prompt:
            notice = f"Empty task prompt. Usage: {my_id}/task <your instruction>"
            print(f"[!] {notice}")
            send_notification(notice, title=f"[{my_id}] Task Error")
            return

        handle_task(task_prompt)

    elif command.startswith(("/models", "/list")):
        running = get_running_models()
        active_prefix = (
            f"Active Model: {SELECTED_MODEL}\n\n" if SELECTED_MODEL else ""
        )
        if running:
            running_lines = "\n".join(f"• {m}" for m in running)
            send_notification(
                f"Computer [{my_id}]\n\n{active_prefix}Currently running in memory:\n{running_lines}",
                title=f"[{my_id}] Running Models",
            )
        else:
            send_models_list()


def main():
    topic_url = get_topic_url()
    comp_id = get_computer_id()

    print("=" * 60)
    print(" Remotely - Message & Task Listener")
    print("=" * 60)
    print(f"[+] Computer ID: {comp_id}")
    print(f"[+] Topic URL  : {topic_url}")
    print(f"[+] Ollama Host: {OLLAMA_HOST}")

    # Announce this computer's online status and ID to ntfy.sh
    send_notification(
        f"Computer ID: {comp_id} is online and listening.\n\n"
        f"Commands for this machine:\n"
        f"• {comp_id}/task <prompt>\n"
        f"• {comp_id}/start_model <model_name>\n"
        f"• {comp_id}/models",
        title=f"System Online [{comp_id}]",
        tags="computer,satellite",
    )

    running = get_running_models()
    if running:
        print(f"[+] Running in memory: {', '.join(running)}")
    else:
        print("[!] No models currently running in memory.")
        available = get_available_models()
        if available:
            print(f"[+] Available installed models: {', '.join(available)}")
        send_models_list()

    print(f"[*] Listening for messages targeted to [{comp_id}] or broadcast... (Press Ctrl+C to exit)\n")

    try:
        listen_for_messages(on_message=message_handler)
    except KeyboardInterrupt:
        print("\n[*] Listener stopped by user.")


if __name__ == "__main__":
    main()
