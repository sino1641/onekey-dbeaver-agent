@echo off
setlocal enabledelayedexpansion

REM DBeaver License Generator Script
REM Usage: gen-license.bat [OPTIONS] [DBeaver_Path]
REM
REM Arguments:
REM   DBeaver_Path    Path to DBeaver installation directory or executable (optional, will prompt if not provided)
REM
REM Options:
REM   -h, --help                Show help message
REM   -t <type>                 License type: le (Lite), ee (Enterprise), ue (Ultimate)
REM                             If not specified, will read from .eclipseproduct or prompt
REM   -v <version>              Product version (e.g., 25)
REM                             If not specified, will read from .eclipseproduct or prompt
REM
REM Examples:
REM   gen-license.bat                                       REM Interactive mode
REM   gen-license.bat "C:\Program Files\DBeaver"
REM   gen-license.bat "C:\Program Files\DBeaver\dbeaver.exe"
REM   gen-license.bat -t ee -v 24 "C:\Program Files\DBeaver"

REM Default values (empty means will be determined later)
set LICENSE_TYPE=
set VERSION=
set DBEAVER_PATH=

REM Parse arguments
:parse_args
if "%~1"=="" goto check_path
if /i "%~1"=="-h" goto show_help
if /i "%~1"=="--help" goto show_help

if /i "%~1"=="-t" (
    set LICENSE_TYPE=%~2
    shift
    shift
    goto parse_args
)

if /i "%~1"=="-v" (
    set VERSION=%~2
    shift
    shift
    goto parse_args
)

REM Check if argument starts with - (unknown option)
set arg=%~1
if "%arg:~0,1%"=="-" (
    echo Unknown option: %~1
    echo Use -h or --help for usage information
    exit /b 1
)

REM Otherwise, it's the DBeaver path
set DBEAVER_PATH=%~1
shift
goto parse_args

:show_help
echo Usage: %~nx0 [OPTIONS] [DBeaver_Path]
echo.
echo Arguments:
echo   DBeaver_Path              Path to DBeaver installation directory or executable (optional)
echo                             If not provided, will prompt for input
echo.
echo Options:
echo   -h, --help                Show this help message
echo   -t ^<type^>                 License type: le (Lite), ee (Enterprise), ue (Ultimate)
echo                             If not specified, will read from .eclipseproduct or prompt
echo   -v ^<version^>              Product version (e.g., 25)
echo                             If not specified, will read from .eclipseproduct or prompt
echo.
echo Examples:
echo   %~nx0                                       REM Interactive mode
echo   %~nx0 "C:\Program Files\DBeaver"
echo   %~nx0 "C:\Program Files\DBeaver\dbeaver.exe"
echo   %~nx0 -t ee -v 24 "C:\Program Files\DBeaver"
exit /b 0

:check_path
REM If DBeaver path is not provided, prompt for it
if "%DBEAVER_PATH%"=="" (
    echo ==========================================
    echo DBeaver License Generator
    echo ==========================================
    echo.
    echo Please enter DBeaver installation path:
    echo   - Directory: C:\Program Files\DBeaver
    echo   - Executable: C:\Program Files\DBeaver\dbeaver.exe
    echo.
    set /p DBEAVER_PATH="Path: "

    REM Remove quotes if present
    set DBEAVER_PATH=!DBEAVER_PATH:"=!

    if "!DBEAVER_PATH!"=="" (
        echo Error: No path provided
        exit /b 1
    )
)

REM Normalize path - if it's an executable, get the directory
set INSTALL_DIR=%DBEAVER_PATH%
if /i "%DBEAVER_PATH:~-4%"==".exe" (
    for %%F in ("%DBEAVER_PATH%") do set INSTALL_DIR=%%~dpF
    REM Remove trailing backslash
    set INSTALL_DIR=!INSTALL_DIR:~0,-1!
)

REM Determine plugins directory
set PLUGINS_DIR=%INSTALL_DIR%\plugins
set PRODUCT_FILE=%INSTALL_DIR%\.eclipseproduct

REM Check if plugins directory exists
if not exist "%PLUGINS_DIR%" (
    echo Error: Plugins directory not found: %PLUGINS_DIR%
    echo Please check the DBeaver installation path
    exit /b 1
)

REM Check if dbeaver-agent.jar exists
set AGENT_JAR=%PLUGINS_DIR%\dbeaver-agent.jar
if not exist "%AGENT_JAR%" (
    echo Error: dbeaver-agent.jar not found: %AGENT_JAR%
    echo Please deploy the agent first using onekey.py or manually
    exit /b 1
)

REM Read product information from .eclipseproduct if not specified
if "%LICENSE_TYPE%"=="" (
    if exist "%PRODUCT_FILE%" (
        echo Reading product information from .eclipseproduct...

        REM Read product ID to determine license type
        for /f "tokens=2 delims==" %%i in ('findstr "^id=" "%PRODUCT_FILE%"') do (
            set PRODUCT_ID=%%i
        )

        echo !PRODUCT_ID! | findstr /i "lite" >nul
        if !errorlevel! equ 0 set LICENSE_TYPE=le

        echo !PRODUCT_ID! | findstr /i "ultimate" >nul
        if !errorlevel! equ 0 set LICENSE_TYPE=ue

        echo !PRODUCT_ID! | findstr /i "enterprise" >nul
        if !errorlevel! equ 0 (
            if not "!LICENSE_TYPE!"=="ue" set LICENSE_TYPE=ee
        )

        if "!LICENSE_TYPE!"=="" (
            echo Warning: Could not determine license type from product ID: !PRODUCT_ID!
        )
    ) else (
        echo Warning: .eclipseproduct file not found: %PRODUCT_FILE%
    )
)

if "%VERSION%"=="" (
    if exist "%PRODUCT_FILE%" (
        REM Read version and extract major version
        for /f "tokens=2 delims==" %%i in ('findstr "^version=" "%PRODUCT_FILE%"') do (
            set FULL_VERSION=%%i
        )

        REM Extract major version (e.g., "25.2.0" -> "25")
        for /f "tokens=1 delims=." %%i in ("!FULL_VERSION!") do (
            set VERSION=%%i
        )
    )
)

REM Prompt for missing values
if "%LICENSE_TYPE%"=="" (
    echo.
    echo Please enter License Type:
    echo   - le: Lite Edition
    echo   - ee: Enterprise Edition
    echo   - ue: Ultimate Edition
    set /p LICENSE_TYPE="License Type (le/ee/ue): "

    if "!LICENSE_TYPE!"=="" (
        echo Error: License type is required
        exit /b 1
    )
)

if "%VERSION%"=="" (
    echo.
    set /p VERSION="Please enter Product Version (e.g., 25): "

    if "!VERSION!"=="" (
        echo Error: Version is required
        exit /b 1
    )
)

echo.
echo ==========================================
echo Generating DBeaver License
echo ==========================================
echo DBeaver Path: %DBEAVER_PATH%
echo Install Dir:  %INSTALL_DIR%
echo Plugins Dir:  %PLUGINS_DIR%
echo License Type: %LICENSE_TYPE%
echo Version:      %VERSION%
echo ==========================================
echo.

REM Change to plugins directory and run License generator
cd /d "%PLUGINS_DIR%" || exit /b 1

REM Run java command with all jars in plugins directory
java -cp "*" com.dbeaver.agent.License -t %LICENSE_TYPE% -v %VERSION%
