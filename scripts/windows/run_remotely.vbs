' Windows silent background launcher for Remotely
' Runs without popping up any command prompt window

Set FSO = CreateObject("Scripting.FileSystemObject")
Set WshShell = CreateObject("WScript.Shell")

' Resolve project root dynamically (two levels up from scripts\windows)
ScriptDir = FSO.GetParentFolderName(WScript.ScriptFullName)
ProjectDir = FSO.GetParentFolderName(FSO.GetParentFolderName(ScriptDir))

WshShell.CurrentDirectory = ProjectDir
WshShell.Run "pythonw.exe src\remotely.py -l", 0, False
