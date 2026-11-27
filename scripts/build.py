#!/usr/bin/env python3
"""
Remotely - PyInstaller Build Automation
Defines explicit build targets and compilation settings for standalone Windows binaries.
"""

import argparse
from dataclasses import dataclass
import os
import shutil
import subprocess
import sys
from typing import Dict, List, Optional


@dataclass
class BuildTarget:
    """Explicit build specification for a binary target."""

    name: str
    source_file: str
    output_name: str
    console: bool
    description: str
    default: bool = True

    @property
    def console_flag(self) -> str:
        return "--console" if self.console else "--noconsole"


# Explicitly defined build targets
TARGETS: Dict[str, BuildTarget] = {
    "remotely": BuildTarget(
        name="remotely",
        source_file="remotely.py",
        output_name="remotely",
        console=True,
        description="Unified CLI tool for task listener, notifications, and Ollama models",
        default=True,
    ),
    "connector": BuildTarget(
        name="connector",
        source_file="connector.py",
        output_name="connector",
        console=False,
        description="Silent windowless boot beacon client (runs in background on boot)",
        default=True,
    ),
    "listener": BuildTarget(
        name="listener",
        source_file="listener.py",
        output_name="listener",
        console=True,
        description="Standalone task listener daemon (alternative to remotely.exe listener)",
        default=False,
    ),
}


def clean_artifacts(build_dir: str):
    """Remove intermediate build directories."""
    if os.path.isdir(build_dir):
        print(f"[*] Cleaning build directory: {build_dir}")
        shutil.rmtree(build_dir, ignore_errors=True)


def ensure_pyinstaller():
    """Ensure PyInstaller is installed and available."""
    print("[+] Checking PyInstaller installation...")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "--upgrade", "pyinstaller"]
    )


def compile_target(
    target: BuildTarget,
    src_dir: str,
    dist_dir: str,
    build_dir: str,
):
    """Compile a single explicit build target."""
    source_path = os.path.join(src_dir, target.source_file)
    if not os.path.isfile(source_path):
        print(f"[!] Error: Source file not found: {source_path}", file=sys.stderr)
        return False

    print("\n" + "=" * 60)
    print(f"Target:      {target.name}")
    print(f"Description: {target.description}")
    print(f"Source:      {source_path}")
    print(f"Output:      {dist_dir}/{target.output_name}.exe")
    print(f"Mode:        {target.console_flag} ({'Console Window' if target.console else 'Silent/Windowless'})")
    print("=" * 60)

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        target.console_flag,
        "--name",
        target.output_name,
        "--distpath",
        dist_dir,
        "--workpath",
        os.path.join(build_dir, target.output_name),
        "--specpath",
        os.path.join(build_dir, "specs"),
        source_path,
    ]

    print(f"[+] Executing: {' '.join(cmd)}")
    subprocess.check_call(cmd)
    return True


def list_targets():
    """Display all available build targets."""
    print("=" * 65)
    print(f"{'Target Name':<15} {'Subsystem':<15} {'Default':<10} {'Description'}")
    print("=" * 65)
    for name, t in TARGETS.items():
        subsystem = "Console" if t.console else "Windowless"
        is_default = "Yes" if t.default else "No"
        print(f"{name:<15} {subsystem:<15} {is_default:<10} {t.description}")
    print("=" * 65)


def build_targets(
    selected_names: Optional[List[str]] = None,
    clean: bool = False,
):
    # Resolve directory paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(script_dir)
    src_dir = os.path.join(base_dir, "src")
    dist_dir = os.path.join(base_dir, "dist")
    build_dir = os.path.join(base_dir, "build")

    if clean:
        clean_artifacts(build_dir)

    ensure_pyinstaller()

    # Determine which targets to build
    if selected_names:
        targets_to_build = []
        for name in selected_names:
            if name in TARGETS:
                targets_to_build.append(TARGETS[name])
            else:
                print(f"[!] Unknown target: '{name}'. Run with --list to view valid targets.", file=sys.stderr)
                sys.exit(1)
    else:
        # Default targets
        targets_to_build = [t for t in TARGETS.values() if t.default]

    print(f"\n[+] Building {len(targets_to_build)} target(s): {', '.join(t.name for t in targets_to_build)}")

    os.makedirs(dist_dir, exist_ok=True)
    os.makedirs(build_dir, exist_ok=True)

    for target in targets_to_build:
        compile_target(target, src_dir, dist_dir, build_dir)

    # Copy config.example.json alongside compiled binaries
    example_cfg = os.path.join(base_dir, "config.example.json")
    if os.path.isfile(example_cfg):
        shutil.copy2(example_cfg, os.path.join(dist_dir, "config.example.json"))
        print(f"\n[+] Copied config.example.json -> {dist_dir}/")

    print("\n" + "=" * 60)
    print(f"[OK] All selected targets compiled successfully into:\n     {dist_dir}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Remotely - PyInstaller Build Automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-t",
        "--target",
        dest="targets",
        action="append",
        choices=list(TARGETS.keys()),
        help="Specify target(s) to compile (can be passed multiple times)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Compile all defined targets (including non-default ones)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all defined build targets and their specifications",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean intermediate build/ directory before compiling",
    )
    parser.add_argument(
        "--clean-only",
        action="store_true",
        help="Clean intermediate build/ directory and exit without compiling",
    )

    args = parser.parse_args()

    if args.list:
        list_targets()
        return

    if args.clean_only:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        base_dir = os.path.dirname(script_dir)
        clean_artifacts(os.path.join(base_dir, "build"))
        print("[✓] Build directory cleaned.")
        return

    if args.all:
        selected = list(TARGETS.keys())
    elif args.targets:
        selected = args.targets
    else:
        selected = None  # Use defaults

    build_targets(selected_names=selected, clean=args.clean)


if __name__ == "__main__":
    main()
