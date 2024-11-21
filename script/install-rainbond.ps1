################################################################################
# Copyright (c) Goodrain, Inc.
#
# This source code is licensed under the LGPL-3.0 license found in the
# LICENSE file in the root directory of this source tree.
################################################################################

param($IMAGE_MIRROR="registry.cn-hangzhou.aliyuncs.com/goodrain", $RAINBOND_VERSION="v6.0.0-release")
$DATE=Get-Date -Format "yyyy-MM-dd HH:mm:ss"

function Write-ColoredText($Text,$Color) {
    switch -regex ($Color) {
        "green" {
            Write-Host "$DATE - INFO: $Text" -ForegroundColor green
            send_msg $Text
        }
        "yellow" {
            Write-Host "$DATE - WARN: $Text" -ForegroundColor yellow
            send_msg $Text
        }
        "red" {
            Write-Host "$DATE - ERROR: $Text" -ForegroundColor red
            send_msg $Text
        }
    }
}

function send_msg ($msg) {

    $os_name = (Get-WmiObject -Class Win32_OperatingSystem).Name
    $body = @{
        "message" = "$msg"
        "os_info" = "$os_name"
        "eip" = "$EIP"
        "uuid" = "$UUID"
    } | ConvertTo-Json
    $params = @{
        Uri = "https://log.rainbond.com/dindlog"
        Method = "POST"
        ContentType = "application/json"
        Body = $body
    }
    Invoke-RestMethod @params > $null
}

$os_info = Get-WmiObject -Class Win32_OperatingSystem
if ($os_info.Name -match 'Microsoft Windows') {
    $os_arch = $os_info.OSArchitecture
    $os_type = $os_info.Name.Split("|")[0]
} else {
    Write-ColoredText "The current system is not Windows OS" red
    Exit
}

function check_docker {

    if (-not (Get-Command -Name docker -ErrorAction SilentlyContinue)) {
        Write-ColoredText "Ops! Docker has not been installed.`nPlease visit the following website to get the latest Docker Desktop for Windows.`n`thttps://docs.docker.com/desktop/install/windows-install/" red
        Exit
    }
    if (-not (Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue)) {
        Write-ColoredText "Ops! Docker daemon is not running. Start docker first please.`n`t- For Windows, start the Docker Desktop for Windwos.`n`t- And re-exec this script." red
        Exit
    }
    if (docker ps -a | Select-String "rainbond") {
        Write-ColoredText "Ops! rainbond container already exists.`n`t- Ensure if rainbond is running.`n`t- Try to exec 'docker start rainbond' to start it.`n`t- Or you can remove it by 'docker rm -f rainbond'" red
        Exit
    }
}

function MD5 {
    $systemInfo = Get-CimInstance Win32_OperatingSystem | Select-Object Caption, OSArchitecture, Manufacturer, SerialNumber
    $infoString = $systemInfo | ForEach-Object { $_.Caption + $_.OSArchitecture + $_.Manufacturer + $_.SerialNumber } | Out-String
    $md5Hasher = [System.Security.Cryptography.MD5]::Create()
    $hashBytes = $md5Hasher.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($infoString))
    $global:UUID = [System.BitConverter]::ToString($hashBytes).ToLower() -replace "-", ""
}

function Test-ValidIPAddress {
    param (
        [string]$IPAddress
    )

    $pattern = '^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    $regex = [System.Text.RegularExpressions.Regex]::new($pattern)

    if ($IPAddress -match $regex) {
        return $true
    } else {
        return $false
    }
}

function select_eip { 
    Write-Host "Welcome to install Rainbond, If you install problem, please feedback to https://www.rainbond.com/community/support. `n" -ForegroundColor green

    Write-Host "######################################################################" -ForegroundColor green
    Write-Host "# The script automatically detects IP addresses in the system" -ForegroundColor green
    Write-Host "# You can choose one by enter its index" -ForegroundColor green
    Write-Host "# If you have an Public IP, Just type it in" -ForegroundColor green
    Write-Host "######################################################################" -ForegroundColor green

    $Default_IP = "127.0.0.1"
    Write-Host "The following IP has been detected:" -ForegroundColor green
    $IPAddress_List = (Get-NetIPAddress | Where-Object { $_.InterfaceAlias -ne 'Loopback Pseudo-Interface 1' -and $_.AddressFamily -eq 'IPv4' }).IPAddress

    for ($i = 0; $i -lt $IPAddress_List.Count; $i++) {
        Write-Host "$($i+1). $($IPAddress_List[$i])"
    }
    $Custom_EIP = Read-Host "For example: enter '1 or 2' to choose the IP, or input '11.22.33.44'(IPv4 address) for specific one, press enter to use the default IP address`nEnter your choose or a specific IP address( Default IP is $Default_IP)"
    if ([string]::IsNullOrWhiteSpace($Custom_EIP)) {
        $global:EIP = $Default_IP
    } elseif ($Custom_EIP -match '^\d+$') {
        $index = [int]$Custom_EIP
        if ($index -ge 1 -and $index -le $IPAddress_List.Count) {
            $global:EIP = $IPAddress_List[$index - 1]
        }
        else {
            Write-ColoredText "Invalid index, please run the script again and enter a valid index." red
            exit
        }
    } elseif (-not (Test-ValidIPAddress $selectedIP)){
        Write-ColoredText "Invalid IP address, please run the script again and enter a valid IP address." red
        Exit
    } 

    Write-Host "The selected IP address is: $EIP" -ForegroundColor green
}

function start_rainbond {
    
    Write-Host "##############################################" -ForegroundColor green
    Write-Host "# Rainbond standalone will be installed:" -ForegroundColor green
    Write-Host "# Rainbond version: $RAINBOND_VERSION" -ForegroundColor green
    Write-Host "# Arch: $os_arch" -ForegroundColor green
    Write-Host "# OS: $os_type" -ForegroundColor green
    Write-Host "# Web Site: http://${EIP}:7070" -ForegroundColor green
    Write-Host "# Rainbond Docs: https://www.rainbond.com/docs" -ForegroundColor green
    Write-Host "# If you install problem, please feedback to:" -ForegroundColor green
    Write-Host "#    https://www.rainbond.com/community/support" -ForegroundColor green
    Write-Host "##############################################" -ForegroundColor green
    Write-Host "Generating the installation command:" -ForegroundColor green

    $RBD_IMAGE = "$IMAGE_MIRROR/rainbond:$($RAINBOND_VERSION)-k3s"
    $docker_run_cmd = "docker run --privileged -d --name=rainbond --restart=always -p 7070:7070 -p 80:80 -p 443:443 -p 6060:6060 -p 30000-30010:30000-30010 -v rainbond-opt:/opt/rainbond -e EIP=$EIP -e uuid=$UUID $RBD_IMAGE"
    Write-Host $docker_run_cmd
    send_msg $docker_run_cmd

    Write-ColoredText "Pulling image ${RBD_IMAGE}..." green
    if (-not (docker pull $RBD_IMAGE)) {
        Write-ColoredText "Ops! Pull image ${RBD_IMAGE} failed. Please check your network." red
        Exit
    }

    $container_id = Invoke-Expression $docker_run_cmd
    if ($container_id) {
        Write-ColoredText "Please waiting 5 minutes and enter http://${EIP}:7070 the browser to access the Rainbond." green
    } else {
        Write-ColoredText "Ops! Rainbond container startup failed, Execute the 'docker logs -f rainbond' command to view startup logs." red
        Exit
    }
}

MD5

check_docker

select_eip

start_rainbond