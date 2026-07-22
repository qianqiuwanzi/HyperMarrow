; Kill app + Python before install/uninstall
!macro customCheckAppRunning
  nsExec::ExecToLog 'cmd /c taskkill /f /im 智商藏不住.exe 2>nul'
  nsExec::ExecToLog 'cmd /c taskkill /f /im python.exe 2>nul'
  Sleep 2500
!macroend
!macro customInit
  nsExec::ExecToLog 'cmd /c taskkill /f /im 智商藏不住.exe 2>nul'
  nsExec::ExecToLog 'cmd /c taskkill /f /im python.exe 2>nul'
  Sleep 1500
!macroend
