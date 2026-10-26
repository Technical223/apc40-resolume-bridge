Option Explicit
Dim fs, shell, folder, app, build, code, ps
Set fs = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
folder = fs.GetParentFolderName(WScript.ScriptFullName)
app = fs.BuildPath(folder, "APC40 Bridge.exe")
If Not fs.FileExists(app) Then
  build = fs.BuildPath(folder, "build-ui.ps1")
  ps = shell.ExpandEnvironmentStrings("%WINDIR%") & "\System32\WindowsPowerShell\v1.0\powershell.exe"
  code = shell.Run(Quote(ps) & " -NoProfile -NonInteractive -ExecutionPolicy Bypass -File " & Quote(build), 0, True)
  If code <> 0 Or Not fs.FileExists(app) Then
    MsgBox "Aplikaci se nepodarilo pripravit. Podrobnosti najdes v navodu.", 48, "APC40 Bridge"
    WScript.Quit 1
  End If
End If
shell.Run Quote(app), 1, False
Function Quote(value)
  Quote = Chr(34) & value & Chr(34)
End Function
