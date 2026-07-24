; Kill app + Python before install/uninstall
!macro customCheckAppRunning
  nsExec::Exec 'taskkill /F /IM 智商藏不住.exe'
  nsExec::Exec 'taskkill /F /IM python.exe'
  Sleep 3000
!macroend
!macro customInit
  nsExec::Exec 'taskkill /F /IM 智商藏不住.exe'
  nsExec::Exec 'taskkill /F /IM python.exe'
  Sleep 2000
!macroend
