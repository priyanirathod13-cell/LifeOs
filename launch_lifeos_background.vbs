Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\LifeOs"
WshShell.Run "cmd.exe /c start_lifeos.bat", 0, False
