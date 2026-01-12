#Requires -Version 5.1
<#
.SYNOPSIS
    Rainbond WSL2 One-Click Installer for Windows
.DESCRIPTION
    Automatically installs WSL2, Ubuntu 22.04, and Rainbond on Windows 10/11
.NOTES
    Requires Administrator privileges
    Supports Windows 10 21H2+ and Windows 11
#>

param(
    [switch]$Debug,
    [switch]$OfflineMode,
    [string]$UbuntuTarPath
)

# Error handling
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# Set console encoding to UTF-8 for proper Chinese display
try {
    # Set code page to UTF-8 first (must be before other encoding settings)
    $null = cmd /c chcp 65001
    # Set PowerShell encodings
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    [Console]::InputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
    # For WSL commands
    $env:WSL_UTF8 = "1"
} catch {
    # Ignore encoding errors, continue with default
}

# Configuration
$script:Config = @{
    MinWindowsBuild     = 19041
    UbuntuDistroName    = "rainbond-ubuntu2204"
    UbuntuRootfsUrl     = "https://pkg.rainbond.com/wsl/ubuntu-jammy-wsl-amd64-ubuntu22.04lts.rootfs.tar.gz"
    RainbondInstallUrl  = "https://get.rainbond.com"
    TempDir             = "$env:TEMP\rainbond-wsl-install"
    WslMsiUrl           = "https://pkg.rainbond.com/wsl/wsl.2.6.3.0.x64.msi"
    WslMinVersion       = [version]"2.6.3.0"
    LogServerUrl        = "https://log.rainbond.com/dindlog"
}

# Global variables for telemetry
$script:UUID = $null
$script:EIP = $null

#region Telemetry Functions

function Get-MachineUUID {
    # Generate unique machine identifier based on system info
    try {
        $systemInfo = Get-CimInstance Win32_OperatingSystem | Select-Object Caption, OSArchitecture, Manufacturer, SerialNumber
        $infoString = $systemInfo | ForEach-Object { $_.Caption + $_.OSArchitecture + $_.Manufacturer + $_.SerialNumber } | Out-String
        $md5Hasher = [System.Security.Cryptography.MD5]::Create()
        $hashBytes = $md5Hasher.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($infoString))
        $script:UUID = [System.BitConverter]::ToString($hashBytes).ToLower() -replace "-", ""
    }
    catch {
        $script:UUID = "unknown"
    }
}

