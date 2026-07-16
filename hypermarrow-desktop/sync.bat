@echo off
chcp 65001 >nul
set APPDIR=release\win-unpacked\resources
set ASAR=%APPDIR%\app.asar
set TMPDIR=%APPDIR%\app_tmp

echo ── Extracting app.asar...
if exist "%TMPDIR%" rmdir /s /q "%TMPDIR%"
npx asar extract "%ASAR%" "%TMPDIR%"

echo ── Syncing source files...
xcopy /E /Y /Q "dist\*" "%TMPDIR%\dist\" >nul
xcopy /E /Y /Q "src\renderer\*" "%TMPDIR%\src\renderer\" >nul
copy /Y "package.json" "%TMPDIR%\" >nul

echo ── Repacking app.asar...
del "%ASAR%"
npx asar pack "%TMPDIR%" "%ASAR%"
rmdir /s /q "%TMPDIR%"

echo ── Done! Run release\win-unpacked\"智商藏不住.exe" to test.
