@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0..\.."

REM ── Read version from VERSION file (npm prebuild auto-bumps it) ──
set /p VERSION=<VERSION
if "%VERSION%"=="" set VERSION=0.0.0

REM Check for --split flag
set BUILD_MODE=full
if "%1"=="--split" set BUILD_MODE=split

echo ================================================
echo   HyperMarrow Protected Build Pipeline [%BUILD_MODE%] v%VERSION%
echo ================================================

REM Version auto-bumped by npm prebuild script; just read it
echo Building HyperMarrow v%VERSION%

REM Step 1: Clean
echo [1/6] Cleaning...
rmdir /s /q dist\pyd 2>nul
mkdir dist\pyd 2>nul
for /d %%i in (openclaw-memory-system\build_tmp openclaw-learning-system\build_tmp) do rmdir /s /q "%%i" 2>nul
for /r openclaw-memory-system %%f in (*.c *.cpp *.html) do del /q "%%f" 2>nul
for /r openclaw-learning-system %%f in (*.c *.cpp *.html) do del /q "%%f" 2>nul

REM Step 2: Setup embedded Python
echo [2/6] Setting up embedded Python...
rmdir /s /q dist\pyd\py310 2>nul
mkdir dist\pyd\py310
tar -xf C:\tmp\python-3.10.11-embed-amd64.zip -C dist\pyd\py310 2>nul || (
    powershell -Command "Expand-Archive -Path C:\tmp\python-3.10.11-embed-amd64.zip -DestinationPath dist\pyd\py310 -Force"
)
REM Enable site-packages
python -c "p=open('dist/pyd/py310/python310._pth','r').read();p=p.replace('#import site','import site');open('dist/pyd/py310/python310._pth','w').write(p+'\nLib\\\\site-packages\n')"
REM Install pip
dist\pyd\py310\python.exe C:\tmp\get-pip.py --no-warn-script-location 2>nul
mkdir dist\pyd\py310\Lib\site-packages 2>nul

if "%BUILD_MODE%"=="split" goto :build_split

REM ═══════════════════════════════════════════════════════════════════════════════
REM FULL BUILD: install all deps into embedded Python
REM ═══════════════════════════════════════════════════════════════════════════════
echo   [FULL] Installing all Python deps...
dist\pyd\py310\python.exe -m pip install --target dist\pyd\py310\Lib\site-packages --ignore-installed --no-cache-dir fastapi uvicorn chromadb sentence-transformers numpy torch pydantic --extra-index-url https://download.pytorch.org/whl/cpu -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn 2>nul
goto :cleanup_deps

:build_split
REM ═══════════════════════════════════════════════════════════════════════════════
REM SPLIT BUILD: base installer (core only) + engine zips for CDN
REM ═══════════════════════════════════════════════════════════════════════════════
echo   [SPLIT] Installing core deps only (fastapi, uvicorn, numpy, pydantic)...
dist\pyd\py310\python.exe -m pip install --target dist\pyd\py310\Lib\site-packages --ignore-installed --no-cache-dir fastapi uvicorn numpy pydantic -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn 2>nul
echo   Core deps installed

REM Build engine-vector.zip (chromadb + sentence-transformers + transitive deps)
echo   [SPLIT] Building engine-vector-%VERSION%.zip...
rmdir /s /q dist\pyd\engine-vector 2>nul
mkdir dist\pyd\engine-vector
dist\pyd\py310\python.exe -m pip install --target dist\pyd\engine-vector --ignore-installed --no-cache-dir chromadb sentence-transformers -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn 2>nul
REM Clean up unused transitive deps from engine package
rmdir /s /q dist\pyd\engine-vector\kubernetes 2>nul
for /d %%i in (dist\pyd\engine-vector\kubernetes-*) do rmdir /s /q "%%i" 2>nul
cd dist\pyd\engine-vector
powershell -Command "Compress-Archive -Path * -DestinationPath ..\engine-vector-%VERSION%.zip -Force"
cd ..\..\..

