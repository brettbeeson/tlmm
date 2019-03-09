import inspect
import shutil
from os.path import dirname, basename
import argparse
import glob
import datetime
import os.path
from PIL import Image
import piexif

verbose = False

def finditem(obj, key):
    if key in obj: return obj[key]
    for k, v in obj.items():
        if isinstance(v,dict):
            item = finditem(v, key)
            if item is not None:
                return item


def get_user_attributes(cls):
    boring = dir(type('dummy', (object,), {}))
    return [item
            for item in inspect.getmembers(cls)
            if item[0] not in boring]

def fileListFromGlob(fileGlobList):
    fileList = []
    for fg in fileGlobList:
        if (verbose): print ("Globbing {}.".format(fg))
        fileList.extend(glob.glob(fg))
    if (verbose): print ("Processing %d files"%(len(fileList)))
    return fileList
    
if __name__ == "__main__":
    
    print ("Starting...")

    parser = argparse.ArgumentParser("Add exif dates based on dated folder names")
    parser.add_argument("fileGlob",nargs='+')
    parser.add_argument("--verbose",action='store_true',default=False)
    parser.add_argument("--testmode",action='store_true',default=False)
    parser.add_argument("--force",action='store_true',default=False)
    
    args = (parser.parse_args())
    verbose = args.verbose
    
    if args.testmode:
        shutil.rmtree("testdata-addexifdate-processed",ignore_errors=True)
        shutil.copytree("testdata-addexifdate","testdata-addexifdate-processed")
    
    smallGap = datetime.timedelta(seconds=1)
    startTime = datetime.timedelta(hours=7)
    fileList = fileListFromGlob(args.fileGlob)
    fileList.sort()#.sort()
    
    i=0
    for fn in fileList:
        #f = open(fn,'rb')
        img = Image.open(fn)

     
        #for x in exifDict: print x
        #print finditem(exifDict,piexif.ExifIFD.DateTimeOriginal)
        #print exifDict['Exif'][piexif.ExifIFD.DateTimeOriginal]
#        print exifDict[piexif.ExifIFD.DateTimeOriginal]
        #print exifDict
        dto = None
    #    print exif.DateTimeOriginal
        try: 
            exifDict = piexif.load(img.info['exif'])
            dto  = finditem(exifDict,piexif.ExifIFD.DateTimeOriginal)   #printexif.primary.DateTimeOriginal 
        except Exception as e:
            # Made a basic one
            exifDict = {}
            exifDict['Exif']={}
            exifDict['Exif'][piexif.ExifIFD.DateTimeOriginal] = None
#        print ("fn={} dto={}".format(fn,dto))
        if dto == None or args.force:
            if verbose: print ("Adding missing datetime to {}".format(fn))
            parentDir = basename(dirname(os.path.abspath(fn)))
            try:
                # get parent folder's date
                i +=1
                dtFormat = "%Y-%m-%d"
                dateTimeObj = datetime.datetime.strptime(parentDir,dtFormat)
                # add a seq time
                dateTimePlus = dateTimeObj + startTime + smallGap * i
                dateStr = dateTimePlus.strftime("%Y:%m:%d %H:%M:%S")
                
                # apply to exif and save
              
                exifDict['Exif'][piexif.ExifIFD.DateTimeOriginal] = dateStr
                exif_bytes = piexif.dump(exifDict)
                img.save(fn, "jpeg", exif=exif_bytes)
                if verbose: print ("Adding date {} to {}".format(dateStr,fn))
                #f.save()
            except Exception as e:
                #print (e)
                print ("Couldn't set a date for parentdir:{} since {}".format(parentDir,e))
        
            #tags["EXIF DateTimeOriginal"] = 
        else:
            pass
            #if verbose: print ("Ignored date {} in file {}".format(dto,fn))
        img.close() 
    