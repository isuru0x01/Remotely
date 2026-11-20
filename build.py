import glob
import os
import shutil
import subprocess
import sys


def build():
    # Install or verify PyInstaller
    print("[+] Ensuring PyInstaller is installed...")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "--upgrade", "pyinstaller"]
    )

    base_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.join(base_dir, "src")
    dist_dir = os.path.join(base_dir, "dist")
    build_dir = os.path.join(base_dir, "build")

    # Find all top-level .py files in src/ (ignoring __init__.py and private files starting with _ or .)
    py_files = [
        f
        for f in glob.glob(os.path.join(src_dir, "*.py"))
        if not os.path.basename(f).startswith(("_", "."))
    ]

    if not py_files:
        print(f"[!] No eligible Python files found in {src_dir} to compile.")
        return

    print(f"[+] Found {len(py_files)} script(s) in {src_dir}:")
    for f in py_files:
        print(f"    - {os.path.basename(f)}")

    for file_path in py_files:
        stem = os.path.splitext(os.path.basename(file_path))[0]

        # Background daemon (connector) runs windowless (--noconsole).
        # CLI tools (remotely, listener) require console output (--console).
        is_daemon = stem in ["connector"]
        console_flag = "--noconsole" if is_daemon else "--console"

        print(
            f"\n[+] Compiling: {file_path} -> dist/{stem}.exe ({console_flag}) ..."
        )

        cmd = [
            sys.executable,
            "-m",
            "PyInstaller",
            "--onefile",
            console_flag,
            "--name",
            stem,
            "--distpath",
            dist_dir,
            "--workpath",
            os.path.join(build_dir, stem),
            "--specpath",
            os.path.join(build_dir, "specs"),
            file_path,
        ]
        print(f"    Executing: {' '.join(cmd)}")
        subprocess.check_call(cmd)

    # Copy config.example.json into dist/ alongside executables
    example_cfg = os.path.join(base_dir, "config.example.json")
    if os.path.isfile(example_cfg):
        shutil.copy2(example_cfg, os.path.join(dist_dir, "config.example.json"))
        print(f"\n[+] Copied config.example.json -> {dist_dir}/")

    print("\n" + "=" * 60)
    print(
        f"[OK] All builds complete! Portable executables located in:\n    {dist_dir}"
    )
    print("=" * 60)


if __name__ == "__main__":
    build()
