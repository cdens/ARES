#! /usr/bin/env python3
# Build script for ARES

import os, shutil
from platform import system as cursys


def copystuff(sourcepath, destpath):
    try:
        shutil.copy(sourcepath, destpath)
    except IsADirectoryError:
        shutil.copy(sourcepath, destpath)
        
def movestuff(sourcepath, destpath):
    shutil.move(sourcepath, destpath)    

def deletestuff(itempath):
    try:
        os.remove(itempath)
    except PermissionError:
        shutil.rmtree(itempath)


        
#copies code from github directory to separate directory, only copying necessary files
def copy_code(repodir,ares_path,things_to_copy,copy_if_nonexistent,slash):
    
    #copy over relevant code to new directory
    for item in things_to_copy:
        sourcepath = repodir + slash + item
        destpath = ares_path + slash + item
        if os.path.exists(destpath): #delete item if it exists
            deletestuff(itempath)
        copystuff(sourcepath, destpath)
            
    #only copy over qcdata and testdata if the directories don't exist already
    for item in things_to_copy:
        sourcepath = repodir + slash + item
        destpath = ares_path + slash + item
        if not os.path.exists(destpath): #delete item if it exists
            copystuff(sourcepath, destpath)


            
            
#creates configuration file and runs PyInstaller
def run_pyinstaller(specfile,slash):
    os.system(f"pyinstaller {specfile}") #execute pyinstaller
    
    #move files from dist to upper directory
    distpath = "dist" + slash + os.listdir("dist")[0]
    for item in os.listdir(distpath):
        movestuff(distpath + slash + item, item)
    
    #delete dist and build, spec file
    deletestuff("dist")
    deletestuff("build")
    deletestuff(specfile)
    
    movestuff("main.exe","ARES.exe") #rename main.exe to ARES.exe
    
    
    
#creates configuration file and runs Inno Script Setup
def run_inno(innofile, installerfile, slash):
    os.system(f'issc "{innofile}"') #executing inno command
    
    #moving output file to same directory level, deleting config file
    deletestuff(innofile)
    movestuff("Output"+slash+installerfile,installerfile)
    deletestuff("Output")


    
    
if __name__ == "__main__":
    
    #filesystem dependent
    if cursys() == 'Windows':
        slash = '\\'
    else:
        slash = '/'
    
    #reading main.spec and ares iss config files
    print("Configuring environment/preparing to bundle ARES")
    specfile = "main.spec"
    specfilecontents = open(specfile,"r").read().strip()
    issfile = "ares_installer_setup.iss"
    issfilecontents = open(issfile,"r").read().strip()
    
    os.chdir("..") #backing out of bundling folder
    repodir = os.getcwd() #getting current directory (github directory)
    
    #read/ID necessary variables (general path, build path, ARES version + version for filenames)
    bundledir = "ARES_Bundled" #establishing name for bundle directory
    ares_version = open("version.txt","r").read().strip() #app version
    ares_installer_filename = "ARES_win64_installer_v" + ares_version + ".exe"
    
    os.chdir("..") #backing out one more directory
    ares_path = os.getcwd() + slash + bundledir #full path to bundled version of ares
    
    #creating bundling directory if it doesn't exist
    if not os.path.exists(ares_path):
        os.mkdir(ares_path)
    
    print(f"Copying ARES code (and data?) to bundling directory {bundledir}")
    things_to_copy = ["ARESgui","License_GNU_GPL_v3.txt","main.py","qclib","README.md","version.txt"]
    copy_if_nonexistent = ["qcdata","testdata"]
    copy_code(repodir,ares_path,things_to_copy,copy_if_nonexistent,slash)
    
    print("Running PyInstaller and reorganizing files")
    with open(specfile,"w") as f: #writing pyinstaller config file
        f.write(specfilecontents.replace("{{ARESPATH}}",ares_path))
    os.chdir(bundledir)
    run_pyinstaller(specfile,slash)
    os.chdir("..")
    
    print("Running Inno Script Setup/Generating executable installer")
    #writing iss config file
    replacevars = ["{{ARESPATH}}","{{ARESVERSION}}","{{ARESINSTALLERFILENAME}}"]
    replacewith = [ares_path, ares_version, ares_installer_filename]
    for var,item in zip(replacevars, replacewith):
        issfilecontents = issfilecontents.replace(var,item)
    with open(issfile,"w") as f:
        f.write(issfile)
    run_iss()
    
    #deleting build folder
    deletestuff(bundledir)
    
    
    
    
    
    
    
    