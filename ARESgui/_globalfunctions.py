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
#   Globally Required Functions (used by other module subfiles)
#       o addnewtab: updates ARES tab-tracking system with information for new tab
#       o whatTab: gets identifier for open tab
#       o renametab: renames open tab
#       o setnewtabcolor: sets the background color pattern for new tabs
#       o closecurrenttab: closes open tab
#       o savedataincurtab: saves data in open tab (saved file types depend on tab type and user preferences)
#       o postwarning: posts a warning box specified message
#       o posterror: posts an error box with a specified message
#       o postwarning_option: posts a warning box with Okay/Cancel options
#       o closeEvent: pre-existing function that closes the GUI- function modified to prompt user with an "are you sure" box

from platform import system as cursys

global slash
if cursys() == 'Windows':
    slash = '\\'
else:
    slash = '/'

from os import remove, path, listdir
from traceback import print_exc as trace_error
from shutil import copy as shcopy

from PyQt5.QtWidgets import QApplication, QMessageBox, QFileDialog, QInputDialog
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPalette, QBrush, QLinearGradient

import time as timemodule
import datetime as dt
import numpy as np
import matplotlib.pyplot as plt

import qclib.tropicfileinteraction as tfio
import qclib.makeAXBTplots as tplot




    
# =============================================================================
#     TAB MANIPULATION OPTIONS, OTHER GENERAL FUNCTIONS
# =============================================================================

#handles tab indexing
def addnewtab(self):
    #creating numeric ID for newly opened tab
    self.totaltabs += 1
    self.tabnumbers.append(self.totaltabs)
    newtabnum = self.tabWidget.count()
    curtabstr = "Tab "+str(self.totaltabs) #pointable string for self.alltabdata dict
    return newtabnum,curtabstr
    
    

#gets index of open tab in GUI
def whatTab(self):
    ctabnum = self.tabWidget.currentIndex()
    if ctabnum == -1:
        return ctabnum
    else:
        return self.tabnumbers[ctabnum]
    
    

#renames tab (only user-visible name, not self.alltabdata dict key)
def renametab(self):
    try:
        curtab = self.tabWidget.currentIndex()
        name, ok = QInputDialog.getText(self, 'Rename Current Tab', 'Enter new tab name:',QLineEdit.Normal,str(self.tabWidget.tabText(curtab)))
        if ok:
            self.tabWidget.setTabText(curtab,name)
    except Exception:
        trace_error()
        self.posterror("Failed to rename the current tab")
        
        

#sets default color scheme for tabs
@staticmethod
def setnewtabcolor(tab):
    p = QPalette()
    gradient = QLinearGradient(0, 0, 0, 400)
    gradient.setColorAt(0.0, QColor(253,253,255))
    #gradient.setColorAt(1.0, QColor(248, 248, 255))
    gradient.setColorAt(1.0, QColor(225, 225, 255))
    p.setBrush(QPalette.Window, QBrush(gradient))
    tab.setAutoFillBackground(True)
    tab.setPalette(p)
    
    
        
