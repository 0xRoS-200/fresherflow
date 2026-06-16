Set WshShell = CreateObject("WScript.Shell")
strPath = CreateObject("Scripting.FileSystemObject").GetParentFolderName(Wscript.ScriptFullName)
WshShell.Run Chr(34) & strPath & "\run.bat" & Chr(34), 0, False
Set WshShell = Nothing
