Add-Type -AssemblyName System.Windows.Forms

Write-Host "Starting HuntEye.exe..."
 = Start-Process -FilePath "dist\HuntEye\HuntEye.exe" -PassThru -NoNewWindow
Start-Sleep -Seconds 8

Write-Host "Sending ENTER (to click Launch Mission)..."
[System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
Start-Sleep -Seconds 10

Write-Host "Sending SPACE (to transition to LIVE loop)..."
[System.Windows.Forms.SendKeys]::SendWait(" ")
Start-Sleep -Seconds 10

Write-Host "Sending Q (to quit)..."
[System.Windows.Forms.SendKeys]::SendWait("q")
Start-Sleep -Seconds 5

if (!.HasExited) {
    Write-Host "Process still running, killing it..."
    Stop-Process -Id .Id -Force
} else {
    Write-Host "Process exited cleanly."
}

Write-Host "Test complete. Checking for crash_log.txt..."
if (Test-Path "dist\HuntEye\crash_log.txt") {
    Write-Host "CRASH DETECTED!"
    Get-Content "dist\HuntEye\crash_log.txt"
} else {
    Write-Host "No crash log found. Success!"
}