#closes a tab
def closecurrenttab(self):
    try:
        reply = QMessageBox.question(self, 'Message',
            "Are you sure to close the current tab?", QMessageBox.Yes | 
            QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:

            #getting tab to close
            curtab = int(self.whatTab())
            curtabstr = "Tab " + str(curtab)
            indextoclose = self.tabWidget.currentIndex()
            
            #check to make sure there isn't a corresponding processor thread, close if there is
            if self.alltabdata[curtabstr]["tabtype"] == 'SignalProcessor_incomplete' or self.alltabdata[curtabstr]["tabtype"] == 'SignalProcessor_completed':
                if self.alltabdata[curtabstr]["isprocessing"]:
                    reply = QMessageBox.question(self, 'Message',
                        "Closing this tab will terminate the current profile and discard the data. Continue?", QMessageBox.Yes | 
                        QMessageBox.No, QMessageBox.No)
                    if reply == QMessageBox.No:
                        return
                    else:
                        self.alltabdata[curtabstr]["processor"].abort()

            #closing open figures in tab to prevent memory leak
            if self.alltabdata[curtabstr]["tabtype"] == "ProfileEditor":
                plt.close(self.alltabdata[curtabstr]["ProfFig"])
                plt.close(self.alltabdata[curtabstr]["LocFig"])

            elif self.alltabdata[curtabstr]["tabtype"] == 'SignalProcessor_incomplete' or self.alltabdata[curtabstr]["tabtype"] == 'SignalProcessor_completed':
                plt.close(self.alltabdata[curtabstr]["ProcessorFig"])

            #closing tab
            self.tabWidget.removeTab(indextoclose)

            #removing current tab data from the self.alltabdata dict, correcting tabnumbers variable
            self.alltabdata.pop("Tab "+str(curtab))
            self.tabnumbers.pop(indextoclose)

    except Exception:
        trace_error()
        self.posterror("Failed to close the current tab")
        
        
        
            
#save data in open tab        
def savedataincurtab(self):
    try:
        #getting directory to save files from QFileDialog
        try:
            outdir = str(QFileDialog.getExistingDirectory(self, "Select Directory to Save File(s)",self.defaultfilewritedir,QFileDialog.DontUseNativeDialog))
        except Exception:
            trace_error()
            return False
                            
        #checking directory validity
        if outdir == '':
            QApplication.restoreOverrideCursor()
            return False
        else:
            self.defaultfilewritedir = outdir
                            
    except:
        self.posterror("Error raised in directory selection")
        return

    try:
        QApplication.setOverrideCursor(Qt.WaitCursor)
        
        #pulling all relevant data
        curtabstr = "Tab " + str(self.whatTab())
        
        if self.alltabdata[curtabstr]["tabtype"] == "ProfileEditor":
            try:
                rawtemperature = self.alltabdata[curtabstr]["profdata"]["temp_raw"]
                rawdepth = self.alltabdata[curtabstr]["profdata"]["depth_raw"]
                climotempfill = self.alltabdata[curtabstr]["profdata"]["climotempfill"]
                climodepthfill = self.alltabdata[curtabstr]["profdata"]["climodepthfill"]
                temperature = self.alltabdata[curtabstr]["profdata"]["temp_plot"]
                depth = self.alltabdata[curtabstr]["profdata"]["depth_plot"]
                day = self.alltabdata[curtabstr]["profdata"]["day"]
                month = self.alltabdata[curtabstr]["profdata"]["month"]
                year = self.alltabdata[curtabstr]["profdata"]["year"]
                time = self.alltabdata[curtabstr]["profdata"]["time"]
                lat = self.alltabdata[curtabstr]["profdata"]["lat"]
                lon = self.alltabdata[curtabstr]["profdata"]["lon"]
                identifier = self.alltabdata[curtabstr]["profdata"]["ID"]
                num = 99 #placeholder- dont have drop number here currently!!
                
                dtg = str(year) + str(month).zfill(2) + str(day).zfill(2) + str(time).zfill(4)
                curtab = self.tabWidget.currentIndex()
                filename = self.tabWidget.tabText(curtab)
                
                if self.settingsdict["overlayclimo"]:
                    matchclimo = self.alltabdata[curtabstr]["profdata"]["matchclimo"]
                else:
                    matchclimo = 1

            except:
                self.posterror("Failed to retrieve profile information")
                QApplication.restoreOverrideCursor()
                return False

            if self.settingsdict["savefin"]:
                try:
                    depth1m = np.arange(0,np.floor(depth[-1]))
                    temperature1m = np.interp(depth1m,depth,temperature)
                    tfio.writefinfile(outdir + slash + filename + '.fin',temperature1m,depth1m,day,month,year,time,lat,lon,num)
                except Exception:
                    trace_error()
                    self.posterror("Failed to save FIN file")
            if self.settingsdict["savejjvv"]:
                isbtmstrike = self.alltabdata[curtabstr]["tabwidgets"]["isbottomstrike"].isChecked()
                try:
                    tfio.writejjvvfile(outdir + slash + filename + '.jjvv',temperature,depth,day,month,year,time,lat,lon,identifier,isbtmstrike)
                except Exception:
                    trace_error()
                    self.posterror("Failed to save JJVV file")
            if self.settingsdict["savebufr"]:
                try:
                    tfio.writebufrfile(outdir + slash + filename + '.bufr',temperature,depth,year,month,day,time,lon,lat,identifier,self.settingsdict["originatingcenter"],False,b'\0')
                except Exception:
                    trace_error()
                    self.posterror("Failed to save BUFR file")
            if self.settingsdict["saveprof"]:
                try:
                    fig1 = plt.figure()
                    fig1.clear()
                    ax1 = fig1.add_axes([0.1,0.1,0.85,0.85])
                    climohandle = tplot.makeprofileplot(ax1,rawtemperature,rawdepth,temperature,depth,climotempfill,climodepthfill,dtg,matchclimo)
                    if self.settingsdict["overlayclimo"] == 0:
                        climohandle.set_visible(False)
                    fig1.savefig(outdir + slash + filename + '_prof.png',format='png')
                except Exception:
                    trace_error()
                    self.posterror("Failed to save profile image")
                finally:
                    plt.close('fig1')

            if self.settingsdict["saveloc"]:
                try:
                    fig2 = plt.figure()
                    fig2.clear()
                    ax2 = fig2.add_axes([0.1,0.1,0.85,0.85])
                    _,exportlat,exportlon,exportrelief = oci.getoceandepth(lat,lon,6,self.bathymetrydata)
                    tplot.makelocationplot(fig2,ax2,lat,lon,dtg,exportlon,exportlat,exportrelief,6)
                    fig2.savefig(outdir + slash + filename + '_loc.png',format='png')
                except Exception:
                    trace_error()
                    self.posterror("Failed to save location image")
                finally:
                    plt.close('fig2')

                
        elif self.alltabdata[curtabstr]["tabtype"] == "SignalProcessor_completed":
            
            if self.alltabdata[curtabstr]["isprocessing"]:
                self.postwarning('You must stop processing the current tab before saving data!')

            else:

                try:
                    #pulling prof data
                    rawtemperature = self.alltabdata[curtabstr]["rawdata"]["temperature"]
                    rawdepth = self.alltabdata[curtabstr]["rawdata"]["depth"]
                    frequency = self.alltabdata[curtabstr]["rawdata"]["frequency"]
                    timefromstart = self.alltabdata[curtabstr]["rawdata"]["time"]

                    #pulling profile metadata if necessary
                    try:
                        lat = self.alltabdata[curtabstr]["rawdata"]["lat"]
                        lon = self.alltabdata[curtabstr]["rawdata"]["lon"]
                        year = self.alltabdata[curtabstr]["rawdata"]["year"]
                        month = self.alltabdata[curtabstr]["rawdata"]["month"]
                        day = self.alltabdata[curtabstr]["rawdata"]["day"]
                        time = self.alltabdata[curtabstr]["rawdata"]["droptime"]
                        hour = self.alltabdata[curtabstr]["rawdata"]["hour"]
                        minute = self.alltabdata[curtabstr]["rawdata"]["minute"]
                    except:
                        # pulling data from inputs
                        latstr = self.alltabdata[curtabstr]["tabwidgets"]["latedit"].text()
                        lonstr = self.alltabdata[curtabstr]["tabwidgets"]["lonedit"].text()
                        profdatestr = self.alltabdata[curtabstr]["tabwidgets"]["dateedit"].text()
                        timestr = self.alltabdata[curtabstr]["tabwidgets"]["timeedit"].text()

                        #only checks validity of necessary data
                        try:
                            if self.settingsdict["saveedf"]:
                                lat, lon, year, month, day, time, hour, minute, _ = self.parsestringinputs(latstr, lonstr,profdatestr,timestr, 'omit', True, True, False)
                            else:
                                _, _, year, month, day, time, hour, minute, _ = self.parsestringinputs(latstr, lonstr,profdatestr,timestr, 'omit', False, True, False)
                        except:
                            self.postwarning("Failed to save raw data files!")
                            QApplication.restoreOverrideCursor()
                            return False

                    #date and time strings for LOG file
                    initdatestr = str(year) + '/' + str(month).zfill(2) + '/' + str(day).zfill(2)
                    inittimestr = str(hour).zfill(2) + ':' + str(minute).zfill(2) + ':00'
                    
                    filename = str(year) + str(month).zfill(2) + str(day).zfill(2) + str(time).zfill(4)

                except Exception:
                    trace_error()
                    self.posterror("Failed to pull raw profile data")
                    QApplication.restoreOverrideCursor()
                    return False
                
                if self.settingsdict["savelog"]:
                    try:
                        tfio.writelogfile(outdir + slash + filename + '.DTA',initdatestr,inittimestr,timefromstart,rawdepth,frequency,rawtemperature)
                    except Exception:
                        trace_error()
                        self.posterror("Failed to save LOG file")
                if self.settingsdict["saveedf"]:
                    try:
                        # noinspection PyUnboundLocalVariable
                        tfio.writeedffile(outdir + slash + filename + '.edf',rawtemperature,rawdepth,year,month,day,hour,minute,0,lat,lon) #lat/lon only parsed if self.settingsdict["saveedf"] is True
                    except Exception:
                        trace_error()
                        self.posterror("Failed to save EDF file")

                if self.settingsdict["savewav"]:
                    try:
                        oldfile = self.tempdir + slash + 'tempwav_' + str(self.alltabdata[curtabstr]["tabnum"]) + '.WAV'
                        newfile = outdir + slash + filename + '.WAV'

                        if path.exists(newfile):
                            remove(newfile)

                        shcopy(oldfile,newfile)
                    except Exception:
                        trace_error()
                        self.posterror("Failed to save WAV file")

                if self.settingsdict["savesig"]:
                    try:
                        oldfile = self.tempdir + slash + 'sigdata_' + str(self.alltabdata[curtabstr]["tabnum"]) + '.txt'
                        newfile = outdir + slash + filename + '.sigdata'

                        if path.exists(newfile):
                            remove(newfile)

                        shcopy(oldfile, newfile)
                    except Exception:
                        trace_error()

        else:
            self.postwarning('You must process a profile before attempting to save data!')
            
    except Exception:
        trace_error() #if something else in the file save code broke
        self.posterror("Filed to save files")
        QApplication.restoreOverrideCursor()
        return False
    finally:
        QApplication.restoreOverrideCursor()
        return True
    
        
        
#warning message
@staticmethod
def postwarning(warningtext):
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Warning)
    msg.setText(warningtext)
    msg.setWindowTitle("Warning")
    msg.setStandardButtons(QMessageBox.Ok)
    msg.exec_()
    
    
    
