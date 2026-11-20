Set WshShell = CreateObject("WScript.Shell")
' Replace the path below with your actual project directory
WshShell.CurrentDirectory = "C:\path\to\remotely"
WshShell.Run "pythonw.exe src\listener.py", 0, False