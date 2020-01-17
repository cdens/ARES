# **AXBT Realtime Editing System (ARES)**


**Authors: Casey Densmore (cdensmore101@gmail.com) and Matt Kuhn**

![Icon](qclib/dropicon.png)

Table of Contents
=================
  * [Overview](#overview)
    * [Bash](#bash)
    * [Fish](#fish)
    * [DevIcons](#devicons-optional)
    * [Manual Install](#alternatively)
  * [Signal Processor](#signal-processor-capabilities)
  * [Profile Editor](#profile-editor-capabilities)
    * [Profile Editing Tools](#profile-editing-tools)
    * [Profile Viewing Tools](#profile-viewing-tools)
    * [Profile Flagging Tools](#profile-flagging-tools)
  * [Additional Information](#nolink)
    * [Required Datasets](#python)
    * [Radio Reciever Interaction](#switching-between-buffers)
    * [Platform Support](#toggle-relative-numbering)
    * [Python Requirements](#comfortable-motion-scrolling)


## Overview
This program is designed to enable processing and editing of ocean AXBT-generated temperature
vs. depth profiles in a single program. Multiple profiles can be received (limited by the 
number of receivers connected) and edited simultaneously in different tabs. The profile
editor runs and automated quality control algorithm to correct profile deficiencies without
any operator input. However, unusual discrepancies may be missed by this algorithm and thus
require operator review to remove. In addition to receiving VHF data, this program is capable
of reading raw audio files or raw ASCII AXBT data files. The autoQC algorithm and user input
in the profile editor are both guided by ocean climatology and bathymetry data (datasets
listed below). 


## Signal Processor Capabilities
The WiNRADIO signal processor tab can be opened either from the file menu
or by typing CTRL+N. The dropdown menu allows the user to select the data source:
either a connected receiver (all detected receivers will be listed by serial number),
a raw audio file (currently only WAV files are supported) or a test dataset. Select 
"START" to begin processing, and "STOP" to terminate. Corresponding drop information
can be entered in the right column. Date and time are autopopulated for when "START" 
is selected if a connected WiNRADIO receiver (not "Test" or "Audio") is the selected
data source. This option can be suppressed in "Signal Processor Preferences". Upon
collecting all data and entering the relevant information, selecting "Process Profile"
will first open a prompt to save the raw data files (currently .DTA and .edf are supported-
this can be adjusted in the File menu) before loading the profile editor tab.


## Profile Editor Capabilities
The profile editor tab populates with an automatically quality-controlled profile (red line) 
extracted from the raw data (black line). The autoQC algorithm which generates this profile
completes the following modifications to the raw data:

	* Despiking (points > 1 stdev from the mean in a 10m sliding window are removed)
	* 5m running smooth filter
	* Gap (VHF interference/false start) detection and removable (may be suppressed in settings)
	* Bottom strike detection (comparison to climatology and NOAA bathymetric data)
	* Climatology comparison (Levitus Ocean Climatology)
	* Point selection (resolution may be configured in settings)

### Profile editing tools
	* Isothermal layer depth: create a surface isothermal layer (reccomended < 10m)
		to remove any surface spikes transmitted prior to AXBT acclimation to
		ambient ocean temperatures
	* Depth delay: vertical shift in profile to account for any uncorrected VHF
		interference-driven false starts.
	* Maximum depth: tune profile maximum depth to suppress excessive interference
		or cut off any artifact data from bottom strikes. If ARES will not extend
		the depth of the automatically QC'ed profile to the depth of the raw profile,
		turn off the climatology and bathymetry-driven bottom strike detection options
		in the settings and then select "Rerun QC"
	* Add/Remove Point: Add or remove individual points from the profile
	* Inflection Point Threshold: This slider adjusts the magnitude of the d2T/dz2 value
		necessary for a point to be labelled as an inflection point and automatically
		recorded in the final profile. This option, along with the resolution setting 
		under "Profile Editor Preferences", requires the user to select "Rerun QC" in 
		order to take effect
	
### Profile viewing tools
	* Overlay climatology: View or hide the shaded blue climatological ocean temperatures
		based on AXBT drop location and month. This profile should not be taken as the
		absolute truth, but rather a guide that may highlight potential discrepancies if
		the measured and climatological profiles deviate significantly.
	* Navigation toolbar: The toolbar in the top row adjacent to the profile plot provides
		the option to change the VIEW of the profile. No part of this toolbar makes any
		changes to the temperature-depth profile, but rather enables the user to zoom 
		and pan to different locations on the profile. 
		
### Profile flagging tools
	* Bottom strike: This checkbox should be selected if either ETOPO1-indicated ocean
		depth or profile shape suggest the thermister probe reached the ocean bottom. 
		While this option does not affect the QC process for the profile, it is recorded
		in any JJVV files exported with the quality-controlled data. 
	* Profile flag: This menu is currently an INTERNAL-USE feature that enables the user
		to quickly highlight any potential profile errors or discrepancies. Currently 
		the selection of this box is not saved to any output files, but that will be 
		changed in a future release.
		

## Required Datasets
This program requires several datasets, saved in $ARES_PATH$/qcdata/$datasetsubfolder$/
Required datasets are:
	> Levitus Monthly Ocean Temperature Climatology (netCDF4 1 degree horizontal resolution):
		Provides global ocean climotological temperature depth profiles for the editor to 
		incorporate into the autoQC algorithm and display for the user to make addional edits
	> NOAA-NGDC ETOPO1 Global Relief Dataset (netCDF4, 1 arcminute resolution)
		Aids automatic and user-based bottom strike identification, populates map in profile
		editor tab to provide user with information regarding surrounding bathymetric features
	> World Hydrological Organization Global Seas (Shape File and supporting files)
		Provides high resolution demarkation lines for major seas and global ocean features to
		identify the region in which the AXBT was launched


## Radio Reciever Interaction
Processing AXBT files transmitted live via VHF requires a connected WiNRADIO
receiver. Multiple radio receivers may be connected and operated simultaneously.
The WiNRADIO driver is built into the program, and thus there are no external 
software dependencies associated with the WiNRADIOs. If a WiNRADIO is disconnected
or powered off during transmission, the program *should* terminate the data stream 
and close the current radio connection, so after reconnecting that radio the user
*should* be able to click "START" to resume processing. However, sudden disconnection
without first selecting "STOP" may result a hard crash of the operating system. In this case,
restarting the computer is sufficient to resolve any issues. For this reason, take care to
ensure that the power supply and USB connections between the receiver and the computer are
secured before starting a processing instance.


## Platform Support
ARES is currently only fully functional in Windows as there is currently
no .so or .dylib counterparts to the .DLL file that enables communication
between ARES and the WiNRADIO receiver API. Future versions may either
.so or .dylib files, or may transition to a cross-platform radio receiver
option such as SDR. 


## Python requirements
This program was developed in Python 3.x, with the GUI built using PyQt5.
Python dependencies are as follows:
Python core modules: sys, os, platform, traceback, ctypes, datetime, time

Modules which must first be installed before running ARES:
	numpy		matplotlib			scipy
	shapely		PyShp				PyQt5
	cmocean		netCDF4				pynmea2
	pyserial	
	fbs (generate executable)
	wheel (to download Shapely .whl file if on Windows)
	
### Installing on Linux/MacOs:
```
pip3 install numpy matplotlib scipy PyShp PyQt5 cmocean netCDF4 Shapely fbs pyserial pynmea2
```

NOTE: You may need to install the libgeos library (e.g. *brew install libgeos* on MacOS) for Shapely to work

### Installing on Windows:
```
pip install numpy matplotlib scipy PyShp PyQt5 cmocean netCDF4 wheel fbs pyserial pynmea2
```

Next, download Shapely wheel for Python v3.x from https://www.lfd.uci.edu/~gohlke/pythonlibs/- 
The file should be named Shapely-1.6.4.post2-cp3x-cp3xm-win(32 or _amd64).whl depending on Python version and windows type (e.g. Shapely-1.6.4.post2-cp37-cp37m-win_amd64.whl for Python v3.7, Windows x64-bit)

```
pip install Shapely-1.6.4.post2-cp3x-cp3xm-win(32 or _amd64).whl 
```
***(again, fill in necessary info there)