#error message
@staticmethod
def posterror(errortext):
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Critical)
    msg.setText(errortext)
    msg.setWindowTitle("Error")
    msg.setStandardButtons(QMessageBox.Ok)
    msg.exec_()
    
    

#warning message with options (Okay or Cancel)
@staticmethod
def postwarning_option(warningtext):
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Warning)
    msg.setText(warningtext)
    msg.setWindowTitle("Warning")
    msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
    outval = msg.exec_()
    option = 'unknown'
    if outval == 1024:
        option = 'okay'
    elif outval == 4194304:
        option = 'cancel'
    return option

    
    
#add warning message before closing GUI
def closeEvent(self, event):
    reply = QMessageBox.question(self, 'Message',
        "Are you sure to close the application? \n All unsaved work will be lost!", QMessageBox.Yes | 
        QMessageBox.No, QMessageBox.No)
    if reply == QMessageBox.Yes:

        if self.preferencesopened:
            self.settingsthread.close()

        #explicitly closing figures to clean up memory (should be redundant here but just in case)
        for curtabstr in self.alltabdata:
            if self.alltabdata[curtabstr]["tabtype"] == "ProfileEditor":
                plt.close(self.alltabdata[curtabstr]["ProfFig"])
                plt.close(self.alltabdata[curtabstr]["LocFig"])

            elif self.alltabdata[curtabstr]["tabtype"] == 'SignalProcessor_incomplete' or self.alltabdata[curtabstr]["tabtype"] == 'SignalProcessor_completed':
                plt.close(self.alltabdata[curtabstr]["ProcessorFig"])

                #aborting all threads
                if self.alltabdata[curtabstr]["isprocessing"]:
                    self.alltabdata[curtabstr]["processor"].abort()

        event.accept()
        # delete all temporary files
        allfilesanddirs = listdir(self.tempdir)
        for cfile in allfilesanddirs:
            if len(cfile) >= 5:
                cfilestart = cfile[:4]
                cfileext = cfile[-3:]
                if (cfilestart.lower() == 'temp' and cfileext.lower() == 'wav') or (cfilestart.lower() == 'sigd' and cfileext.lower() == 'txt'):
                    remove(self.tempdir + slash + cfile)
    else:
        event.ignore() 

        
        