REM Build engine-neural.zip (torch CPU)
echo   [SPLIT] Building engine-neural-%VERSION%.zip...
rmdir /s /q dist\pyd\engine-neural 2>nul
mkdir dist\pyd\engine-neural
dist\pyd\py310\python.exe -m pip install --target dist\pyd\engine-neural --ignore-installed --no-cache-dir torch --extra-index-url https://download.pytorch.org/whl/cpu -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn 2>nul
cd dist\pyd\engine-neural
powershell -Command "Compress-Archive -Path * -DestinationPath ..\engine-neural-%VERSION%.zip -Force"
cd ..\..\..
echo   Engine zips built in dist/pyd/

:cleanup_deps
REM Cleanup unused transitive dependencies
if "%BUILD_MODE%"=="full" (
    echo   Cleaning up unused transitive deps...
    rmdir /s /q dist\pyd\py310\Lib\site-packages\kubernetes 2>nul
    for /d %%i in (dist\pyd\py310\Lib\site-packages\kubernetes-*) do rmdir /s /q "%%i" 2>nul
    echo   Unused deps cleaned (kubernetes)
)

REM Step 3: Cython compile
echo [3/6] Cython compiling...
call _build_cython.bat
if errorlevel 1 (echo ERROR & pause & exit /b 1)

REM Step 4: Verify Python deps survived Cython build
echo [4/6] Verifying Python deps...
if "%BUILD_MODE%"=="split" (
    REM Split mode: only verify core deps
    dist\pyd\py310\python.exe -c "import fastapi,uvicorn,numpy; print('Core deps OK')" 2>nul
    if errorlevel 1 (
        echo ERROR: Core Python deps broken after Cython build!
        pause & exit /b 1
    )
    echo   Core deps verified (engine modules will be downloaded on first use)
) else (
    REM Full mode: verify all deps
    dist\pyd\py310\python.exe -c "import fastapi,uvicorn,chromadb,numpy,torch; from sentence_transformers import SentenceTransformer; print('All deps OK')" 2>nul
    if errorlevel 1 (
        echo ERROR: Python deps broken after Cython build!
        pause & exit /b 1
    )
    REM Verify unwanted packages are gone
    for %%d in (kubernetes sympy sklearn) do (
        if exist dist\pyd\py310\Lib\site-packages\%%d (
            echo WARNING: %%d still present in site-packages
        )
    )
    echo   Deps verified OK
)

REM Step 5: Build Electron + Package
echo [5/6] Building Electron installer...
cd /d "%~dp0"
rmdir /s /q release 2>nul
REM Use npmmirror for electron-builder binaries (winCodeSign, NSIS) — avoids GitHub dependency
REM Cache to user-writable location so binaries survive between builds
set ELECTRON_BUILDER_BINARIES_MIRROR=https://npmmirror.com/mirrors/electron-builder-binaries/
set ELECTRON_BUILDER_CACHE=%APPDATA%\hypermarrow\electron-builder-cache
call npm run build
call npm run pack:win
if "%BUILD_MODE%"=="split" (
    REM Copy engine zips to release alongside the installer
    echo   Copying engine zips to release...
    copy /y ..\..\dist\pyd\engine-vector-%VERSION%.zip release\ 2>nul
    copy /y ..\..\dist\pyd\engine-neural-%VERSION%.zip release\ 2>nul
)
echo   Installer ready

REM Step 6: Verify output
echo [6/6] Verifying output...
cd /d "%~dp0..\.."
echo ================================================
echo BUILD COMPLETE [%BUILD_MODE%]
echo Installer: hypermarrow-desktop\release\智商藏不住-Setup-%VERSION%-win-x64.exe
if "%BUILD_MODE%"=="split" (
    echo Engine modules ^(upload to CDN^):
    echo   Vector:  hypermarrow-desktop\release\engine-vector-%VERSION%.zip
    echo   Neural:  hypermarrow-desktop\release\engine-neural-%VERSION%.zip
    echo CDN target: https://cdn.qianshi.cool/download/
)
echo ================================================
echo BUILD COMPLETE [%BUILD_MODE%]
echo Installer: hypermarrow-desktop\release\智商藏不住-Setup-%VERSION%-win-x64.exe
if "%BUILD_MODE%"=="split" (
    echo Engine modules ^(upload to CDN^):
    echo   Vector:  hypermarrow-desktop\release\engine-vector-%VERSION%.zip
    echo   Neural:  hypermarrow-desktop\release\engine-neural-%VERSION%.zip
    echo CDN target: https://cdn.qianshi.cool/download/
)
echo ================================================
pause
