; Script generated by the Inno Script Studio Wizard.
; SEE THE DOCUMENTATION FOR DETAILS ON CREATING INNO SETUP SCRIPT FILES!

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Do not use the same AppId value in installers for other applications.
; (To generate a new GUID, click Tools | Generate GUID inside the IDE.)
AppId={{EBBBC69F-B2EE-477C-840F-97022F4AC1C1}
AppName=ARES
AppVersion=1.0
;AppVerName=ARES 1.0
AppPublisher=Casey Densmore
DefaultDirName={pf}\ARES
DefaultGroupName=ARES
OutputBaseFilename=ARES_win64_installer
SetupIconFile=C:\Users\cdens\Documents\autoQC\EXEgen_25APR\qclib\dropicon.ico
Password=5309
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64 
LicenseFile=License_GNU_GPL_v3.txt

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 0,6.1

[Files]
Source: "C:\Users\cdens\Documents\autoQC\EXEgen_25APR\ARES.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\cdens\Documents\autoQC\EXEgen_25APR\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Specify pathway to Win10 x64bit driver .inf and .sys files
Source: "C:\Users\cdens\Documents\autoQC\EXEgen_25APR\qcdata\Driver\Win10\WRG39WSB.inf"; DestDir: {app}\driver;
Source: "C:\Users\cdens\Documents\autoQC\EXEgen_25APR\qcdata\Driver\Win10\WRG39WSB_XP64.sys"; DestDir: {app}\driver;
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
Name: "{group}\ARES"; Filename: "{app}\ARES.exe";  IconFilename: "{app}\qclib\dropicon.ico"
Name: "{group}\{cm:UninstallProgram,ARES}"; Filename: "{uninstallexe}";  IconFilename: "{app}\qclib\dropicon.ico"
Name: "{commondesktop}\ARES"; Filename: "{app}\ARES.exe"; Tasks: desktopicon; IconFilename: "{app}\qclib\dropicon.ico"
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\ARES"; Filename: "{app}\ARES.exe"; Tasks: quicklaunchicon; IconFilename: "{app}\qclib\dropicon.ico"

[Run]
Filename: "{app}\ARES.exe"; Description: "{cm:LaunchProgram,ARES}"; Flags: nowait postinstall skipifsilent
; install driver using RUNDLL32.EXE (specify driver Win10 .inf file)
Filename: "{sys}\rundll32.exe"; Parameters: "setupapi,InstallHinfSection DefaultInstall 128 {app}\qcdata\Driver\Win10\WRG39WSB.inf"; WorkingDir: "{app}\qcdata\Driver\Win10";
