$OutputEncoding = [System.Text.Encoding]::GetEncoding("UTF-8")
#基本环境变量
$RAINBOND_VERSION="v5.14.2"
$IMGHUB_MIRROR="registry.cn-hangzhou.aliyuncs.com/goodrain"
$clock=Get-Date
$ports = @(80, 443, 6060, 7070, 8443)

#定义颜色输出函数
function Write-ColoredText($Text,$Color) {
    Write-Host $Text -ForegroundColor $Color
}
#系统MD5值
function cmd5 {
    $systemInfo = Get-CimInstance Win32_OperatingSystem | Select-Object Caption, OSArchitecture, Manufacturer, SerialNumber
    $infoString = $systemInfo | ForEach-Object { $_.Caption + $_.OSArchitecture + $_.Manufacturer + $_.SerialNumber } | Out-String
    #使用MD5哈希算法计算信息的哈希值
    $md5Hasher = [System.Security.Cryptography.MD5]::Create()
    $hashBytes = $md5Hasher.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($infoString))
    $global:md5Hash = [System.BitConverter]::ToString($hashBytes) -replace "-", ""
    #Write-Host "系统信息的MD5哈希值:$global:md5Hash"
}
#请求信息记录
function send_msg {
    $dest_url = "https://log.rainbond.com"
    
    if (-not $global:args) {
        $msg = "Terminating by userself."
    }
    else {
        $msg = $global:args[0] -replace '"', ' ' -replace "'", ' '
    }
    
    $body = @{
        "message" = $msg
        "os_info" = [System.Environment]::OSVersion.Version
        "eip" = $selectedIP
        "uuid" = $md5Hash
    } | ConvertTo-Json
    
    $params = @{
        Uri = "$dest_url/dindlog"
        Method = "POST"
        ContentType = "application/json"
        Body = $body
    }
    
    try {
        Invoke-RestMethod @params > $null
    }
    catch {
        ;
    }

    if ($msg -eq "Terminating by userself.") {
        exit
    }
    #Write-Host Invoke-RestMethod @params
}
#系统架构判断
function system-judgment {
    $osInfo = Get-WmiObject -Class Win32_OperatingSystem
    $isWindows = $osInfo.Caption.Contains("Windows")
    if ($isWindows) {
        $architecture = $osInfo.OSArchitecture
        $global:ostype="Windows"
        $global:osarch=$architecture
    }
    else {
        Write-ColoredText "not Windows OS" red
        Exit
    }
}
#欢迎语句
function welcome {
    $global:args="$clock :Welcome! Let's get started Rainbond dind allinone install..."
    send_msg
    Write-ColoredText "$clock :Welcome! Let's get started Rainbond dind allinone install..." green  
}
#检测端口是否开放
function port-is-open-or-no {  
    foreach ($port in $ports) {
        $tcpClient = New-Object System.Net.Sockets.TcpClient
        try {
            $tcpClient.Connect('localhost', $port)
            $tcpClient.Close()
            Write-ColoredText "Warning port $port Opened." Yellow
        } catch {
        
        }
    }
}
#检测 Docker 是否已安装,且是否正在运行
function docker-install-and-run {
    $dockerDesktopInstalled = Get-Command -ErrorAction SilentlyContinue -Name "docker" | Select-Object -First 1

    if ($dockerDesktopInstalled) {
        ;
        $dockerDesktopRunning = Get-Process -Name "Docker Desktop" 2>$null
    
        if ($dockerDesktopRunning) {
            ;
        }
        else {
            Write-ColoredText "Docker Desktop Not running, start it first" red
            Exit
        }
    }
    else {
        Write-ColoredText "Docker Desktop Not installed." red
        Exit
    }
}
#输出IP提示
function messageip {
    Write-ColoredText "######################################################################" green
    Write-ColoredText "# The following IPs are automatically detected on your system" green
    Write-ColoredText "# You can select one by entering its index" green
    Write-ColoredText "# For example:" green
    Write-ColoredText "#   You can enter 1 to select the first IP" green
    Write-ColoredText "#   Or enter an IP address like 11.22.33.44" green
    Write-ColoredText "#   Or directly enter 127.0.0.1 as the selected IP address by default" green
    Write-ColoredText "######################################################################" green
}
#选择IP地址
function selected-ip { 
    $defaultIP = "127.0.0.1"
    Write-ColoredText "Available local IP addresses:" green
    $ipAddresses = (Get-NetIPAddress | Where-Object { $_.InterfaceAlias -ne 'Loopback Pseudo-Interface 1' -and $_.AddressFamily -eq 'IPv4' }).IPAddress

    for ($i = 0; $i -lt $ipAddresses.Count; $i++) {
        Write-ColoredText "$($i+1). $($ipAddresses[$i])" green
    }
    $selectedIP = Read-Host "Please select the serial number of the IP address (Enter directly to select the default address 127.0.0.1)"
    if ([string]::IsNullOrWhiteSpace($selectedIP)) {
        $global:selectedIP = $defaultIP
    }
    elseif ($selectedIP -match '^\d+$') {
        $selectedIndex = [int]$selectedIP
        if ($selectedIndex -ge 1 -and $selectedIndex -le $ipAddresses.Count) {
            $global:selectedIP = $ipAddresses[$selectedIndex - 1]
        }
        else {
            Write-ColoredText "Invalid index, please run the script again and enter a valid index." red
            exit
        }
    } 
    else {
        if ([System.Net.IPAddress]::TryParse($selectedIP, [ref]$null)) {
            $global:selectedIP = $selectedIP
        }
        else {
            Write-ColoredText "Invalid IP address, please run the script again and enter a valid IP address." red
            exit
        }
    }

    Write-Host
    Write-ColoredText "The selected IP address is: $global:selectedIP" blue
    Write-Host
}
#输出安装检测准备好的信息
function check-message {
        Write-ColoredText "##############################################" green
        Write-ColoredText "# Rainbond dind allinone will be installed:" green
        Write-ColoredText "# Rainbond version: $RAINBOND_VERSION" green
        Write-ColoredText "# System architecture: $osarch" green
        Write-ColoredText "# OS: $ostype" green
        Write-ColoredText "# URL: http://$($global:selectedIP):7070" green
        Write-ColoredText "# Rainbond document: https://www.rainbond.com/docs" green
        Write-ColoredText "# If you encounter any problems, you can submit a problem to:" green
        Write-ColoredText "# https://github.com/goodrain/rainbond" green
        Write-ColoredText "# Time: $clock" green
        Write-ColoredText "##############################################" green
        Write-Host
        Write-ColoredText "To start installing Rainbond, please wait" green
}
#启动容器
function start-rainbond {
    $containerId = docker run --privileged -d  -p 7070:7070 --name=rainbond-allinone --restart=on-failure `
    -p 80:80 -p 443:443 -p 6060:6060 -p 8443:8443 -p 10000-10010:10000-10010 `
    -v rainbond-data:/app/data `
    -v rainbond-opt:/opt/rainbond `
    -e EIP=$global:selectedIP `
    -e uuid=$global:selectedIP `
    $IMGHUB_MIRROR/rainbond:$($RAINBOND_VERSION)-dind-allinone
    if ($containerId) {
        $global:args = "Docker The container started successfully."
        send_msg
        Write-Host
        Write-ColoredText "#############################################################" green
        Write-ColoredText "Next is the installed log message, starting up, please wait~" green
        Write-ColoredText "#############################################################" green
        Start-Sleep -Seconds 130
    } else {
        Write-Host
        Write-ColoredText "Docker The container failed to start, check to see if there is a duplicate name" red
        $global:args=docker logs rainbond-allinone
        send_msg
        exit
    }
}
#输出日志信息
function print-logs {
Write-Host
Write-Host
$variable =docker ps -q
docker logs $variable
if ($LASTEXITCODE -eq 0) {
    Write-Host
    Write-Host
    Write-ColoredText "http://$($global:selectedIP):7070 Access Rainbond(Hold down CTRL+left mouse button and click on the left URL to jump)" green
}
Write-ColoredText "Press any key to exit..." blue
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}
##############################main#########################
cmd5
system-judgment
port-is-open-or-no
welcome
#send_msg
docker-install-and-run
messageip
selected-ip
check-message
start-rainbond
print-logs
