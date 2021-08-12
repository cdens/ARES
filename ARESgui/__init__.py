#     Code: ARESgui
#     Author: ENS Casey R. Densmore, 25JUN2019
#     
#     Purpose: GUI script for AXBT Realtime Editing System (ARES). See README 
#       for program overview, external dependencies and additional information. 
#
#    This file is part of the AXBT Realtime Editing System (ARES).
#
#    ARES is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    ARES is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with ARES.  If not, see <https://www.gnu.org/licenses/>.
#


from PyQt5.QtWidgets import QMainWindow
from traceback import print_exc as trace_error

class RunProgram(QMainWindow):
    
    #importing methods from other files
    from ._DASfunctions import (makenewprocessortab, datasourcerefresh, datasourcechange, changefrequencytomatchchannel, changechanneltomatchfrequency, changechannelandfrequency, updatefftsettings, startprocessor, prepprocessor, runprocessor, stopprocessor, gettabstrfromnum, triggerUI, updateUIinfo, updateUIfinal, failedWRmessage, updateaudioprogressbar, AudioWindow, AudioWindowSignals, audioWindowClosed, processprofile)
    from ._PEfunctions import (makenewproftab, selectdatafile, checkdatainputs_editorinput, continuetoqc, runqc, applychanges, updateprofeditplots, generateprofiledescription, addpoint, removepoint, removerange, on_press_spike, on_release, toggleclimooverlay, CustomToolbar)
    from ._MissionPlotter import (makenewMissiontab, plotMapAxes, updateMissionPlot, updateMissionPosition, updateMissionPlot_line, updateMissionPlot_circle, updateMissionPlot_box, getPoint, mouse_move)
    from ._GUIfunctions import (initUI, loaddata, buildmenu, configureGuiFont, changeGuiFont, openpreferencesthread, updatesettings, settingsclosed, updateGPSdata, updateGPSsettings)
    from ._globalfunctions import (addnewtab, whatTab, renametab, add_asterisk, remove_asterisk, setnewtabcolor, closecurrenttab, savedataincurtab, check_filename, postwarning, posterror, postwarning_option, closeEvent, parsestringinputs)
    
    
    # INITIALIZE WINDOW, INTERFACE
    def __init__(self):
        super().__init__()
        
        try:
            self.initUI() #creates GUI window
            self.buildmenu() #Creates interactive menu, options to create tabs and run ARES systems
            self.loaddata() #loads climo and bathy data into program first if using the full datasets
            self.makenewprocessortab() # opens a data acquisition tab on startup
            
        except Exception:
            trace_error()
            self.posterror("Failed to initialize the program.")
            
            

    
    
