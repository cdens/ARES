from traceback import print_exc as trace_error
import numpy as np
from os import remove, path

from PyQt5.QtWidgets import (QMainWindow, QLabel, QSpinBox, QDoubleSpinBox, QCheckBox, QPushButton,
    QMessageBox, QWidget, QTabWidget, QGridLayout, QSlider, QComboBox, QLineEdit)
from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal, QObject
from PyQt5.QtGui import QIcon, QColor, QPalette, QBrush, QLinearGradient, QFont

import qclib.GPS_COM_interaction as gps
import qclib.VHFsignalprocessor as vsp #for temperature conversion for flims

from platform import system as cursys
if cursys() == 'Windows':
    from ctypes import windll

import qclib.tropicfileinteraction as tfio
from pykml import parser
from pykml.factory import KML_ElementMaker as kml
import lxml
import matplotlib.pyplot as plt
from matplotlib import cm
import qclib.ocean_climatology_interaction as oci
import qclib.tropicfileinteraction as tfio
import qclib.makeAXBTplots as tplot
import shutil
from os import path, mkdir, listdir
from ._globalfunctions import (addnewtab, whatTab, renametab, setnewtabcolor, closecurrenttab, savedataincurtab, postwarning, posterror, postwarning_option, closeEvent, parsestringinputs)



