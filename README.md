# Remotely

A lightweight, zero-dependency remote management beacon and local AI task agent. **Remotely** connects your machine to a private [ntfy.sh](https://ntfy.sh) topic to broadcast boot/online status beacons and remotely execute tasks via local LLMs using [Ollama](https://ollama.com).

---

## Features

- **Boot & Online Beacon**: Sends a silent "System Online" heartbeat upon system boot with automatic retry backoff.
- **Remote AI Task Execution (`/task`)**: Streams incoming instructions from `ntfy.sh` and routes them to active models on Ollama.
- **Model Management & Auto-Pull (`/start_model`)**: Remotely load models into memory or automatically pull new models from the [Ollama Library](https://ollama.com/library).
- **Auto-Discovery & Fallback**: Lists available installed models when no models are actively loaded in memory.
- **Unified CLI (`remotely`)**: Complete command-line interface with `-h`/`--help` support for sending messages, polling topics, checking model status, and running the listener.
- **Zero External Python Dependencies**: Built entirely with standard Python libraries (`urllib`, `json`, `argparse`).
- **Production-Ready Windows Packaging**:
  - Standalone `.exe` cross-compilation from Linux via Docker/Wine.
  - Native Windows batch builds via PyInstaller.
  - Automated silent background execution on Windows startup (`pythonw.exe` / VBScript).

---

## Architecture

```mermaid
flowchart LR
    User[User / Mobile / Browser] <-->|Push Notifications| Ntfy["ntfy.sh (Private Topic)"]
    Ntfy <-->|Stream / Poll| Remotely["Remotely Listener (src/listener.py or remotely.exe)"]
    Remotely <-->|REST API (:11434)| Ollama["Local Ollama Service"]
```

---

## Project Structure

```text
remotely/
├── src/
│   ├── connector.py               # Core networking (publish, stream, poll, beacon)
│   ├── listener.py                # Message stream listener & Ollama model router
│   └── remotely.py                # Unified CLI entrypoint
├── scripts/
│   ├── build.py                   # Automated cross-platform PyInstaller compiler
│   ├── build.bat                  # Native Windows build script
│   ├── build_docker.sh            # Linux Docker cross-compilation script (Wine)
│   └── windows/
│       ├── run_remotely.vbs       # Silent background launcher (no CMD window)
│       └── install_startup.bat    # 1-click Windows Task Scheduler installer
├── Dockerfile                     # Docker builder image definition
├── config.example.json            # Configuration template
├── config.json                    # Local secret configuration (ignored by git)
├── README.md                      # Documentation
└── .gitignore                     # Git ignore rules
```

---

## Configuration

Remotely resolves its target ntfy topic and settings using the following precedence:

1. **Environment Variables**:
   - `REMOTELY_TOPIC_URL` or `NTFY_TOPIC_URL`: Target ntfy topic URL.
   - `OLLAMA_HOST`: Base URL for Ollama (defaults to `http://localhost:11434`).
   - `REMOTELY_CONFIG_PATH`: Explicit path to a configuration file.
2. **Configuration File (`config.json`)**:
   Create a `config.json` file in the root directory (or next to the `.exe`):
   ```json
   {
     "topic_url": "https://ntfy.sh/your_private_secret_topic_name"
   }
   ```

---

## Usage

### 1. Command-Line Interface (`remotely.py`)

Run the unified CLI directly using Python:

```bash
# View all options and help
python3 src/remotely.py --help

# Start the continuous message & AI task listener
python3 src/remotely.py -l
python3 src/remotely.py listener

# Send system boot notification beacon
python3 src/remotely.py -b
python3 src/remotely.py boot

# Publish a custom notification to ntfy
python3 src/remotely.py send "Deployment complete" --title "Alert" --priority high

# Poll recent messages without persistent streaming
python3 src/remotely.py poll --since 10m

# List active and installed Ollama models
python3 src/remotely.py models

# Select and start an Ollama model (pulls if needed)
python3 src/remotely.py start_model llama3.2
```

---

### 2. Remote Control over ntfy

Once the listener is running, you can publish messages to your ntfy topic from your phone or web browser:

| Command | Action | Example |
| :--- | :--- | :--- |
| `/task <instruction>` | Directs the task to the active model and replies with the result. | `/task Summarize the server error logs` |
| `/start_model <name>` | Loads a model into memory or downloads it from the Ollama library. | `/start_model llama3.2` |
| `/models` or `/list` | Replies with the active model, models in memory, and installed models. | `/models` |

---

## Running on Windows Startup in the Background

### Option A: 1-Click Task Scheduler Installer (Recommended)
Right-click `scripts\windows\install_startup.bat` and select **Run as administrator**. This registers a task with Windows Task Scheduler that starts Remotely silently on user logon.

### Option B: Windows Startup Folder
1. Press <kbd>Win</kbd> + <kbd>R</kbd>, type `shell:startup`, and press <kbd>Enter</kbd>.
2. Copy `scripts\windows\run_remotely.vbs` (or create a shortcut to it) into that folder. It automatically resolves the repository root dynamically and runs `pythonw.exe src\remotely.py -l` with no console window.

---

## Building Standalone Windows Executables (`.exe`)

You can compile standalone single-file `.exe` binaries with no Python runtime required on target machines.

### Option A: From Linux using Docker (Cross-Compilation)

Cross-compiles Windows binaries directly on Linux using Wine:

```bash
./scripts/build_docker.sh
```

### Option B: Native Windows Build

Run the batch script from Command Prompt on a Windows host:

```cmd
scripts\build.bat
```

Compiled executables will be output to the `dist/` directory:
- **`dist/remotely.exe`**: CLI utility with full console and help flag support.
- **`dist/connector.exe`**: Silent background beacon (`--noconsole`).
- **`dist/config.example.json`**: Bundled configuration template.

---

## License

MIT License. See individual script headers for details.