# =============================================================================
#    PARSE STRING INPUTS/CHECK VALIDITY WHEN TRANSITIONING TO PROFILE EDITOR
# =============================================================================
def parsestringinputs(self,latstr,lonstr,profdatestr,timestr,identifier,checkcoords,checktime, checkid):
    try:
        #parsing and checking data
        if checkcoords:
            try:
                #checking latitude validity
                latstr = latstr.split(',')
                latsign = np.sign(float(latstr[0]))
                if len(latstr) == 3:
                    lat = float(latstr[0]) + latsign*float(latstr[1])/60 + latsign*float(latstr[2])/3600
                elif len(latstr) == 2:
                    lat = float(latstr[0]) + latsign*float(latstr[1])/60
                else:
                    lat = float(latstr[0])
            except:
                self.postwarning('Invalid Latitude Entered!')
                return

            try:
                #checking longitude validity
                lonstr = lonstr.split(',')
                lonsign = np.sign(float(lonstr[0]))
                if len(lonstr) == 3:
                    lon = float(lonstr[0]) + lonsign*float(lonstr[1])/60 + lonsign*float(lonstr[2])/3600
                elif len(lonstr) == 2:
                    lon = float(lonstr[0]) + lonsign*float(lonstr[1])/60
                else:
                    lon = float(lonstr[0])
            except:
                self.postwarning('Invalid Longitude Entered!')
                return

            if lon < -180 or lon > 180:
                self.postwarning('Longitude must be between -180 and 180')
            elif lat < -90 or lat > 90:
                self.postwarning('Latitude must be between -90 and 90')

            lon = round(lon,3)
            lat = round(lat,3)

        else:
            lon = np.NaN
            lat = np.NaN


        if checktime: #checking time
            if len(timestr) != 4:
                self.postwarning('Invalid Time Format!')
                return
            elif len(profdatestr) != 8:
                self.postwarning('Invalid Date Format!')
                return

            try: #checking date
                year = int(profdatestr[:4])
                month = int(profdatestr[4:6])
                day = int(profdatestr[6:])
            except:
                self.postwarning('Invalid Date Entered!')
                return
            try:
                time = int(timestr)
                hour = int(timestr[:2])
                minute = int(timestr[2:4])
            except:
                self.postwarning('Invalid Time Entered!')
                return

            if year < 1938: #year the bathythermograph was invented
                self.postwarning('Invalid Year Entered (< 1938 AD)!')
                return
            elif month == 0 or month > 12:
                self.postwarning("Invalid Month Entered (must be between 1 and 12)")
                return
            elif day == 0 or day > 31:
                self.postwarning("Invalid Day Entered (must be between 1 and 31")
                return
            elif hour > 23 or hour < 0:
                self.postwarning('Invalid Time Entered (hour must be between 0 and 23')
                return
            elif minute >= 60:
                self.postwarning('Invalid Time Entered (minutes must be < 60')
                return

            #making sure the profile is within 12 hours and not in the future, warning if otherwise
            curtime = timemodule.gmtime()
            deltat = dt.datetime(curtime[0],curtime[1],curtime[2],curtime[3],curtime[4],curtime[5]) - dt.datetime(year,month,day,hour,minute,0)
            option = ''
            if self.settingsdict["dtgwarn"]:
                if deltat.days < 0:
                    option = self.postwarning_option("Drop time appears to be after the current time. Continue anyways?")
                elif deltat.days > 1 or (deltat.days == 0 and deltat.seconds > 12*3600):
                    option = self.postwarning_option("Drop time appears to be more than 12 hours ago. Continue anyways?")
                if option == 'cancel':
                    return
        else:
            year = np.NaN
            month = np.NaN
            day = np.NaN
            time = np.NaN
            hour = np.NaN
            minute = np.NaN

        #check length of identifier
        if checkid and len(identifier) != 5:
            option = self.postwarning_option("Identifier is not 5 characters! Continue anyways?")
            if option == 'cancel':
                return

        return lat,lon,year,month,day,time,hour,minute,identifier
    except Exception:
        trace_error()
        self.posterror("Unspecified error in reading profile information!")
        return
            