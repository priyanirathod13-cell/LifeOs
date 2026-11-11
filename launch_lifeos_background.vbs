Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\LifeOs"
WshShell.Run """C:\LifeOs\.venv\Scripts\pythonw.exe"" ""C:\LifeOs\supervisor.py""", 0, False
