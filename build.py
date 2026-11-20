import glob
import os
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
        print(f"\n[+] Compiling: {file_path} -> dist/{stem}.exe ...")

        cmd = [
            sys.executable,
            "-m",
            "PyInstaller",
            "--onefile",
            "--noconsole",
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

    print("\n" + "=" * 60)
    print(f"[OK] All builds complete! Portable executables located in:\n    {dist_dir}")
    print("=" * 60)


if __name__ == "__main__":
    build()
