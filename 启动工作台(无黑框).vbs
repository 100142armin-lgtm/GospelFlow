Set ws = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
ws.CurrentDirectory = scriptDir
serverPath = scriptDir & "\server.py"

' 优先使用 pythonw 启动，实现 100% 后台静默无控制台黑框
On Error Resume Next
ws.Run "pythonw """ & serverPath & """", 0, False
If Err.Number <> 0 Then
    ' 备用方案：尝试 pyw
    Err.Clear
    ws.Run "pyw """ & serverPath & """", 0, False
End If
If Err.Number <> 0 Then
    ' 若无 pythonw，回退到普通 python
    Err.Clear
    ws.Run "python """ & serverPath & """", 0, False
End If
