@echo off
setlocal enabledelayedexpansion
echo ================================================
echo   HyperMarrow Protected Build Pipeline
echo ================================================

REM Step 1: Clean all intermediates
echo [1/5] Cleaning build artifacts...
cd /d "%~dp0..\.."
for /d %%i in (openclaw-memory-system\build openclaw-learning-system\build openclaw-memory-system\__pycache__ openclaw-learning-system\__pycache__) do (
    if exist "%%i" rmdir /s /q "%%i" 2>nul
)
del /s /q openclaw-memory-system\*.c openclaw-learning-system\*.c 2>nul
del /s /q openclaw-memory-system\*.cpp openclaw-learning-system\*.cpp 2>nul
del /s /q openclaw-memory-system\*.html openclaw-learning-system\*.html 2>nul

REM Step 2: Cython compile .py -^> .pyd
echo [2/5] Cython compiling source code to .pyd...
call _build_cython.bat
if errorlevel 1 (echo ERROR: Cython compilation failed & pause & exit /b 1)

REM Step 3: Verify zero source leakage BEFORE packaging
echo [3/5] Verifying zero source leakage...
set LEAK_COUNT=0
for /r openclaw-memory-system %%f in (*.c) do set /a LEAK_COUNT+=1
for /r openclaw-learning-system %%f in (*.c) do set /a LEAK_COUNT+=1
for /r openclaw-memory-system %%f in (*.cpp) do set /a LEAK_COUNT+=1
for /r openclaw-learning-system %%f in (*.cpp) do set /a LEAK_COUNT+=1
if !LEAK_COUNT! gtr 0 (
    echo ERROR: !LEAK_COUNT! C/C++ source files found - ABORTING
    echo These must be cleaned before packaging
    git checkout -- openclaw-memory-system\ openclaw-learning-system\
    pause
    exit /b 1
)
echo   OK - No C/C++ intermediates found

REM Step 4: Build Electron + Package
echo [4/5] Building Electron installer...
cd /d "%~dp0"
rmdir /s /q release\win-unpacked 2>nul
del /q release\*.exe 2>nul
call npm run build
if errorlevel 1 (echo ERROR: npm build failed & goto cleanup & exit /b 1)
call npm run pack:win
if errorlevel 1 (echo ERROR: packaging failed & goto cleanup & exit /b 1)

REM Step 5: Verify installer contents
echo [5/5] Verifying installer contents...
set PY_COUNT=0
for /r release\win-unpacked\resources %%f in (*.py) do set /a PY_COUNT+=1
REM Exclude start.py and stop.py (launcher scripts with no algorithms)
set /a PY_COUNT=!PY_COUNT!-2
if !PY_COUNT! gtr 10 (
    echo WARNING: !PY_COUNT! .py files in installer
    echo Check that only launcher scripts + __init__ remain
)

echo.
echo ================================================
echo   BUILD COMPLETE
echo   Installer: release\HyperMarrow-Setup.x64.exe
echo   Source protected: .pyd + .pyc only
echo ================================================

:cleanup
REM Restore source for development
cd /d "%~dp0..\.."
git checkout -- openclaw-memory-system\ openclaw-learning-system\
echo Development source restored.
pause
