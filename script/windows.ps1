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
#系统架构判断
function system-judgment {
    $osInfo = Get-WmiObject -Class Win32_OperatingSystem
    $isWindows = $osInfo.Caption.Contains("Windows")
    if ($isWindows) {
        $architecture = $osInfo.OSArchitecture
        $ostype="Windows"
        $osarch=$architecture
    }
    else {
        Write-ColoredText "not Windows OS" red
        Exit
    }
}
#欢迎语句
function welcome {
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
        Write-ColoredText "Docker Desktop Installed." green
        $dockerDesktopRunning = Get-Process -Name "Docker Desktop" 2>$null
    
        if ($dockerDesktopRunning) {
            Write-ColoredText "Docker Desktop Running." green
        }
        else {
            Write-ColoredText "Docker Desktop Not running, start it first" red
        }
    }
    else {
        Write-ColoredText "Docker Desktop Not installed." red
        Exit
    }
}
#输出IP提示
function messageip {
    Write-ColoredText "###############################################" green
    Write-ColoredText "# 自动检测到您的系统上有以下 IP" green
    Write-ColoredText "# 您可以通过输入其索引来选择一个" green
    Write-ColoredText "# 例如:" green
    Write-ColoredText "#   您可以输入1选择第一个IP" green
    Write-ColoredText "#   或直接回车默认使用127.0.0.1作为所选IP地址" green
    Write-ColoredText "###############################################" green
}
#选择IP地址
function selected-ip { 
    $ipAddresses = (Get-NetIPAddress | Where-Object { $_.InterfaceAlias -ne 'Loopback Pseudo-Interface 1' -and $_.AddressFamily -eq 'IPv4' }).IPAddress
    Write-ColoredText "Available local IP addresses：" green
    for ($i = 0; $i -lt $ipAddresses.Count; $i++) {
        Write-ColoredText "$($i+1). $($ipAddresses[$i])" green
    }
    $selectedIP = Read-Host "Please select the serial number of the IP address（Enter directly to select the default address 127.0.0.1）"
    if ([string]::IsNullOrWhiteSpace($selectedIP)) {
        $selectedIPAddress = '127.0.0.1'
    } elseif ($selectedIP -ge 1 -and $selectedIP -le $ipAddresses.Count) {
        $selectedIPAddress = $ipAddresses[$selectedIP - 1]
    } else {
        Write-ColoredText "Invalid choice! Please select a valid serial number." red
        exit
    } 
    Write-ColoredText "The IP address that was selected：$selectedIPAddress" green
}
#输出安装检测准备好的信息
function check-message {
        Write-ColoredText "##############################################" green
        Write-ColoredText "# Rainbond dind allinone will be installed:" green
        Write-ColoredText "# Rainbond version: $RAINBOND_VERSION" green
        Write-ColoredText "# System architecture: $osarch" green
        Write-ColoredText "# OS: $ostype" green
        Write-ColoredText "# URl: http://$($selectedIPAddress):7070" green
        Write-ColoredText "# Rainbond document: https://www.rainbond.com/docs" green
        Write-ColoredText "# If you encounter any problems, you can submit a problem to:" green
        Write-ColoredText "# https://github.com/goodrain/rainbond" green
        Write-ColoredText "# Time: $clock" green
        Write-ColoredText "##############################################" green
        Write-Host
        Write-ColoredText "开始安装rainbond请稍等" green
    
}
#启动容器
function start-rainbond {
        $containerId = docker run --privileged -d  -p 7070:7070 --name=rainbond-allinone --restart=on-failure `
        -p 80:80 -p 443:443 -p 6060:6060 -p 8443:8443 -p 10000-10010:10000-10010 `
        -v rainbond-data:/app/data `
        -v rainbond-opt:/opt/rainbond `
        -e EIP=$selectedIPAddress `
        $IMGHUB_MIRROR/rainbond:$($RAINBOND_VERSION)-dind-allinone
        if ($containerId) {
            #Write-Host "Docker The container started successfully。"
            Write-Host
            Write-ColoredText "#############################################################" green
            Write-ColoredText "Next is the installed log message, starting up, please wait~" green
            Write-ColoredText "#############################################################" green
            Start-Sleep -Seconds 130
        } else {
            Write-ColoredText "Docker 容器启动失败,请查看是否有重名" red
            # 可以处理容器启动失败的情况
        }
}
#输出日志信息
function print-logs {
    $variable =docker ps -q
    docker logs $variable
    Write-ColoredText "http://$($selectedIPAddress):7070 访问 Rainbond（Hold down CTRL+left mouse button and click on the left URL to jump）" green
    Write-ColoredText "Press any key to exit..." blue
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}
##############################main#########################
system-judgment
port-is-open-or-no
welcome
docker-install-and-run
messageip
selected-ip
check-message
start-rainbond
print-logs


