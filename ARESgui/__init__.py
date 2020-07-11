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
#   This module contains the class that generates the main window for ARES.
#   This file also calls functions from the following necessary files:
#           o autoqc.py: autoQC algorithm for temperature-depth profiles
#           o tropicfileinteraction.py: file reading/writing functions
#           o makeAXBTplots.py: Profile/location plot generation
#           o geoplotfunctions.py: Location plot formatting
#           o ocean_climatology_interaction.py: Interaction with climatology
#               and bathymetry datasets
#           o GPS_COM_interaction.py: Interaction with COM ports and NMEA feeds
#               to autopopulate drop location after each launch
#           o VHFsignalprocessor.py: Signal processing and temperature/depth
#               conversion equation functions, interface for interaction with
#               C++ based DLL file for WiNRADIO receivers, QRunnable thread
#               class to process AXBT data from radio receivers or audio files
#           o settingswindow.py: Separate settings GUI and slots necessary to
#               export updated settings to the main GUI
#

from PyQt5.QtWidgets import QMainWindow
from traceback import print_exc as trace_error

class RunProgram(QMainWindow):
    
    #importing methods from other files
    from ._DASfunctions import (makenewprocessortab, datasourcerefresh, datasourcechange, changefrequencytomatchchannel, changechanneltomatchfrequency, changechannelandfrequency, updatefftsettings, startprocessor, stopprocessor, gettabstrfromnum, triggerUI, updateUIinfo, updateUIfinal, failedWRmessage, updateaudioprogressbar, processprofile)
    from ._PEfunctions import (makenewproftab, selectdatafile, checkdatainputs_editorinput, continuetoqc, runqc, applychanges, updateprofeditplots, generateprofiledescription, addpoint, removepoint, removerange, on_press_spike, on_release, toggleclimooverlay, CustomToolbar)
    from ._GUIfunctions import (initUI, loaddata, buildmenu, configureGuiFont, changeGuiFont, openpreferencesthread, updatesettings, settingsclosed, updateGPSdata, updateGPSsettings)
    from ._globalfunctions import (addnewtab, whatTab, renametab, setnewtabcolor, closecurrenttab, savedataincurtab, postwarning, posterror, postwarning_option, closeEvent, parsestringinputs)
    
    
    # INITIALIZE WINDOW, INTERFACE
    def __init__(self):
        super().__init__()
        
        try:
            self.initUI() #creates GUI window
            self.buildmenu() #Creates interactive menu, options to create tabs and run ARES systems
            self.loaddata() #loads climo and bathy data into program first if using the full datasets
            self.makenewprocessortab() #Opens first tab

        except Exception:
            trace_error()
            self.posterror("Failed to initialize the program.")
            
            

    
    
