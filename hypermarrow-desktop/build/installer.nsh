!define LOGFILE "$TEMP\hypermarrow-install.log"
!macro _LOG msg
  FileOpen $9 "${LOGFILE}" a
  FileWrite $9 "[$\r$\n] ${msg}$\r$\n"
  FileClose $9
!macroend

!macro customInit
  !insertmacro _LOG "customInit: INSTDIR=$INSTDIR"
  nsExec::Exec 'taskkill /F /IM "智商藏不住.exe"'
  Pop $0
  nsExec::Exec 'taskkill /F /IM "python.exe"'
  Pop $0
  Sleep 3000

  ; Force-delete old uninstaller via cmd (NSIS Delete/Rename fail on locked files)
  ; If the uninstaller is gone, NSIS skips the "Failed to uninstall" step entirely
  nsExec::Exec 'cmd /c del /f /q "$INSTDIR\Uninstall 智商藏不住.exe" 2>nul'
  Pop $0
  !insertmacro _LOG "cmd del uninstaller exit=$0"
  ; Also try deleting with 8.3 short path as fallback
  nsExec::Exec 'cmd /c del /f /q "$INSTDIR\Uninst~1.exe" 2>nul'
  nsExec::Exec 'cmd /c del /f /q "$INSTDIR\Uninst~2.exe" 2>nul'

  ; Verify uninstaller is gone
  IfFileExists "$INSTDIR\Uninstall 智商藏不住.exe" 0 uninst_gone
    !insertmacro _LOG "WARNING: uninstaller still exists!"
    goto done
  uninst_gone:
    !insertmacro _LOG "Uninstaller successfully removed"
  done:
!macroend

!macro customCheckAppRunning
  nsExec::Exec 'taskkill /F /IM "智商藏不住.exe"'
  nsExec::Exec 'taskkill /F /IM "python.exe"'
  Sleep 2000
!macroend
