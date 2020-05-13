# =============================================================================
#     Code: main.py
#     Author: ENS Casey R. Densmore, 25JUN2019
#     
#     Purpose: Main (launcher) script for AXBT Realtime Editing System (ARES). 
# =============================================================================

#import and run splash screen
from sys import argv, exit

from platform import system as cursys

#add splash screen on Windows because of SLOW import speed due to drivers
if cursys() == 'Windows':
    
    #basic Qt5 bindings for app + splash screen
    from PySide2.QtWidgets import QApplication, QSplashScreen
    from PySide2.QtGui import QPixmap
    
    #making splash screen
    app = QApplication(argv)
    splash = QSplashScreen(QPixmap("qclib/dropicon.png"))
    splash.show()
    
    #Imports necessary for main program
    import ARESgui 
    
    #creates main program instance
    ex = ARESgui.RunProgram()
    
    #kill splash screen
    splash.close()
    
else:
    #Qt5 binding for app only
    from PySide2.QtWidgets import QApplication
        
    #Imports necessary for main program
    import ARESgui 
    
    #creates main program instance
    app = QApplication(argv)
    ex = ARESgui.RunProgram()
    

#executes main program (identical regardless of splash screen)
exit(app.exec_())
    
    