#   DEFINE CLASS FOR SETTINGS (TO BE CALLED IN THREAD)
class RunExport(QMainWindow):

    # =============================================================================
    #   INITIALIZE WINDOW, INTERFACE
    # =============================================================================
    def __init__(self, export_info, missiondir, slash, bathymetrydata):
        super().__init__()

        try:
            self.missiondir = missiondir
            self.exportinfo = export_info
            self.slash = slash
            self.bathymetrydata = bathymetrydata
            self.initUI()
        except Exception:
            trace_error()
            self.posterror("Failed to initialize the export menu.")


    def initUI(self):
        
        self.signals = ExportSignals()

        # setting title/icon, background color
        self.setWindowTitle('AXBT Realtime Editing Export Data')
        self.setWindowIcon(QIcon('qclib/dropicon.png'))
        p = self.palette()
        p.setColor(self.backgroundRole(), QColor(255, 255, 255))
        self.setPalette(p)

        myappid = 'ARES_v1.0'  # arbitrary string
        if cursys() == 'Windows':
            windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

        # changing font size
        font = QFont()
        font.setPointSize(11)
        font.setFamily("Arial")
        self.setFont(font)

        # prepping to include tabs
        self.mainWidget = QWidget()
        self.setCentralWidget(self.mainWidget)
        self.mainLayout = QGridLayout()
        self.mainWidget.setLayout(self.mainLayout)
        
        #create the labels
        for i in range(len(self.exportinfo['unique files'])):
            widget = QLabel(self.exportinfo['unique files'][i], self.mainWidget)
            self.mainLayout.addWidget(widget, i + 1, 0, 1, 1)
        
        self.kml_checkbuttons = []
        #create the kml column
        if self.exportinfo['genkml'] == True:
            #create the kml column label
            widget = QLabel('Include\nKML?')
            self.mainLayout.addWidget(widget, 0, 1, 1, 1)
            for i in range(len(self.exportinfo['unique files'])):
                widget = QCheckBox(' ', self.mainWidget)
                widget.setChecked(True)
                self.mainLayout.addWidget(widget, i + 1, 1, 1, 1)
                self.kml_checkbuttons.append(widget)
        
        self.prof_checkbuttons = []
        #create the kml column
        if self.exportinfo['genprofplot'] == True:
            #create the kml column label
            widget = QLabel('Include in\nProfile Plot?')
            self.mainLayout.addWidget(widget, 0, 2, 1, 1)
            for i in range(len(self.exportinfo['unique files'])):
                widget = QCheckBox(' ', self.mainWidget)
                widget.setChecked(True)
                self.mainLayout.addWidget(widget, i + 1, 2, 1, 1)
                
                self.prof_checkbuttons.append(widget)
        
        self.pos_checkbuttons = []
        #create the kml column
        if self.exportinfo['genposplot'] == True:
            #create the kml column label
            widget = QLabel('Include in\nPosition Plot?')
            self.mainLayout.addWidget(widget, 0, 3, 1, 1)
            for i in range(len(self.exportinfo['unique files'])):
                widget = QCheckBox(' ', self.mainWidget)
                widget.setChecked(True)
                self.mainLayout.addWidget(widget, i + 1, 3, 1, 1)
                self.pos_checkbuttons.append(widget)

        self.jjvv_checkbuttons = []
        #create the kml column
        if self.exportinfo['catjjvv'] == True:
            #create the kml column label
            widget = QLabel('Include\n in JJVV?')
            self.mainLayout.addWidget(widget, 0, 4, 1, 1)
            for i in range(len(self.exportinfo['unique files'])):
                widget = QCheckBox(' ', self.mainWidget)
                widget.setChecked(True)
                self.mainLayout.addWidget(widget, i + 1, 4, 1, 1)
                self.jjvv_checkbuttons.append(widget)
        
        #create the export button
        self.exportbutton = QPushButton('Export')
        self.exportbutton.clicked.connect(self.exportfiles)
        self.mainLayout.addWidget(self.exportbutton, len(self.exportinfo['unique files']) + 1, 0, 1, 4)
        
        self.show()
        return 

    def exportfiles(self):
        try:
            if self.exportinfo['genkml'] == True:
                self.exportkml()
            if self.exportinfo['catjjvv'] == True:
                self.concatjvv()
            if self.exportinfo['genprofplot'] == True:
                self.genprofplot()
            if self.exportinfo['genposplot'] == True:
                self.genposplot()
            if self.exportinfo['organizefiles'] == True:
                self.organize_files()
        except Exception:
            trace_error()
            self.posterror('File mismatch. Ensure that all files are named based off the same time')
        return
    
    def exportkml(self):
        #get the applicable files based on whether or not they are checked
        files = []
        for i in range(len(self.exportinfo['unique files'])):
            if self.kml_checkbuttons[i].isChecked() == True:
                files.append(self.exportinfo['unique files'][i])
        #add the full path and fin file extension to the filename
        filepaths = []
        for i in range(len(files)):
            filepaths.append(f'{self.missiondir}/{files[i]}.fin')
        
        #loop through the files
        kml_points = []
        for i in range(len(filepaths)):
            #read the fin file
            info = tfio.readfinfile(filepaths[i])

            lat = info[6]
            lon = info[7]
            coordstring = f'{lon} {lat}'
            name = str(files[i])
            
            plm = kml.Placemark(kml.name(name), kml.Point(kml.coordinates(coordstring)))
            kml_points.append(plm)
        
        folder = kml.Folder(*kml_points)
        
        #get the folder string
        folder_string = lxml.etree.tostring(folder, pretty_print = True)
        
        kmlfile = f'{self.missiondir}/drop_coordinates.kml'
        #write the file
        with open(kmlfile, 'wb') as file:
            file.write(folder_string)
        
        return 
    
    def concatjvv(self):
        #get the applicable files based on whether or not they are checked
        files = []
        for i in range(len(self.exportinfo['unique files'])):
            if self.kml_checkbuttons[i].isChecked() == True:
                files.append(self.exportinfo['unique files'][i])
        #add the full path and jjvv file extension to the name
        filepaths = []
        for i in range(len(files)):
            filepaths.append(f'{self.missiondir}/{files[i]}.jjvv')
        jjvvconcatfile = f'{self.missiondir}{self.slash}mission_axbt_drops.jjvv'
        
        with open(f'{jjvvconcatfile}',"w") as f_out:
            f_out.write("UNCLASSIFIED\n\nDATA distribution STATEMENT A: PUBLIC DOMAIN\\\n\n")
            for file in filepaths:
                with open(f'{file}') as f_in:
                    f_out.write(f_in.read().strip() + "\n\n")
            
    def genprofplot(self):
        try:
            header = f'{self.missiondir}{self.slash}mission_'
            
            #get the applicable files based on whether or not they are checked
            files = []
            for i in range(len(self.exportinfo['unique files'])):
                if self.kml_checkbuttons[i].isChecked() == True:
                    files.append(self.exportinfo['unique files'][i])
            #add the full path and fin file extension to the name
            filepaths = []
            for i in range(len(files)):
                filepaths.append(f'{self.missiondir}{self.slash}{files[i]}.fin')
            
            alltemps = []
            alldepths = []
            alldtgs = []
            
            for file in filepaths:
                [temp,depth,day,month,year,time,lat,lon,_] = tfio.readfinfile(file)
                alltemps.append(temp)
                alldepths.append(depth)
                alldtgs.append(f"{year:04d}{month:02d}{day:02d}{time:04d}")
            
            
            #multi-profile plot
            if len(alltemps) > 0:
                figprof, axprof = plt.subplots()
                
                if len(alltemps) >= 17: #only show ddhhmm in legend, make 2 columns
                    manydrops = True
                else:
                    manydrops = False
                    
                colors = cm.get_cmap("brg",len(alltemps))
                
                i = 0
                for temp,depth,dtg in zip(alltemps,alldepths,alldtgs):
                    if manydrops:
                        dtg = dtg[-6:]
                    i += 1
                    axprof.plot(temp,depth, label=dtg, color=colors(i)[:3]) 
                    
                axprof.set_xlabel('Temperature ($^\circ$C)')
                axprof.set_ylabel('Depth (m)')
                if manydrops:
                    axprof.legend(ncol=2)
                else:
                    axprof.legend()
                axprof.grid()
                axprof.set_xlim([-3,32])
                axprof.set_ylim([-5,1000])
                axprof.set_yticks([0,100,200,400,600,800,1000])
                axprof.set_yticklabels([0,100,200,400,600,800,1000])
                axprof.invert_yaxis()
                
                figprof.savefig(header + "_profileplot.png")
            
        except:
            trace_error()
            self.posterror("Error raised in mission profile/location plot generation")
    
    def genposplot(self):
        header = f'{self.missiondir}{self.slash}mission_'
        
        #get the applicable files based on whether or not they are checked
        files = []
        for i in range(len(self.exportinfo['unique files'])):
            if self.kml_checkbuttons[i].isChecked() == True:
                files.append(self.exportinfo['unique files'][i])
        #add the full path and fin file extension to the name
        filepaths = []
        for i in range(len(files)):
            filepaths.append(f'{self.missiondir}{self.slash}{files[i]}.fin')
        
        alltemps = []
        alldepths = []
        alldtgs = []
        alllats = []
        alllons = []
        
        for file in filepaths:
            [temp,depth,day,month,year,time,lat,lon,_] = tfio.readfinfile(file)
            alltemps.append(temp)
            alldepths.append(depth)
            alldtgs.append(f"{year:04d}{month:02d}{day:02d}{time:04d}")
            alllats.append(lat)
            alllons.append(lon)
        
        #location plot
        if len(alltemps) > 0:
            figpos = plt.figure()
            figpos.clear()
            axpos = figpos.add_axes([0.1,0.1,0.85,0.85])
            
            _,exportlat,exportlon,exportrelief = oci.getoceandepth(alllats[0],alllons[0],10,self.bathymetrydata)
            tplot.makelocationplot(figpos,axpos,alllats,alllons,_,exportlon,exportlat,exportrelief,6)
            
            figpos.savefig(header + "_locationplot.png")
    
    def organize_files(self):
        filetypes = ["DTA","EDF","WAV","SIGDATA","FIN","BUFR","JJVV","PNG"] #MUST be upper-case (files to move)
        all_files = [f for f in listdir(self.missiondir) if path.isfile(self.missiondir + self.slash + f)] #getting list of files only in mission dir (non-recursive)            
        for file in all_files:
            if file[:7].lower() != "mission" and file[0] not in ['.','_']: #if filename starts with mission, it isn't for a specific drop and shouldn't be moved
                for ftype in filetypes:
                    cl = len(ftype)
                    if file[-cl:].upper() == ftype:
                        fdir = self.missiondir + self.slash + ftype
                        if not path.exists(fdir): #creating directory if necessary
                            mkdir(fdir)
                        shutil.move(self.missiondir + self.slash + file, fdir + self.slash + file) #moving file
    
    
    def closeEvent(self, event):
        event.accept()
        self.signals.exportclosed.emit(True)
    
    @staticmethod
    def posterror(errortext):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText(errortext)
        msg.setWindowTitle("Error")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

# SIGNAL SETUP HERE
class ExportSignals(QObject):
    exportclosed = pyqtSignal(bool)