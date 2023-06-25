@echo off
@chcp 65001 >nul

::基本环境变量
set RAINBOND_VERSION=VERSION:-v5.14.1
set IMGHUB_MIRROR=registry.cn-hangzhou.aliyuncs.com/goodrain
set OS_TYPE=%OS%
set clock=%date%---%time%

::系统判断
:System-judgment
        @echo off
        if "%OS%"=="Windows_NT" goto continue
            echo 此脚本仅在 Windows 操作系统上运行。
        exit /b
        :continue
            echo 这是一个 Windows 操作系统 >nul

        ::系统架构判断
        @echo off
        IF "%PROCESSOR_ARCHITECTURE%"=="x86" (
            set OS_ARCH=x86
        ) ELSE IF "%PROCESSOR_ARCHITECTURE%"=="AMD64" (
            set OS_ARCH=AMD64
        )


::检测端口是否开放
:port-is-open-or-no
        @echo off
        setlocal enabledelayedexpansion
        set PORTS_IN_USE=0
        set LISTEN_PORTS=80 443 6060 7070 8443
        for %%p in (%LISTEN_PORTS%) do (
            netstat -an | findstr ":!p " >nul
            if !errorlevel! equ 0 (
                set PORTS_IN_USE=1
                echo 警告端口 %%p 正在使用.
            ) else (
                echo Port %%p is not in use. >nul
            )
        )
        if %PORTS_IN_USE%==1 (
            echo.  
            echo 请修改或者清理之前的环境，按任意键退出！
            pause >nul
            exit /b
        )


:: 检查 Docker 是否已安装,且是否正在运行
:docker-install-and-run
        @echo off
        rem 检查是否安装了 Docker 桌面
        where docker >nul 2>&1
        if %errorlevel% equ 0 (
            rem 检查 Docker Desktop 是否正在运行
            docker system info >nul 2>&1
            if %errorlevel% equ 0 (
                echo Docker Desktop 已经安装且正在运行.>nul
            ) else (
                echo Docker Desktop 已经安装但是没有运行，请先点击docker-desktop运行.
                exit
            )
        ) else (
            echo Docker Desktop 没有安装请先按照官网安装.
            exit
        )


::欢迎语句
:welcome
        @echo off
        echo ###################################### Start ####################################
        echo "%clock%:欢迎！让我们开始 Rainbond dind allinone 安装..."
        echo #################################################################################


::选择IP地址
:selected-ip
        echo.
        echo ###############################################
        echo # 自动检测到您的系统上有以下 IP
        echo # 您可以通过输入其索引来选择一个
        @echo off 
        echo # 例如: 
        echo #   您可以输入1选择第一个IP
        echo #   或直接回车默认使用127.0.0.1作为所选IP地址
        echo ###############################################
        echo.
        ::检测IP地址用来选择绑定的ip
        @echo off
        setlocal enabledelayedexpansion
        set "defaultIP=127.0.0.1"
        set "counter=1"
        for /f "tokens=2 delims=:" %%A in ('ipconfig ^| findstr /c:"IPv4"') do (
            for /f "tokens=1 delims= " %%B in ("%%A") do (
                set "IP[!counter!]=%%B"
                echo !counter!. %%B
                set /a counter+=1      
            )
        )
        echo.
        echo 请选择一个IP地址(默认回车为 %defaultIP%)
        set /p choice=请输入选项数字：

        if "%choice%"=="" (
            set "selectedIP=%defaultIP%"
        ) else if not defined IP[%choice%] (
            echo 无效选项！
            exit /b 1
        ) else (
            set "selectedIP=!IP[%choice%]!"
        )


::输出安装检测准备好的信息
:check-message
        @echo off
        echo ###############################################
        echo # Rainbond dind allinone 将安装:
        echo # Rainbond 版本: %RAINBOND_VERSION%
        echo # 系统架构: %OS_ARCH%
        echo # 系统: %OS_TYPE%
        echo # 网址: http://%selectedIP%:7070
        echo # Rainbond 文档: https://www.rainbond.com/docs
        echo # 如果您遇到任何问题，都可以提交问题到:
        echo # https://github.com/goodrain/rainbond
        echo # 时间: %clock%
        echo ###############################################
        echo.
        echo 开始安装rainbond请稍等
        timeout /t 3


::启动容器
:start-rainbond
        call docker run --privileged -d  -p 7070:7070 --name=rainbond-allinone --restart=on-failure ^
        -p 80:80 -p 443:443 -p 6060:6060 -p 8443:8443 -p 10000-10010:10000-10010 ^
        -v rainbond-data:/app/data ^
        -v rainbond-opt:/opt/rainbond ^
        -e EIP=%selectedIP% ^
        registry.cn-hangzhou.aliyuncs.com/goodrain/rainbond:v5.14.2-dind-allinone
        if errorlevel 1 goto Fail
        if errorlevel 0 goto Success


        :Fail
        echo.
        echo docker启动失败或者已经启动,请按任意键继续
        echo.
        pause >nul

        :Success 
        echo docker 成功安装>nul
        echo.
        echo ###############################################
        echo 接下来是已经安装好的日志信息，正在启动请稍等~
        echo ###############################################
        echo.
        timeout /t 150

::输出日志信息
:print-logs
        for /f "usebackq delims=" %%i in (`docker ps -q`) do set dockerID=%%i
        docker logs %dockerID%
        echo 请通过 http://%selectedIP%:7070 访问 Rainbond（按住ctrl+鼠标左键单击即左边网址即可跳转）
        @echo off
        echo 按任意键退出脚本
        pause >nul
        exit /b

::#############################main###########################
if 
call :System-judgment
call :port-is-open-or-no
call :docker-install-and-run
call :welcome
call :selected-ip
call :check-message
call :start-rainbond
call :print-logs