function Get-SystemInfo {
    # Collect system info as a string for message field
    $info = @()
    try {
        $build = (Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion").CurrentBuildNumber
        $info += "build=$build"
    }
    catch {}

    try {
        $wslVersion = Get-WslVersion
        if ($wslVersion) {
            $info += "wsl=$wslVersion"
        }
    }
    catch {}

    try {
        $disk = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'"
        $freeGB = [math]::Round($disk.FreeSpace / 1GB, 1)
        $info += "disk_free=${freeGB}GB"
    }
    catch {}

    return ($info -join ", ")
}

function Send-Telemetry {
    param(
        [string]$Message,
        [switch]$ShowError   # Show error in console if send fails
    )

    try {
        $osName = (Get-WmiObject -Class Win32_OperatingSystem).Name
        $body = @{
            "message" = $Message
            "os_info" = $osName
            "eip"     = if ($script:EIP) { $script:EIP } else { "" }
            "uuid"    = if ($script:UUID) { $script:UUID } else { "" }
        } | ConvertTo-Json

        $params = @{
            Uri         = $script:Config.LogServerUrl
            Method      = "POST"
            ContentType = "application/json; charset=utf-8"
            Body        = $body
            TimeoutSec  = 10
        }
        Invoke-RestMethod @params | Out-Null
    }
    catch {
        if ($ShowError) {
            Write-Host "  [Telemetry] Failed to send: $($_.Exception.Message)" -ForegroundColor Gray
        }
    }
}

function Send-TelemetryError {
    param(
        [string]$Step,           # Which step failed
        [string]$ErrorMessage,   # Error message
        [int]$ExitCode = 0,      # Command exit code
        [string]$CommandOutput,  # Actual command output
        [string]$StackTrace      # Exception stack trace
    )

    # Build message with all details
    $msgParts = @()
    $msgParts += "[ERROR][$Step]"
    $msgParts += $ErrorMessage
    if ($ExitCode -ne 0) {
        $msgParts += "exit=$ExitCode"
    }
    $msgParts += Get-SystemInfo

    # Add command output (truncate if too long)
    if ($CommandOutput) {
        $output = $CommandOutput.Trim()
        if ($output.Length -gt 500) {
            $output = $output.Substring(0, 500) + "..."
        }
        $msgParts += "output: $output"
    }

    $message = $msgParts -join " | "
    Send-Telemetry -Message $message -ShowError
}

#endregion

#region Helper Functions

function Write-Banner {
    $banner = @"

Welcome to Rainbond WSL2 One-Click Installer (PowerShell)

This script will automatically:
  1. Enable WSL2 features and set as default
  2. Install Ubuntu 22.04 as WSL2 distribution
  3. Download and install Docker and Rainbond in WSL

Estimated time: About 10 minutes

"@
    Write-Host $banner -ForegroundColor Cyan
}

function Write-Step {
    param([string]$Step, [string]$Message)
    Write-Host "`n[$Step] $Message" -ForegroundColor Yellow
}

function Write-Success {
    param([string]$Message)
    Write-Host "  $Message [OK]" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "  WARNING: $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "  ERROR: $Message" -ForegroundColor Red
}

function Test-Administrator {
    $currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    return $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Get-WindowsBuild {
    return [int](Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion").CurrentBuildNumber
}

function Test-WslInstalled {
    try {
        $null = Get-Command wsl -ErrorAction Stop
        $result = wsl --status 2>&1
        return $LASTEXITCODE -eq 0
    }
    catch {
        return $false
    }
}

function Test-WslInstallCommandSupported {
    # wsl --install is supported on Windows 10 21H2+ (build 19044+) and Windows 11
    $build = Get-WindowsBuild
    return $build -ge 19044
}

function Get-UbuntuDistroName {
    # Try to find installed Ubuntu distribution
    $distros = @("rainbond-ubuntu2204", "Ubuntu", "Ubuntu-20.04", "Ubuntu-24.04")

    foreach ($distro in $distros) {
        $result = wsl -d $distro -- echo "test" 2>&1
        if ($LASTEXITCODE -eq 0) {
            return $distro
        }
    }
    return $null
}

function Test-UbuntuInstalled {
    # Check if Ubuntu directory exists (more reliable than parsing wsl -l output)
    $ubuntuPath = "$env:USERPROFILE\WSL\rainbond-ubuntu2204"
    if (Test-Path "$ubuntuPath\ext4.vhdx") {
        return $true
    }

    # Also check via wsl command using cmd to avoid Unicode issues
    try {
        $result = cmd /c "wsl -d rainbond-ubuntu2204 -- echo ok" 2>&1
        if ($result -match "ok") {
            return $true
        }
    }
    catch {}

    return $false
}

function Test-SystemdRunning {
    param([string]$Distro)
    $result = wsl -d $Distro -- bash -c "ps -p 1 -o comm= 2>/dev/null" 2>&1
    return $result -match "systemd"
}

function Invoke-WithRetry {
    param(
        [scriptblock]$ScriptBlock,
        [int]$MaxAttempts = 3,
        [int]$DelaySeconds = 5
    )

    for ($i = 1; $i -le $MaxAttempts; $i++) {
        try {
            return & $ScriptBlock
        }
        catch {
            if ($i -eq $MaxAttempts) { throw }
            Write-Host "  Attempt $i failed, retrying in $DelaySeconds seconds..." -ForegroundColor Yellow
            Start-Sleep -Seconds $DelaySeconds
        }
    }
}

function Request-Reboot {
    param([string]$Reason)

    Write-Host "`n========================================================================" -ForegroundColor Yellow
    Write-Host "  IMPORTANT: System restart required" -ForegroundColor Yellow
    Write-Host "========================================================================" -ForegroundColor Yellow
    Write-Host "`n  $Reason"
    Write-Host "  After restart, please run this script again.`n"

    $response = Read-Host "Restart now? (Y/N)"
    if ($response -eq 'Y' -or $response -eq 'y') {
        Restart-Computer -Force
    }
    exit 0
}

#endregion

#region Installation Functions

function Install-WslViaCommand {
    Write-Host "  Installing WSL2 via 'wsl --install' command..."
    Write-Host "  This may take several minutes, please wait...`n" -ForegroundColor Cyan

    # Use wsl --install directly so output is visible to user
    & wsl --install -d rainbond-ubuntu2204 --no-launch 2>&1 | ForEach-Object {
        Write-Host "  $_"
    }

    $exitCode = $LASTEXITCODE

    if ($exitCode -eq 0) {
        Write-Success "WSL2 and rainbond-ubuntu2204 installation initiated"
        return $true
    }

    # Check if reboot is needed (exit code 3010)
    if ($exitCode -eq 3010) {
        Write-Success "WSL2 installed, reboot required"
        return "reboot"
    }

    Write-Host "  wsl --install exited with code: $exitCode" -ForegroundColor Yellow
    return $false
}

function Ensure-VirtualizationEnabled {
    # Check and enable virtualization features required for WSL2
    Write-Host "  Checking virtualization features..."
    $needReboot = $false

    # Check WSL feature
    $wslFeature = Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux -ErrorAction SilentlyContinue
    if ($wslFeature.State -ne "Enabled") {
        Write-Host "  Enabling Windows Subsystem for Linux..."
        $result = dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart 2>&1
        if ($LASTEXITCODE -in @(0, 3010)) {
            Write-Success "WSL feature enabled"
            $needReboot = $true
        }
    }
    else {
        Write-Success "WSL feature already enabled"
    }

    # Check Virtual Machine Platform
    $vmFeature = Get-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform -ErrorAction SilentlyContinue
    if ($vmFeature.State -ne "Enabled") {
        Write-Host "  Enabling Virtual Machine Platform..."
        $result = dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart 2>&1
        if ($LASTEXITCODE -in @(0, 3010)) {
            Write-Success "Virtual Machine Platform enabled"
            $needReboot = $true
        }
    }
    else {
        Write-Success "Virtual Machine Platform already enabled"
    }

    if ($needReboot) {
        Request-Reboot -Reason "Virtualization features have been enabled and require a system restart."
    }
}

function Install-WslLegacy {
    Write-Host "  Using legacy installation method..."

    # Step 1: Enable WSL feature
    Write-Host "  Enabling Windows Subsystem for Linux..."
    $result = dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart 2>&1
    if ($LASTEXITCODE -notin @(0, 3010)) {
        Write-Warning "WSL feature may already be enabled (exit code: $LASTEXITCODE)"
    }
    else {
        Write-Success "WSL feature enabled"
    }

    # Step 2: Enable Virtual Machine Platform
    Write-Host "  Enabling Virtual Machine Platform..."
    $result = dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart 2>&1
    if ($LASTEXITCODE -notin @(0, 3010)) {
        Write-Warning "Virtual Machine Platform may already be enabled (exit code: $LASTEXITCODE)"
    }
    else {
        Write-Success "Virtual Machine Platform enabled"
    }

    # Step 3: Download and install WSL2 kernel
    Write-Host "  Downloading WSL2 kernel update (~15MB)..."
    $kernelUrl = "https://wslstorestorage.blob.core.windows.net/wslblob/wsl_update_x64.msi"
    $kernelPath = Join-Path $script:Config.TempDir "wsl_update_x64.msi"

    New-Item -ItemType Directory -Path $script:Config.TempDir -Force | Out-Null

    Invoke-WithRetry {
        try {
            Import-Module BitsTransfer -ErrorAction Stop
            Start-BitsTransfer -Source $kernelUrl -Destination $kernelPath -DisplayName "Downloading WSL2 Kernel"
        }
        catch {
            $ProgressPreference = 'Continue'
            Invoke-WebRequest -Uri $kernelUrl -OutFile $kernelPath -UseBasicParsing
        }
    }
    Write-Success "WSL2 kernel downloaded"

    Write-Host "  Installing WSL2 kernel update..."
    $process = Start-Process -FilePath "msiexec" -ArgumentList "/i", "`"$kernelPath`"", "/quiet", "/norestart" -Wait -PassThru
    if ($process.ExitCode -eq 0) {
        Write-Success "WSL2 kernel installed"
    }
    else {
        Write-Warning "Kernel installation returned code $($process.ExitCode)"
    }

    # Step 4: Set WSL2 as default
    Write-Host "  Setting WSL2 as default version..."
    wsl --set-default-version 2 2>&1 | Out-Null
    Write-Success "WSL2 set as default"

    return "reboot"
}

function Install-Wsl2Kernel {
    Write-Host "  Installing WSL2 kernel update..."

    $kernelUrl = "https://wslstorestorage.blob.core.windows.net/wslblob/wsl_update_x64.msi"
    $kernelPath = Join-Path $script:Config.TempDir "wsl_update_x64.msi"

    New-Item -ItemType Directory -Path $script:Config.TempDir -Force | Out-Null

    # Download kernel if not exists
    if (-not (Test-Path $kernelPath)) {
        Write-Host "  Downloading WSL2 kernel (~15MB)..."
        Write-Host ""
        $curlPath = Get-Command curl.exe -ErrorAction SilentlyContinue
        if ($curlPath) {
            Write-Host "  " -NoNewline
            & curl.exe -L -# -o $kernelPath $kernelUrl
        }
        else {
            try {
                Import-Module BitsTransfer -ErrorAction Stop
                Start-BitsTransfer -Source $kernelUrl -Destination $kernelPath -DisplayName "WSL2 Kernel"
            }
            catch {
                $ProgressPreference = 'Continue'
                Invoke-WebRequest -Uri $kernelUrl -OutFile $kernelPath -UseBasicParsing
            }
        }
        Write-Host ""
        Write-Success "WSL2 kernel downloaded"
    }

    # Install kernel
    Write-Host "  Installing kernel update package..."
    $process = Start-Process -FilePath "msiexec" -ArgumentList "/i", "`"$kernelPath`"", "/quiet", "/norestart" -Wait -PassThru

    if ($process.ExitCode -eq 0) {
        Write-Success "WSL2 kernel installed"
    }
    else {
        Write-Warning "Kernel installation returned code $($process.ExitCode), continuing..."
    }

    # Set WSL2 as default
    wsl --set-default-version 2 2>&1 | Out-Null
}

function Get-WslVersion {
    # Get WSL version by reading wsl.exe file version from Program Files
    # (System32\wsl.exe is just a Windows wrapper, not the real WSL)
    try {
        # Check Program Files\WSL first (where MSI installs)
        $wslPath = "$env:ProgramFiles\WSL\wsl.exe"

        if (Test-Path $wslPath) {
            $fileVersion = (Get-Item $wslPath).VersionInfo.FileVersion
            if ($fileVersion -match "(\d+\.\d+\.\d+\.\d+)") {
                return [version]$Matches[1]
            }
        }
    }
    catch {
        # Error getting version
    }

    return $null
}

function Install-WslMsi {
    Write-Host "  Downloading WSL $($script:Config.WslMinVersion)..."
    Write-Host "  URL: $($script:Config.WslMsiUrl)" -ForegroundColor Gray
    Write-Host ""

    $msiPath = Join-Path $script:Config.TempDir "wsl.msi"
    New-Item -ItemType Directory -Path $script:Config.TempDir -Force | Out-Null

    # Download MSI using curl (shows progress)
    try {
        # Use curl.exe (built into Windows 10/11) for progress display
        $curlPath = Get-Command curl.exe -ErrorAction SilentlyContinue
        if ($curlPath) {
            Write-Host "  " -NoNewline
            & curl.exe -L -# -o $msiPath $script:Config.WslMsiUrl
            if ($LASTEXITCODE -ne 0) {
                throw "curl download failed with exit code $LASTEXITCODE"
            }
        }
        else {
            # Fallback to BITS
            Import-Module BitsTransfer -ErrorAction Stop
            Start-BitsTransfer -Source $script:Config.WslMsiUrl -Destination $msiPath -DisplayName "Downloading WSL"
        }
    }
    catch {
        Write-Host "  curl/BITS not available, using alternative download..."
        Write-Host "  This may take a few minutes with no progress display..." -ForegroundColor Yellow
        $ProgressPreference = 'Continue'
        try {
            Invoke-WebRequest -Uri $script:Config.WslMsiUrl -OutFile $msiPath -UseBasicParsing -TimeoutSec 300
        }
        catch {
            Write-Host ""
            Write-Host "  Download failed: $($_.Exception.Message)" -ForegroundColor Red
            Write-Host ""
            Write-Host "  Please manually download WSL from:" -ForegroundColor Yellow
            Write-Host "  https://github.com/microsoft/WSL/releases/latest" -ForegroundColor Cyan
            Write-Host ""
            Write-Host "  Or ensure the file exists at:" -ForegroundColor Yellow
            Write-Host "  $($script:Config.WslMsiUrl)" -ForegroundColor Cyan
            Write-Host ""
            Send-TelemetryError -Step "wsl_download" `
                -ErrorMessage "Failed to download WSL MSI" `
                -CommandOutput "URL: $($script:Config.WslMsiUrl)`nError: $($_.Exception.Message)"
            throw "Failed to download WSL: $($_.Exception.Message)"
        }
    }

    Write-Host ""
    Write-Success "WSL MSI downloaded"

    # Install MSI silently
    Write-Host "  Installing WSL (this may take a minute)..."
    $process = Start-Process -FilePath "msiexec" -ArgumentList "/i", "`"$msiPath`"", "/quiet", "/norestart" -Wait -PassThru

    if ($process.ExitCode -eq 0) {
        Write-Success "WSL installed successfully"
        return $true
    }
    elseif ($process.ExitCode -eq 3010) {
        Write-Success "WSL installed (reboot may be required)"
        return $true
    }
    else {
        Send-TelemetryError -Step "wsl_install" `
            -ErrorMessage "WSL MSI installation failed" `
            -ExitCode $process.ExitCode `
            -CommandOutput "msiexec /i wsl.msi returned code $($process.ExitCode)"
        Write-Warning "WSL installation returned code $($process.ExitCode)"
        return $false
    }
}

function Ensure-WslVersion {
    Write-Step "0/4" "Checking WSL version..."

    $currentVersion = Get-WslVersion
    $requiredVersion = $script:Config.WslMinVersion

    if ($null -eq $currentVersion) {
        Write-Host "  WSL not installed or version too old (no --version support)"
        Write-Host "  Installing WSL $requiredVersion...`n" -ForegroundColor Cyan

        if (Install-WslMsi) {
            # Verify installation
            $newVersion = Get-WslVersion
            if ($newVersion) {
                Write-Host "  WSL version: $newVersion [OK]" -ForegroundColor Green
            }
            else {
                # MSI installed but wsl --version not working yet
                # Continue anyway, it usually works without reboot
                Write-Host "  WSL MSI installed, continuing..." -ForegroundColor Yellow
            }
            return $true
        }

        # MSI installation failed
        Write-Warning "WSL installation failed"
        Write-Host "  You may need to restart and run this script again." -ForegroundColor Yellow
        return $false
    }

    Write-Host "  Current WSL version: $currentVersion"

    if ($currentVersion -lt $requiredVersion) {
        Write-Host "  WSL version is below $requiredVersion, updating...`n" -ForegroundColor Yellow

        if (Install-WslMsi) {
            $newVersion = Get-WslVersion
            if ($newVersion) {
                Write-Host "  WSL updated to: $newVersion [OK]" -ForegroundColor Green
            }
            else {
                Write-Host "  WSL MSI installed, continuing..." -ForegroundColor Yellow
            }
            return $true
        }

        Write-Warning "WSL update failed"
        return $false
    }

    Write-Success "WSL version $currentVersion meets requirement (>= $requiredVersion)"
    return $true
}

function Install-UbuntuViaImport {
    param([string]$TarPath)

    $installPath = "$env:USERPROFILE\WSL\rainbond-ubuntu2204"

    # SAFETY CHECK: Don't overwrite existing working Ubuntu installation
    $existingCheck = cmd /c "wsl -d rainbond-ubuntu2204 -- echo ok" 2>&1
    if ($existingCheck -match "ok") {
        Write-Host "  rainbond-ubuntu2204 already exists and is working, skipping import" -ForegroundColor Yellow
        return
    }

    Write-Host "  Importing Ubuntu 22.04 into WSL..."

    # Create installation directory
    New-Item -ItemType Directory -Path $installPath -Force | Out-Null

    # Import the rootfs
    $result = wsl --import rainbond-ubuntu2204 $installPath $TarPath 2>&1
    $exitCode = $LASTEXITCODE

    # Check if already exists error
    $resultText = $result | Out-String
    if ($resultText -match "already registered" -or $resultText -match "registered") {
        Write-Host "  Ubuntu already registered, skipping import" -ForegroundColor Yellow
        return
    }

    # Check if kernel is missing (exit code -1 or 4294967295, or error contains wsl2kernel)
    if ($exitCode -ne 0) {
        # Check for kernel error - be very permissive with detection
        # Exit code -1 is typical for kernel missing, also check URL pattern
        $needsKernel = ($exitCode -eq -1) -or
                       ($exitCode -eq 4294967295) -or
                       ($resultText -match "wsl2kernel") -or
                       ($resultText -match "aka.ms") -or
                       ($resultText -match "kernel")

        if ($needsKernel) {
            Write-Host ""
            Write-Host "  WSL2 kernel not found, will install automatically..." -ForegroundColor Cyan
            Install-Wsl2Kernel

            # Only clean up if this is a fresh failed import, not an existing installation
            # Check if the vhdx file is very small (failed import) vs large (existing)
            $vhdxPath = "$installPath\ext4.vhdx"
            $shouldCleanup = $false
            if (Test-Path $vhdxPath) {
                $vhdxSize = (Get-Item $vhdxPath).Length
                # If less than 100MB, it's likely a failed import
                if ($vhdxSize -lt 104857600) {
                    $shouldCleanup = $true
                }
            }
            else {
                $shouldCleanup = $true
            }

            if ($shouldCleanup) {
                Write-Host "  Cleaning up failed import..."
                wsl --unregister rainbond-ubuntu2204 2>&1 | Out-Null
                if (Test-Path $installPath) {
                    Remove-Item $installPath -Recurse -Force -ErrorAction SilentlyContinue
                }
                New-Item -ItemType Directory -Path $installPath -Force | Out-Null

                # Retry import
                Write-Host "  Retrying Ubuntu import..."
                $result = wsl --import rainbond-ubuntu2204 $installPath $TarPath 2>&1
                $exitCode = $LASTEXITCODE
            }
            else {
                Write-Warning "Existing Ubuntu installation detected, not cleaning up"
                return
            }
        }
    }

    if ($exitCode -ne 0) {
        $resultText = $result | Out-String
        Send-TelemetryError -Step "ubuntu_import" `
            -ErrorMessage "Failed to import Ubuntu into WSL" `
            -ExitCode $exitCode `
            -CommandOutput "wsl --import output:`n$resultText"
        throw "Failed to import Ubuntu (exit code: $exitCode): $result"
    }

    Write-Success "Ubuntu 22.04 imported successfully"

    # Set as default distribution
    wsl --set-default rainbond-ubuntu2204 2>&1 | Out-Null
    Write-Success "rainbond-ubuntu2204 set as default distribution"
}

function Install-UbuntuOffline {
    Write-Host "  Downloading Ubuntu 22.04 rootfs..."

    $tarPath = Join-Path $script:Config.TempDir "ubuntu-22.04-rootfs.tar.gz"
    New-Item -ItemType Directory -Path $script:Config.TempDir -Force | Out-Null

    # Check if already downloaded
    if (Test-Path $tarPath) {
        $fileSize = (Get-Item $tarPath).Length
        if ($fileSize -gt 100000000) {
            $sizeMB = [math]::Round($fileSize / 1048576)
            Write-Host "  Found existing rootfs (${sizeMB}MB), using cached file"
        }
        else {
            Remove-Item $tarPath -Force
        }
    }

    if (-not (Test-Path $tarPath)) {
        Write-Host "  Downloading from $($script:Config.UbuntuRootfsUrl)..."
        Write-Host "  This may take a few minutes depending on your network speed...`n" -ForegroundColor Cyan

        Invoke-WithRetry {
            # Use curl.exe for progress display
            $curlPath = Get-Command curl.exe -ErrorAction SilentlyContinue
            if ($curlPath) {
                Write-Host "  " -NoNewline
                & curl.exe -L -# -o $tarPath $script:Config.UbuntuRootfsUrl
                if ($LASTEXITCODE -ne 0) {
                    throw "curl download failed with exit code $LASTEXITCODE"
                }
            }
            else {
                # Fallback to BITS
                try {
                    Import-Module BitsTransfer -ErrorAction Stop
                    Start-BitsTransfer -Source $script:Config.UbuntuRootfsUrl -Destination $tarPath -DisplayName "Downloading Ubuntu Rootfs"
                }
                catch {
                    Write-Host "  BITS not available, using alternative method..."
                    Write-Host "  This may take a few minutes with no progress display..." -ForegroundColor Yellow
                    $ProgressPreference = 'Continue'
                    Invoke-WebRequest -Uri $script:Config.UbuntuRootfsUrl -OutFile $tarPath -UseBasicParsing
                }
            }
        }
        Write-Host ""
        Write-Success "Ubuntu rootfs downloaded"
    }

    Install-UbuntuViaImport -TarPath $tarPath
}

function Initialize-Ubuntu {
    param([string]$Distro)

    Write-Host "  Initializing Ubuntu (creating default user)..."

    # Default user credentials
    $defaultUser = "rbd"
    $defaultPassword = "rbd"

    # Check if already initialized (has a non-root default user)
    # Use cmd to avoid PowerShell Unicode issues
    $currentUser = (cmd /c "wsl -d $Distro -- whoami" 2>&1) | Out-String
    $currentUser = $currentUser.Trim()

    if ($currentUser -and $currentUser -ne "root" -and $currentUser.Length -lt 50) {
        Write-Success "Ubuntu already initialized (user: $currentUser)"
        return
    }

    # For imported distributions, we need to create a user
    Write-Host "  Creating default user '$defaultUser'..." -ForegroundColor Cyan

    # Create user in WSL
    $createUserCmd = "useradd -m -s /bin/bash -G sudo $defaultUser"
    $userOutput = wsl -d $Distro -- bash -c $createUserCmd 2>&1
    $userExitCode = $LASTEXITCODE

    if ($userExitCode -ne 0) {
        Send-TelemetryError -Step "ubuntu_init" `
            -ErrorMessage "Failed to create user" `
            -ExitCode $userExitCode `
            -CommandOutput ($userOutput | Out-String)
        throw "Failed to create user '$defaultUser'"
    }

    # Set password non-interactively
    Write-Host "  Setting password for '$defaultUser'..."
    $pwdOutput = wsl -d $Distro -- bash -c "echo '${defaultUser}:${defaultPassword}' | chpasswd" 2>&1
    $pwdExitCode = $LASTEXITCODE

    if ($pwdExitCode -ne 0) {
        Send-TelemetryError -Step "ubuntu_init" `
            -ErrorMessage "Failed to set password" `
            -ExitCode $pwdExitCode `
            -CommandOutput ($pwdOutput | Out-String)
        throw "Failed to set password for '$defaultUser'"
    }

    # Configure sudoers for passwordless sudo
    Write-Host "  Configuring passwordless sudo for '$defaultUser'..."
    $sudoersOutput = wsl -d $Distro -- bash -c "printf '${defaultUser} ALL=(ALL) NOPASSWD:ALL\n' > /etc/sudoers.d/${defaultUser} && chmod 440 /etc/sudoers.d/${defaultUser}" 2>&1
    $sudoersExitCode = $LASTEXITCODE

    if ($sudoersExitCode -ne 0) {
        Send-TelemetryError -Step "ubuntu_init" `
            -ErrorMessage "Failed to configure sudoers" `
            -ExitCode $sudoersExitCode `
            -CommandOutput ($sudoersOutput | Out-String)
        throw "Failed to configure sudoers"
    }

    # Configure wsl.conf (use printf to avoid encoding issues)
    Write-Host "  Configuring WSL default user and systemd..."
    $confOutput = wsl -d $Distro -- bash -c "printf '[user]\ndefault=$defaultUser\n\n[boot]\nsystemd=true\n' > /etc/wsl.conf" 2>&1
    $confExitCode = $LASTEXITCODE

    if ($confExitCode -ne 0) {
        Send-TelemetryError -Step "ubuntu_init" `
            -ErrorMessage "Failed to configure wsl.conf" `
            -ExitCode $confExitCode `
            -CommandOutput ($confOutput | Out-String)
        throw "Failed to configure wsl.conf"
    }

    Write-Success "User '$defaultUser' created (password: $defaultPassword)"

    # Restart WSL to apply changes
    Write-Host "  Restarting WSL to apply user settings..."
    wsl --shutdown
    Start-Sleep -Seconds 3

    # Verify
    $verifyUser = (cmd /c "wsl -d $Distro -- whoami" 2>&1) | Out-String
    $verifyUser = $verifyUser.Trim()
    Write-Success "Ubuntu initialized (default user: $verifyUser)"
}

function Configure-WslGlobal {
    # Configure .wslconfig to prevent WSL from auto-stopping when idle
    Write-Host "  Configuring WSL global settings..."

    $wslConfigPath = "$env:USERPROFILE\.wslconfig"
    $configContent = @"
[wsl2]
# Disable auto-stop when idle (required for running services like Rainbond)
vmIdleTimeout=-1
"@

    # Check if config already exists
    if (Test-Path $wslConfigPath) {
        $existingContent = Get-Content $wslConfigPath -Raw
        if ($existingContent -match "vmIdleTimeout") {
            Write-Success ".wslconfig already configured"
            return
        }
        # Append to existing config
        Add-Content -Path $wslConfigPath -Value "`n$configContent"
    }
    else {
        # Create new config
        Set-Content -Path $wslConfigPath -Value $configContent -Encoding UTF8
    }

    Write-Success ".wslconfig configured (vmIdleTimeout=-1)"
}

function Enable-Systemd {
    param([string]$Distro)

    Write-Host "  Checking systemd status..."

    if (Test-SystemdRunning -Distro $Distro) {
        Write-Success "Systemd is already running"
        return
    }

    Write-Host "  Enabling systemd in WSL..."

    # Write config using printf to avoid encoding issues (BOM, CRLF)
    wsl -d $Distro -u root -- bash -c "printf '[boot]\nsystemd=true\n' > /etc/wsl.conf"

    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create wsl.conf"
    }

    Write-Success "wsl.conf configured"

    # Skip wsl --update as it has no progress output and takes long time
    # If WSL version is too old, systemd will fail and we'll show instructions

    # Restart WSL
    Write-Host "  Restarting WSL to enable systemd..."
    wsl --shutdown
    Start-Sleep -Seconds 3

    # Start WSL and wait for systemd
    Write-Host "  Starting WSL with systemd..."
    wsl -d $Distro -- bash -c "echo 'WSL started'" | Out-Null
    Start-Sleep -Seconds 5

    # Verify systemd
    if (Test-SystemdRunning -Distro $Distro) {
        Write-Success "Systemd is now running"
    }
    else {
        Write-Warning "Systemd may not be running. Docker installation might fail."
        Write-Host "  You may need to update Windows or WSL manually."
    }
}

function Test-RainbondInstalled {
    param([string]$Distro)

    # Check if rainbond container exists
    try {
        $result = cmd /c "wsl -d $Distro -- docker ps -a --filter name=rainbond --format '{{.Names}}'" 2>&1
        if ($result -match "rainbond") {
            return $true
        }
    }
    catch {}

    return $false
}

function Setup-AutoStart {
    param([string]$Distro)

    Write-Host "  Configuring auto-start on boot..."

    # Use shell special folder to get correct startup path (works for all languages)
    $shell = New-Object -ComObject WScript.Shell
    $startupDir = $shell.SpecialFolders("Startup")
    $vbsPath = "$startupDir\RainbondAutoStart.vbs"

    # Create VBS script (runs silently without showing command window)
    $vbsContent = @"
' Rainbond WSL Auto-Start Script
' This script runs silently at Windows startup
' Docker and Rainbond will auto-start via systemd

Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "wsl -d $Distro -- echo started", 0, False
"@

    try {
        Set-Content -Path $vbsPath -Value $vbsContent -Encoding ASCII
        Write-Success "Auto-start configured (RainbondAutoStart.vbs)"
        Write-Host "    Location: $vbsPath" -ForegroundColor Gray
    }
    catch {
        Write-Warning "Failed to create auto-start script: $($_.Exception.Message)"
    }
}

function Install-Rainbond {
    param([string]$Distro)

    # Check if Rainbond is already installed
    if (Test-RainbondInstalled -Distro $Distro) {
        Write-Success "Rainbond is already installed"

        # Check if running
        $running = cmd /c "wsl -d $Distro -- docker ps --filter name=rainbond --format '{{.Names}}'" 2>&1
        if ($running -match "rainbond") {
            Write-Host "  Rainbond container is running [OK]" -ForegroundColor Green
        }
        else {
            Write-Host "  Starting Rainbond container..." -ForegroundColor Yellow
            wsl -d $Distro -- docker start rainbond 2>&1 | Out-Null
            Write-Success "Rainbond started"
        }
        return
    }

    Write-Host "`n  Downloading and running Rainbond installation script..."
    Write-Host "  If prompted for password, enter your Ubuntu user password.`n"

    # Get WSL IP address for EIP
    $wslIp = (cmd /c "wsl -d $Distro -- hostname -I" 2>&1).Trim().Split()[0]
    $script:EIP = $wslIp

    # Download and execute installation script with EIP environment variable
    # Capture output to a log file for error reporting
    $logFile = "/tmp/rainbond-install.log"
    $installCmd = "curl -fsSL $($script:Config.RainbondInstallUrl) -o /tmp/install-rainbond.sh && sudo EIP=$wslIp bash /tmp/install-rainbond.sh 2>&1 | tee $logFile"

    wsl -d $Distro -- bash -c $installCmd

    if ($LASTEXITCODE -ne 0) {
        # Capture last 50 lines of log for error reporting
        $errorOutput = (cmd /c "wsl -d $Distro -- tail -50 $logFile" 2>&1) | Out-String
        Send-TelemetryError -Step "rainbond_install" `
            -ErrorMessage "Rainbond installation script failed" `
            -ExitCode $LASTEXITCODE `
            -CommandOutput $errorOutput
        throw "Rainbond installation failed (exit code: $LASTEXITCODE)"
    }

    Write-Success "Rainbond installed successfully"
}

function Show-Completion {
    param([string]$Distro)

    # Get WSL IP
    $wslIp = (cmd /c "wsl -d $Distro -- hostname -I" 2>&1).Trim().Split()[0]
    $script:EIP = $wslIp

    $completion = @"

========================================================================
  Installation Complete!
========================================================================

"@
    Write-Host $completion -ForegroundColor Green

    # Open browser
    Start-Sleep -Seconds 3
    Start-Process "http://localhost:7070"
}

#endregion

#region Main

function Main {
    # Display banner
    Write-Banner

    # Initialize telemetry UUID (for error tracking)
    Get-MachineUUID

    # Send startup message (to confirm script is running)
    Send-Telemetry -Message "[START] WSL installer started | $(Get-SystemInfo)" -ShowError

    # Check administrator privileges
    if (-not (Test-Administrator)) {
        Write-Error "Administrator privileges required"
        Write-Host "`n  Please right-click PowerShell and select 'Run as Administrator'"
        Write-Host "  Or run: Start-Process powershell -Verb RunAs -ArgumentList '-File', '$PSCommandPath'`n"
        Send-TelemetryError -Step "prerequisites" -ErrorMessage "Administrator privileges required"
        Read-Host "Press Enter to exit"
        exit 1
    }

    # Check Windows version
    $build = Get-WindowsBuild
    Write-Host "Windows Build: $build"

    if ($build -lt $script:Config.MinWindowsBuild) {
        Write-Error "Windows version too old (Build $build)"
        Write-Host "  Required: Build $($script:Config.MinWindowsBuild) or higher (Windows 10 2004+)"
        Write-Host "  Please upgrade Windows via Settings -> Update & Security -> Windows Update"
        Send-TelemetryError -Step "prerequisites" -ErrorMessage "Windows version too old" -CommandOutput "Build: $build, Required: $($script:Config.MinWindowsBuild)"
        Read-Host "Press Enter to exit"
        exit 1
    }

    Write-Host "Installation will start in 3 seconds..."
    Start-Sleep -Seconds 3

    # Step 0: Ensure WSL version (required for systemd support)
    if (-not (Ensure-WslVersion)) {
        throw "WSL installation/update failed. Please restart and run this script again."
    }

    # Step 1: Check WSL features
    Write-Step "1/4" "Checking WSL features..."

    if (-not (Test-WslInstalled)) {
        Write-Host "  WSL not installed, installing WSL2..."

        if (Test-WslInstallCommandSupported) {
            $result = Install-WslViaCommand
            if ($result -eq "reboot" -or $result -eq $true) {
                Request-Reboot -Reason "WSL2 installation requires a system restart."
            }
            elseif ($result -eq $false) {
                Write-Host "  'wsl --install' failed, trying legacy method..."
                $result = Install-WslLegacy
                if ($result -eq "reboot") {
                    Request-Reboot -Reason "WSL2 feature enablement requires a system restart."
                }
            }
        }
        else {
            $result = Install-WslLegacy
            if ($result -eq "reboot") {
                Request-Reboot -Reason "WSL2 feature enablement requires a system restart."
            }
        }
    }
    else {
        Write-Success "WSL is installed"
    }

    # Ensure WSL2 is default
    wsl --set-default-version 2 2>&1 | Out-Null

    # Ensure virtualization features are enabled (may have been disabled manually)
    Ensure-VirtualizationEnabled

    # Step 2: Install Ubuntu
    Write-Step "2/4" "Checking Ubuntu installation..."

    if (-not (Test-UbuntuInstalled)) {
        Write-Host "  Ubuntu not installed, installing Ubuntu 22.04..."

        if ($OfflineMode -and $UbuntuTarPath) {
            # Use provided tar file
            Install-UbuntuViaImport -TarPath $UbuntuTarPath
        }
        else {
            # Use offline method (download rootfs + import) for better progress display
            # wsl --install uses Windows background download service with no progress output
            Install-UbuntuOffline
        }
    }
    else {
        Write-Success "Ubuntu is installed"
    }

    # Get the actual distribution name
    $distro = Get-UbuntuDistroName
    if (-not $distro) {
        # If no working distro found, try to initialize rainbond-ubuntu2204
        Write-Host "  Ubuntu needs initialization..."
        $distro = "rainbond-ubuntu2204"
    }
    Write-Host "  Using distribution: $distro"

    # Step 3: Initialize Ubuntu and enable systemd
    Write-Step "3/4" "Configuring Ubuntu..."

    # Configure WSL global settings (disable auto-stop)
    Configure-WslGlobal

    # Initialize Ubuntu (create user if needed)
    Initialize-Ubuntu -Distro $distro

    # Enable systemd
    Enable-Systemd -Distro $distro

    # Step 4: Install Rainbond
    Write-Step "4/4" "Installing Rainbond..."

    Install-Rainbond -Distro $distro

    # Setup auto-start on Windows boot
    Setup-AutoStart -Distro $distro

    # Show completion message
    Show-Completion -Distro $distro

    Read-Host "Press Enter to exit"
}

# Run main function
try {
    Main
}
catch {
    Write-Host "`n========================================================================" -ForegroundColor Red
    Write-Host "  Installation failed!" -ForegroundColor Red
    Write-Host "========================================================================" -ForegroundColor Red
    Write-Host "`n  Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "`n  Stack trace:" -ForegroundColor Gray
    Write-Host $_.ScriptStackTrace -ForegroundColor Gray
    Write-Host "`n  For help, visit: https://www.rainbond.com/docs/troubleshooting/install`n"

    # Send detailed error telemetry
    Send-TelemetryError -Step "unknown" `
        -ErrorMessage $_.Exception.Message `
        -StackTrace $_.ScriptStackTrace

    Read-Host "Press Enter to exit"
    exit 1
}

#endregion
