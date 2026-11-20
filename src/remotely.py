#!/usr/bin/env python3
"""
Remotely - Remote Management & AI Task Agent CLI
"""

import argparse
import os
import sys

# Safe encoding handling on Windows terminals
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ensure script directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from connector import (
    get_topic_url,
    notify_boot,
    poll_messages,
    send_notification,
)
from listener import (
    get_available_models,
    get_running_models,
    main as start_listener,
    start_model,
)


def cmd_listener(args):
    """Start the incoming message & task listener."""
    start_listener()


def cmd_boot(args):
    """Send the boot beacon notification."""
    topic_url = get_topic_url()
    retries = getattr(args, "retries", 12)
    delay = getattr(args, "delay", 5)
    print(f"[*] Sending boot notification to: {topic_url}")
    success = notify_boot(topic_url=topic_url, retries=retries, delay=delay)
    if success:
        print("[✓] Boot notification sent successfully.")
    else:
        print("[!] Failed to send boot notification.", file=sys.stderr)
        sys.exit(1)


def cmd_send(args):
    """Publish a notification to the ntfy topic."""
    message = getattr(args, "message", None) or getattr(args, "send", None)
    if not message:
        print("[!] Error: Message text cannot be empty.", file=sys.stderr)
        sys.exit(1)

    title = getattr(args, "title", "Remotely Notification") or "Remotely Notification"
    priority = getattr(args, "priority", "default") or "default"

    print(f"[*] Publishing notification: '{message}' (Title: '{title}')")
    if send_notification(message, title=title, priority=priority):
        print("[✓] Message sent successfully.")
    else:
        print("[!] Failed to send notification.", file=sys.stderr)
        sys.exit(1)


def cmd_poll(args):
    """Poll recent messages from the ntfy topic."""
    since = getattr(args, "since", "10m") or "10m"
    print(f"[*] Polling messages since: {since}")
    messages = poll_messages(since=since)
    if not messages:
        print("[i] No messages received.")
        return

    print(f"[+] Found {len(messages)} message(s):")
    for idx, msg in enumerate(messages, start=1):
        time_str = msg.get("time", "")
        title = msg.get("title", "")
        body = msg.get("message", "")
        prefix = f"  [{idx}]"
        if title:
            prefix += f" {title}:"
        print(f"{prefix} {body}")


def cmd_start_model(args):
    """Select and run an Ollama model, pulling if needed."""
    model_name = getattr(args, "name", None) or getattr(args, "start_model", None)
    if not model_name:
        print("[!] Error: Model name cannot be empty.", file=sys.stderr)
        sys.exit(1)
    if not start_model(model_name):
        sys.exit(1)


def cmd_models(args):
    """Check running and available Ollama models."""
    running = get_running_models()
    available = get_available_models()

    print("=" * 50)
    print(" Ollama Models Status")
    print("=" * 50)

    if running:
        print(f"[+] Active in memory ({len(running)}):")
        for m in running:
            print(f"    • {m}")
    else:
        print("[!] No models actively running in memory.")

    print()
    if available:
        print(f"[+] Available installed models ({len(available)}):")
        for m in available:
            print(f"    • {m}")
    else:
        print("[!] No models installed on Ollama.")
    print("=" * 50)


