# This script is used to install Rainbond standalone on Windows

param($IMAGE_MIRROR="registry.cn-hangzhou.aliyuncs.com/goodrain", $RAINBOND_VERSION="v6.3.1-release")
$DATE=Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$Language = (Get-Culture).Name

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
    if ($Language -eq "zh-CN") {
      Write-ColoredText "当前系统不是Windows OS" red
    } else {
      Write-ColoredText "The current system is not Windows OS" red
    }
    Exit
}

function check_port_occupied {
  param (
    [int[]]$Ports = @(7070, 80, 443, 6060)
  )
  
  if ($Language -eq "zh-CN") {
    Write-ColoredText "开始检测端口占用情况..." green
  } else {
    Write-ColoredText "Start detecting port occupation..." green
  }

  $occupiedPorts = @()
  
  foreach ($port in $Ports) {
    $connection = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($connection) {
      $processId = $connection.OwningProcess
      $processName = (Get-Process -Id $processId -ErrorAction SilentlyContinue).ProcessName
      
      # Skip system idle process (PID 0) and system processes that don't actually block the port
      if ($processId -ne 0 -and $processName -ne "Idle" -and $processName -ne "System") {
        $occupiedPorts += @{
          Port = $port
          ProcessId = $processId
          ProcessName = $processName
        }
      }
    }
  }
    
  if ($occupiedPorts.Count -gt 0) {
    if ($Language -eq "zh-CN") {
      Write-ColoredText "检测到以下端口已被占用：" red
      foreach ($portInfo in $occupiedPorts) {
        Write-ColoredText "  端口 $($portInfo.Port) 被进程 $($portInfo.ProcessName) (PID: $($portInfo.ProcessId)) 占用" red
      }
      Write-ColoredText "请释放这些端口后重新运行脚本，或者停止相关进程。" red
    } else {
      Write-ColoredText "The following ports are already occupied:" red
      foreach ($portInfo in $occupiedPorts) {
        Write-ColoredText "  Port $($portInfo.Port) is occupied by process $($portInfo.ProcessName) (PID: $($portInfo.ProcessId))" red
      }
      Write-ColoredText "Please free these ports and re-run the script, or stop the related processes." red
    }
    return $false
  }
    
  if ($Language -eq "zh-CN") {
    Write-ColoredText "端口检测通过，所有必需端口可用" green
  } else {
    Write-ColoredText "Port check passed, all required ports are available" green
  }
  return $true
}

function check_rainbond_container {
  # Check if docker is available and working
  if (-not (Get-Command -Name docker -ErrorAction SilentlyContinue)) {
    return
  }
  
  try {
    docker info | Out-Null
  } catch {
    return
  }
    
  # Check if rainbond container exists
  $containerExists = docker ps -a --filter "name=^rainbond$" --format "{{.Names}}" | Where-Object { $_ -eq "rainbond" }
    
  if ($containerExists) {
    # Check if container is running
    $containerRunning = docker ps --filter "name=^rainbond$" --filter "status=running" --format "{{.Names}}" | Where-Object { $_ -eq "rainbond" }
    
    if ($containerRunning) {
      # Container is running, get EIP and exit
      $get_eip = docker inspect rainbond --format '{{range .Config.Env}}{{println .}}{{end}}' | Where-Object { $_ -match '^EIP=' } | ForEach-Object { $_.Split('=')[1] }
      
      if ($Language -eq "zh-CN") {
          Write-ColoredText "Rainbond 容器已在运行中.`n`t- 请在浏览器中输入 http://${get_eip}:7070 访问 Rainbond." green
      } else {
          Write-ColoredText "Rainbond container is already running.`n`t- Please enter http://${get_eip}:7070 in the browser to access Rainbond." green
      }
      exit 0
    } else {
      # Container exists but is not running, try to start it
      if ($Language -eq "zh-CN") {
          Write-ColoredText "Rainbond 容器已存在但未运行，正在尝试启动..." yellow
      } else {
          Write-ColoredText "Rainbond container exists but not running, trying to start..." yellow
      }
        
      if (docker start rainbond) {
        Start-Sleep -Seconds 3
        $get_eip = docker inspect rainbond --format '{{range .Config.Env}}{{println .}}{{end}}' | Where-Object { $_ -match '^EIP=' } | ForEach-Object { $_.Split('=')[1] }
        
        if ($Language -eq "zh-CN") {
          Write-ColoredText "Rainbond 容器启动成功.`n`t- 请在浏览器中输入 http://${get_eip}:7070 访问 Rainbond." green
        } else {
          Write-ColoredText "Rainbond container started successfully.`n`t- Please enter http://${get_eip}:7070 in the browser to access Rainbond." green
        }
        exit 0
      } else {
        if ($Language -eq "zh-CN") {
          Write-ColoredText "Rainbond 容器启动失败，请手动执行 docker start rainbond" red
        } else {
          Write-ColoredText "Failed to start Rainbond container, please manually run docker start rainbond" red
        }
        exit 1
      }
    }
  }
}

