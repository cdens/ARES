# =============================================================================
#     Code: main.py
#     Author: ENS Casey R. Densmore, 25JUN2019
#     
#     Purpose: Main (launcher) script for AXBT Realtime Editing System (ARES). 
# =============================================================================

#import and run splash screen
from sys import argv, exit
from PyQt5.QtWidgets import QApplication, QSplashScreen
from PyQt5.QtGui import QPixmap
import time

app = QApplication(argv)
splash = QSplashScreen(QPixmap("qclib/dropicon.png"))
splash.show()

#Imports necessary for main program
import ARESgui 

#creates main program instance
app2 = QApplication(argv)
ex = ARESgui.RunProgram()

#kill splash screen
splash.close()

#executes main program
exit(app2.exec_())
    
    