def build_parser():
    parser = argparse.ArgumentParser(
        prog="remotely",
        description="Remotely - Remote Management & AI Task Agent CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  remotely --help                 Show this help message
  remotely -l                     Run the incoming message & task listener
  remotely listener               Run the incoming message & task listener
  remotely -b                     Send system boot notification beacon
  remotely boot                   Send system boot notification beacon
  remotely -s "Server backup done"  Send a quick notification
  remotely send "Task finished" --title "Status"
  remotely poll --since 1h        Poll messages received in the last hour
  remotely models                 List running and available Ollama models
  remotely start_model llama3.2   Start or pull/run a model
        """,
    )

    parser.add_argument(
        "-v", "--version", action="version", version="remotely 1.0.0"
    )
    parser.add_argument(
        "-c", "--config", help="Path to custom config.json configuration file"
    )
    parser.add_argument(
        "-t", "--topic-url", help="Override the target ntfy topic URL"
    )
    parser.add_argument(
        "--ollama-host",
        help="Override Ollama host URL (default: http://localhost:11434)",
    )

    # Top-level quick action flags
    parser.add_argument(
        "-l",
        "--listener",
        "--listen",
        action="store_true",
        dest="run_listener",
        help="Start the incoming message & AI task listener",
    )
    parser.add_argument(
        "-b",
        "--boot",
        action="store_true",
        dest="run_boot",
        help="Send the system boot/online notification beacon",
    )
    parser.add_argument(
        "-s",
        "--send",
        metavar="MESSAGE",
        help="Send a quick notification message to the ntfy topic",
    )
    parser.add_argument(
        "-p",
        "--poll",
        nargs="?",
        const="10m",
        metavar="SINCE",
        help="Poll recent messages (default: 10m)",
    )
    parser.add_argument(
        "--start-model",
        metavar="MODEL_NAME",
        help="Select and start an Ollama model (pulls from registry if new)",
    )

    # Subcommands
    subparsers = parser.add_subparsers(
        dest="command", title="Commands", metavar="<command>"
    )

    # Subcommand: listener
    sub_listener = subparsers.add_parser(
        "listener",
        aliases=["listen"],
        help="Start the incoming message & AI task listener",
    )
    sub_listener.set_defaults(func=cmd_listener)

    # Subcommand: boot
    sub_boot = subparsers.add_parser(
        "boot", help="Send system boot notification beacon"
    )
    sub_boot.add_argument(
        "--retries", type=int, default=12, help="Number of retries (default: 12)"
    )
    sub_boot.add_argument(
        "--delay",
        type=int,
        default=5,
        help="Delay in seconds between retries (default: 5)",
    )
    sub_boot.set_defaults(func=cmd_boot)

    # Subcommand: send
    sub_send = subparsers.add_parser(
        "send", help="Send a notification message to the ntfy topic"
    )
    sub_send.add_argument("message", help="Message text to send")
    sub_send.add_argument(
        "--title", default="Remotely Notification", help="Notification title"
    )
    sub_send.add_argument(
        "--priority",
        default="default",
        choices=["min", "low", "default", "high", "urgent"],
        help="Notification priority level",
    )
    sub_send.set_defaults(func=cmd_send)

    # Subcommand: poll
    sub_poll = subparsers.add_parser(
        "poll", help="Poll recent messages from the ntfy topic"
    )
    sub_poll.add_argument(
        "--since",
        default="10m",
        help="Fetch messages since duration/timestamp/id (default: '10m', or 'all', '1h')",
    )
    sub_poll.set_defaults(func=cmd_poll)

    # Subcommand: models
    sub_models = subparsers.add_parser(
        "models", help="Check running and available Ollama models"
    )
    sub_models.set_defaults(func=cmd_models)

    # Subcommand: start_model
    sub_start = subparsers.add_parser(
        "start_model",
        aliases=["start-model"],
        help="Select and start an Ollama model (pulls if needed)",
    )
    sub_start.add_argument("name", help="Name of model to start/pull")
    sub_start.set_defaults(func=cmd_start_model)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    # Apply configuration overrides to environment
    if args.config:
        os.environ["REMOTELY_CONFIG_PATH"] = os.path.abspath(args.config)
    if args.topic_url:
        os.environ["REMOTELY_TOPIC_URL"] = args.topic_url
    if args.ollama_host:
        os.environ["OLLAMA_HOST"] = args.ollama_host

    # Handle quick flags
    if args.run_listener:
        cmd_listener(args)
        return
    if args.run_boot:
        cmd_boot(args)
        return
    if args.send:
        cmd_send(args)
        return
    if args.poll:
        args.since = args.poll
        cmd_poll(args)
        return
    if args.start_model:
        cmd_start_model(args)
        return

    # Handle subcommands
    if hasattr(args, "func"):
        args.func(args)
    else:
        # No arguments provided, show help
        parser.print_help()


if __name__ == "__main__":
    main()