function check_docker {

  if (-not (Get-Command -Name docker -ErrorAction SilentlyContinue)) {
    if ($Language -eq "zh-CN") {
      Write-ColoredText "未检测到 Docker 环境, 请先安装 Docker Desktop, 然后重新执行本脚本. 请参考文档: https://www.docker.com/products/docker-desktop/" red
    } else {
      Write-ColoredText "Ops! Docker has not been installed. Please install Docker Desktop and re-run this script. ref: https://www.docker.com/products/docker-desktop/" red
    }
    Exit
  }
  if (-not (Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue)) {
    if ($Language -eq "zh-CN") {
      Write-ColoredText "检测到 Docker Desktop 已安装但未运行，请先启动 Docker Desktop 后重新执行脚本." red
    } else {
      Write-ColoredText "Docker Desktop is installed but not running. Please start Docker Desktop and re-run this script." red
    }
    Exit
  }
    
  # Check for existing rainbond container before proceeding
  check_rainbond_container
  
  # Check if required ports are available
  if (-not (check_port_occupied)) {
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
  if ($Language -eq "zh-CN") {
    Write-Host "######################################################################" -ForegroundColor green
    Write-Host "# 脚本自动检测系统中的IP地址" -ForegroundColor green
    Write-Host "# 您可以通过输入索引来选择一个" -ForegroundColor green
    Write-Host "# 如果您有公网IP，请直接输入" -ForegroundColor green
    Write-Host "######################################################################" -ForegroundColor green
    Write-Host "检测到以下IP地址：" -ForegroundColor green
  } else {
    Write-Host "######################################################################" -ForegroundColor green
    Write-Host "# The script automatically detects IP addresses in the system" -ForegroundColor green
    Write-Host "# You can choose one by enter its index" -ForegroundColor green
    Write-Host "# If you have an Public IP, Just type it in" -ForegroundColor green
    Write-Host "######################################################################" -ForegroundColor green
    Write-Host "The following IP has been detected:" -ForegroundColor green
  }

  $IPAddress_List = (Get-NetIPAddress | Where-Object { $_.InterfaceAlias -ne 'Loopback Pseudo-Interface 1' -and $_.AddressFamily -eq 'IPv4' -and $_.IPAddress -ne '127.0.0.1' }).IPAddress

  for ($i = 0; $i -lt $IPAddress_List.Count; $i++) {
    Write-Host "$($i+1). $($IPAddress_List[$i])"
  }
  if ($Language -eq "zh-CN") {
    $Custom_EIP = Read-Host "例如: 输入 '1 or 2' 选择 IP, 或指定IP '11.22.33.44'(IPv4 address), 直接回车则使用默认 IP 地址 (默认: $($IPAddress_List[0]))"
  } else {
    $Custom_EIP = Read-Host "For example: enter '1 or 2' to choose the IP, or input '11.22.33.44'(IPv4 address) for specific one, press enter to use the default IP address (default: $($IPAddress_List[0]))"
  }
    
  if ([string]::IsNullOrWhiteSpace($Custom_EIP)) {
    # Use first IP as default
    if ($IPAddress_List.Count -gt 0) {
      $global:EIP = $IPAddress_List[0]
    } else {
      if ($Language -eq "zh-CN") {
        Write-ColoredText "未检测到有效的IP地址，请检查网络配置。" red
      } else {
        Write-ColoredText "No valid IP address detected, please check network configuration." red
      }
      Exit
    }
  } elseif ($Custom_EIP -eq "127.0.0.1" -or $Custom_EIP -eq "0.0.0.0") {
    if ($Language -eq "zh-CN") {
      Write-ColoredText "不能使用127.0.0.1和0.0.0.0作为EIP，请重新运行脚本并输入有效的IP地址。" red
    } else {
      Write-ColoredText "127.0.0.1 and 0.0.0.0 cannot be used as EIP, please rerun the script and enter a valid IP address." red
    }
    Exit
  } elseif ($Custom_EIP -match "^\d+$") {
    # Handle numeric index input
    $index = [int]$Custom_EIP
    # Check if IP list is empty
    if ($IPAddress_List.Count -eq 0) {
      if ($Language -eq "zh-CN") {
        Write-ColoredText "未检测到有效的IP地址，无法使用索引选择。" red
      } else {
        Write-ColoredText "No valid IP addresses detected, cannot use index selection." red
      }
      Exit
    }
    # Check if index is within valid range
    if ($index -ge 1 -and $index -le $IPAddress_List.Count) {
      $global:EIP = $IPAddress_List[$index - 1]
    } else {
      if ($Language -eq "zh-CN") {
        Write-ColoredText "无效索引 $index，请输入 1 到 $($IPAddress_List.Count) 之间的数字，或输入有效的IPv4地址。" red
      } else {
        Write-ColoredText "Invalid index $index, please enter a number between 1 and $($IPAddress_List.Count), or enter a valid IPv4 address." red
      }
      Exit
    }
  } elseif (Test-ValidIPAddress $Custom_EIP) {
    # Handle valid IPv4 address input
    $global:EIP = $Custom_EIP
  } else {
    # Handle invalid input
    if ($Language -eq "zh-CN") {
      Write-ColoredText "无效输入 '$Custom_EIP'，请输入有效的IPv4地址（如 192.168.1.100）或选择索引号（1-$($IPAddress_List.Count)）。" red
    } else {
      Write-ColoredText "Invalid input '$Custom_EIP', please enter a valid IPv4 address (e.g., 192.168.1.100) or select an index number (1-$($IPAddress_List.Count))." red
    }
    Exit
  }

  if ($Language -eq "zh-CN") {
    Write-ColoredText "选择的IP地址是: $EIP" green
  } else {
    Write-ColoredText "The selected IP address is: $EIP" green
  }
}

function start_rainbond {
    
  if ($Language -eq "zh-CN") {
    Write-ColoredText "生成 Docker 安装命令:" green
  } else {
    Write-ColoredText "Generating Docker installation command:" green
  }

  $RBD_IMAGE = "$IMAGE_MIRROR/rainbond:$($RAINBOND_VERSION)-k3s"
  $docker_run_cmd = "docker run --privileged -d --name=rainbond --restart=always -p 7070:7070 -p 80:80 -p 443:443 -p 6060:6060 -p 30000-30010:30000-30010 -v rainbond-opt:/opt/rainbond -e EIP=$EIP -e uuid=$UUID $RBD_IMAGE"
  Write-ColoredText $docker_run_cmd green
  send_msg $docker_run_cmd

  if ($Language -eq "zh-CN") {
    Write-ColoredText "拉取镜像 $RBD_IMAGE..." green
  } else {
    Write-ColoredText "Pulling image $RBD_IMAGE..." green
  }

  docker pull $RBD_IMAGE
  if ($LASTEXITCODE -ne 0) {
    if ($Language -eq "zh-CN") {
      Write-ColoredText "拉取镜像 $RBD_IMAGE 失败. 请检查您的网络." red
    } else {
      Write-ColoredText "Pull image $RBD_IMAGE failed. Please check your network." red
    }
    Exit
  }

  $container_id = Invoke-Expression $docker_run_cmd
  if ($container_id) {
    if ($Language -eq "zh-CN") {
      Write-ColoredText "Rainbond 容器启动成功." green
    } else {
      Write-ColoredText "Rainbond container started successfully." green
    }
  } else {
    if ($Language -eq "zh-CN") {
      Write-ColoredText "Rainbond 容器启动失败." red
    } else {
      Write-ColoredText "Rainbond container startup failed." red
    }
    Exit
  }

  if ($Language -eq "zh-CN") {
    Write-Host "###############################################" -ForegroundColor green
    Write-Host "# Rainbond 版本: $RAINBOND_VERSION" -ForegroundColor green
    Write-Host "# 架构: $os_arch" -ForegroundColor green
    Write-Host "# 操作系统: $os_type" -ForegroundColor green
    Write-Host "# Rainbond 文档: https://www.rainbond.com/docs" -ForegroundColor green
    Write-Host "###############################################" -ForegroundColor green
    Write-Host "# 访问 Rainbond:" -ForegroundColor green
    Write-Host "#     - 请等待 5 分钟左右系统完全启动，随后在浏览器中输入 http://${EIP}:7070 访问 Rainbond." -ForegroundColor green
    Write-Host "#     - 您可以通过以下命令观察启动进度: " -ForegroundColor green
    Write-Host "#         - docker exec -it rainbond bash " -ForegroundColor green
    Write-Host "#         - watch kubectl get pod -n rbd-system" -ForegroundColor green
    Write-Host "#     - 如遇问题，请阅读故障排除文档 https://www.rainbond.com/docs/troubleshooting/install" -ForegroundColor green
    Write-Host "# 如无法解决，请反馈至: " -ForegroundColor green
    Write-Host "#     - https://www.rainbond.com/docs/support" -ForegroundColor green
    Write-Host "###############################################" -ForegroundColor green
  } else {
    Write-Host "###############################################" -ForegroundColor green
    Write-Host "# Rainbond Version: $RAINBOND_VERSION" -ForegroundColor green
    Write-Host "# Arch: $os_arch" -ForegroundColor green
    Write-Host "# OS: $os_type" -ForegroundColor green
    Write-Host "# Rainbond Docs: https://www.rainbond.com/docs" -ForegroundColor green
    Write-Host "###############################################" -ForegroundColor green
    Write-Host "# Access Rainbond:" -ForegroundColor green
    Write-Host "#     - Please wait 5 minutes for system to fully start, then enter http://${EIP}:7070 in the browser to access Rainbond." -ForegroundColor green
    Write-Host "#     - You can observe the startup progress with the following commands:" -ForegroundColor green
    Write-Host "#         - docker exec -it rainbond bash " -ForegroundColor green
    Write-Host "#         - kubectl get pod -n rbd-system" -ForegroundColor green
    Write-Host "#     - If you encounter problems, please read the troubleshooting document https://www.rainbond.com/docs/troubleshooting/install" -ForegroundColor green
    Write-Host "# If you cannot solve the problem, please feedback to:" -ForegroundColor green
    Write-Host "#     - https://www.rainbond.com/docs/support" -ForegroundColor green
    Write-Host "###############################################" -ForegroundColor green
  }
}

check_docker

MD5

select_eip

start_rainbond