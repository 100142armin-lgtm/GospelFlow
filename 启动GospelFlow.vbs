Set ws = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
ws.CurrentDirectory = scriptDir

exePath = scriptDir & "\GospelFlow.exe"
serverPath = scriptDir & "\server.py"

' 若存在原生 EXE 则优先运行 EXE，否则使用 pythonw 静默启动
If fso.FileExists(exePath) Then
    ws.Run """" & exePath & """", 0, False
Else
    ws.Run "pythonw """ & serverPath & """", 0, False
End If
