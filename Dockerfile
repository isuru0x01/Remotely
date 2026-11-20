# Dockerfile to build Windows portable .exe binaries on Linux using Wine & PyInstaller
FROM cdrx/pyinstaller-windows:python3

WORKDIR /src

# Sourcing bashrc ensures wine-based python and pyinstaller are in PATH
SHELL ["/bin/bash", "-c"]

# Set default entrypoint to run the multi-file build script
ENTRYPOINT ["/bin/bash", "-c", "python build.py"]

