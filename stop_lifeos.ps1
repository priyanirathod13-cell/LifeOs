# Stop LifeOS Server and Supervisor cleanly

# 1. Stop supervisor via PID file if present
if (Test-Path "$PSScriptRoot\supervisor.pid") {
    $spid = Get-Content "$PSScriptRoot\supervisor.pid" -ErrorAction SilentlyContinue
    if ($spid) {
        Stop-Process -Id $spid -Force -ErrorAction SilentlyContinue
    }
    Remove-Item -Path "$PSScriptRoot\supervisor.pid" -Force -ErrorAction SilentlyContinue
}

# 2. Stop any python process running supervisor.py or serve.py
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like '*supervisor.py*' -or $_.CommandLine -like '*serve.py*'
} | ForEach-Object {
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
}

# 3. Stop any process listening on port 8000
try {
    $conns = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
    foreach ($conn in $conns) {
        if ($conn.OwningProcess -gt 0) {
            Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
        }
    }
} catch {
}
