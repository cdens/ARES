# =============================================================================
#     Code: main.py
#     Author: ENS Casey R. Densmore, 25JUN2019
#     
#     Purpose: Main (launcher) script for AXBT Realtime Editing System (ARES). 
# =============================================================================


#Import and run main program
from sys import argv, exit
from PyQt5.QtWidgets import QApplication
import ARESgui 

app = QApplication(argv)
ex = ARESgui.RunProgram()
exit(app.exec_())
    
    