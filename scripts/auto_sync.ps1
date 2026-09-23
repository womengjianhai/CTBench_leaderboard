param(
    [ValidateSet('Install', 'Status', 'Pause', 'Resume', 'Uninstall')]
    [string]$Action = 'Status'
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$stateDir = Join-Path $repoRoot '.git\auto-sync'
$taskName = 'CTBench-Leaderboard-AutoSync'
$workerPath = Join-Path $PSScriptRoot 'auto_sync.py'
New-Item -ItemType Directory -Path $stateDir -Force | Out-Null

switch ($Action) {
    'Install' {
        $pythonPath = (Get-Command pythonw.exe -ErrorAction Stop).Source
        $userId = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
        $taskAction = New-ScheduledTaskAction -Execute $pythonPath -Argument ('"' + $workerPath + '"') -WorkingDirectory $repoRoot
        $trigger = New-ScheduledTaskTrigger -AtLogOn -User $userId
        $principal = New-ScheduledTaskPrincipal -UserId $userId -LogonType Interactive -RunLevel Limited
        $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -MultipleInstances IgnoreNew
        $existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
        if ($existing -and $existing.Actions.Arguments -ne ('"' + $workerPath + '"')) {
            throw 'A sync task with this name belongs to another checkout.'
        }
        Register-ScheduledTask -TaskName $taskName -Action $taskAction -Trigger $trigger -Principal $principal -Settings $settings -Description 'Validate, commit and push CTBench changes after 15 seconds without edits.' -Force | Out-Null
        Start-ScheduledTask -TaskName $taskName
        Write-Output 'Auto-sync installed and started. It also starts at Windows sign-in.'
    }
    'Pause' {
        New-Item -ItemType File -Path (Join-Path $stateDir 'paused') -Force | Out-Null
        Write-Output 'Auto-sync paused. An in-flight push may finish.'
    }
    'Resume' {
        $pauseFile = Join-Path $stateDir 'paused'
        if (Test-Path -LiteralPath $pauseFile) { Remove-Item -LiteralPath $pauseFile }
        Start-ScheduledTask -TaskName $taskName
        Write-Output 'Auto-sync resumed.'
    }
    'Uninstall' {
        Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
        Write-Output 'Auto-sync task removed. Git history and remote are unchanged.'
    }
    'Status' {
        Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue | Select-Object TaskName,State
        $statusFile = Join-Path $stateDir 'status.json'
        if (Test-Path -LiteralPath $statusFile) { Get-Content -LiteralPath $statusFile -Encoding UTF8 }
        $logFile = Join-Path $stateDir 'sync.log'
        if (Test-Path -LiteralPath $logFile) { Get-Content -LiteralPath $logFile -Tail 8 -Encoding UTF8 }
    }
}