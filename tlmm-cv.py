import tempfile
import os
import numpy
import mathutil
import shelve
import argparse
import glob
import subprocess
import exifread
from enum import Enum
import datetime
import os.path
import inspect
import sys
import itertools
import nptime
from nptime import nptime
try:
    import cv2
    #from cv2 import waitKey
except ImportError:
  pass

import PIL  # image text
from PIL import ImageFont
from PIL import Image
from PIL import ImageDraw


#from tkinter._fix import ver
    
from collections import OrderedDict    
import mathutil



def crop(image,top=0,bottom=0,left=0,right=0):
    if bottom==0: bottom=image.shape[0] 
    else: bottom=-bottom
    if right==0: right=image.shape[1]
    else: right=-right

    return image[top:bottom,left:right] 

    
def str_to_class(str):
    return getattr(sys.modules[__name__], str)


def neighborhood(iterable):
    iterator = iter(iterable)
    prev = None
    item = next(iterator)  # throws StopIteration if empty.
    for nextone in iterator:
        yield (prev,item,nextone)
        prev = item
        item = nextone
    yield (prev,item,None)

def defname():
    try:
        return inspect.stack()[1][3]
    except:
        pass 

class SliceType(Enum):
    day = 1
    hour = 2
    dayhour = 3
    concat = 4
    
    @staticmethod
    def fromStr(name):
        return getattr( SliceType, name )
    
    @staticmethod
    def names():
        return list(map(lambda x: x.name, list(SliceType)))
    #names = staticmethod(names_static)
    
class TLMovieMaker:
    tlMovies = []
    movieFolder = "."
    speedup = 60
    leastImages = 0
    moviesRelPath = ""
    fileGlob = ""
    fileList = []
    tlFiles = []
    motion=False
    dayStartTime = datetime.time(8)
    dayEndTime = datetime.time(15)
    daySliceLength = None
    verbose=False
    cache=True
    suffix=""
    fpsMax = None
    
    def __init__ (self):
        pass
    
    def __str__(self):
        return "{}: Movies:{}  SpeedUp:{} DaySliceLength:{} fileList:{} motion:{}".format(type(self).__name__,len(self.tlMovies),self.speedup,self.daySliceLength,len(self.fileList),self.motion)
    
    def ls(self):
        s = ""         
        for m in self.tlMovies:
            s = s & m.ls()        
        return s
        
    def makeTLFiles(self):
        self.tlFiles=[]
        print (os.getcwd())
        d = shelve.open("tlmm-cache",writeback=True)
        nErrors =0
        if self.verbose: print("Reading dates of {} files...".format(len(self.fileList)))
        globStr = ','.join(self.fileGlob)
        
        # try to find a cached version of file dates
        if self.cache and self.fileGlob!="" and globStr in d:
            print ("Found cache for {}: {} files".format(globStr,len(d[globStr])))
            self.tlFiles = d[globStr] 
        else:
            for fn in self.fileList:
                try:
                    #dname, bname = os.path.split(fn)
                    f = open(fn,'rb')
                    tags = exifread.process_file(f,details=False)
                    f.close()
                    datetimeTakenExifStr = tags["EXIF DateTimeOriginal"]
                    datetimeTakenExif = datetime.datetime.strptime(str(datetimeTakenExifStr), r'%Y:%m:%d %H:%M:%S')
                    #dateExifIso = dateExif.isoformat()
                    #print (os.path.basename(fn) + " date = " + str(exifDate) + " diso = " + diso)
                    #tlf = TLFile(fn,datetimeTakenExif,tags)
                    tlf = TLFile(fn,datetimeTakenExif)
                    self.tlFiles.append(tlf)
                except  Exception as e:
                    nErrors += 1
                    #print ("Error getting date for %s: %s"%(fn,e))
            # write to cache (
            if globStr!="" and globStr not in d:
                d[globStr] = self.tlFiles

        d.close()
        if self.verbose:
            print("Got {} timelapse images from {} files with {} errors".format(len(self.tlFiles),len(self.fileList),nErrors))
        if nErrors: print ("No dates available for {} of {}. Ignoring them.".format(nErrors,len(self.fileList)))
        return self.tlFiles.sort()      
    
    def senseMotion(self):
        if self.verbose: print("Sensing motion in {} movies".format(len(self.tlMovies)))
        for tlm in self.tlMovies:
            tlm.senseMotion()
    
    
    def fileListFromGlob(self, fileGlob):
        self.fileList = []
        self.fileGlob = fileGlob
        for fg in fileGlob:
            if (self.verbose): print ("Globbing {}.".format(fg))
            self.fileList.extend(glob.glob(fg))
        self.fileList.sort()
        if (self.verbose): print ("Processing %d files"%(len(self.fileList)))
    
    def loadMovies(self):
        del(self.tlMovies[:])
        self.makeTLFiles()
          
    def saveMovies(self):
        for m in self.tlMovies: 
            m.verbose = self.verbose # do earlier
            m.write()

class TLMovieMakerConcat(TLMovieMaker):
    def loadMovies(self):
        TLMovieMaker.loadMovies(self)
        self.tlMovies.append(TLMovie(self.tlFiles,self.moviesRelPath,self.speedup,self.leastImages,self.motion,self.suffix))        
        
        
class TLMovieMakerHour(TLMovieMaker):
    pass
#    def loadMovies(self):
#       TLMovieMaker.loadMovies(self)

# Make one movie per day
#
class TLMovieMakerDay(TLMovieMaker):
    def __str__(self):
        return "{}: Movies:{}  SpeedUp:{} fileList:{} range={} to {} daySliceLength:{} leastImages:{} motion:{}".format(type(self).__name__,len(self.tlMovies),self.speedup,len(self.fileList),self.dayStartTime,self.dayEndTime,self.daySliceLength,self.leastImages,self.motion)
        
    def ls(self):
        s=""
        for m in self.tlMovies:
            s += m.ls()  
        return s
        
    def loadMovies(self):
        TLMovieMaker.loadMovies(self)
        groupedByDayTLFiles = self.groupByDay(self.tlFiles)
        for day in groupedByDayTLFiles:
            dayFilesFiltered = self.filterByHour(groupedByDayTLFiles[day], self.dayStartTime, self.dayEndTime,self.verbose)
            if self.verbose: print("Loading movie for {} with {} filtered files from {} total files ".format(day,len(dayFilesFiltered),len(groupedByDayTLFiles[day])))
            self.tlMovies.append(TLMovie(dayFilesFiltered,self.moviesRelPath,self.speedup,self.leastImages,self.motion,fpsMax=self.fpsMax,verbose=self.verbose))
          
        #pprint(groupedTLFiles)
    @staticmethod
    def filterByHour(localTLFiles,localStartTime=None,localEndTime=None,verbose=False):
        retval = localTLFiles
        #if verbose: print("Filtering from {} to {}".format(localStartTime,localEndTime))
        #if verbose: print("Starting with {} files".format(len(retval)))    
        if localStartTime is not None:
            retval = list(filter(lambda x: x.datetimeTaken.time()>=localStartTime, retval))
        
        #if verbose: print("After start with {} files".format(len(retval)))    
            
        if localEndTime is not None:
            #print(localEndTime)
            for i in retval:
                retval = list(filter(lambda x: x.datetimeTaken.time()<=localEndTime, retval ))
        #if verbose: print("After end {} files".format(len(retval))  )  
        
        return retval

    @staticmethod
    def groupByDay(localTLFiles):
        groupedTLFiles = OrderedDict()
        for day, dayFiles in itertools.groupby(localTLFiles,lambda x: x.datetimeTaken.date()):
           # print ("Day {}".format(day))
            groupedTLFiles[day] = []
            for tlf in sorted(dayFiles):
                groupedTLFiles[day].append(tlf)
            #    print ("\t{}".format(tlf.filename))
            #groupedTLFiles = sorted(groupedTLFiles)
        return groupedTLFiles
        
        
class TLMovieMakerDayhour(TLMovieMakerDay):
    def loadMovies(self):
        slicedTLFiles = []
        TLMovieMaker.loadMovies(self)
            
        groupedByDay = self.groupByDay(self.tlFiles)
    #    dailyTimeDelta = (datetime.datetime.combine(datetime.date.today(),self.dayEndTime) - (datetime.date.today() + self.daySliceLength)) / (len(groupedByDay)-1)
        # work out minutesPerDay to be continuous
        if self.daySliceLength == None:
            self.daySliceLength = (nptime.nptime.from_time(self.dayEndTime) - nptime.nptime.from_time(self.dayStartTime))   / len(groupedByDay)
            if self.verbose: print ("Autoset dayslicelength to {}".format(self.daySliceLength))
        
        dailyTimeDelta = nptime.from_time(self.dayEndTime) - nptime.from_time(self.dayStartTime)  
        dailyTimeDelta = dailyTimeDelta - self.daySliceLength
        dailyTimeDelta /= len(groupedByDay)-1
        #print(dailyTimeDelta)
        startDateTime = nptime.from_time(self.dayStartTime)
        #        sortedGroupByDay = sorted(groupedByDay.items(), key=lambda (k,v): k)
        
        for day in sorted(groupedByDay.keys()):
            #dayTLFiles =  self.tlFiles[day]
            #endTime = startTime + self.daySliceLength
            endDateTime = startDateTime + self.daySliceLength            
            dayTLFiles = self.filterByHour(groupedByDay[day],startDateTime,endDateTime)
            if (self.verbose):
                print ("Day {}: {} to {} ({}/{} files)".format(day,startDateTime,endDateTime,len(dayTLFiles),len(groupedByDay[day])))            
            
            slicedTLFiles.extend(list(dayTLFiles))
            #self.tlMovies.append(TLMovie(dayTLFiles,self.moviesRelPath,self.speedup))
            #self.tlMovies
            startDateTime += dailyTimeDelta
        slicedTLFiles.sort()
        if self.verbose:
            pass 
            #[print(tlf) for tlf in slicedTLFiles]
            #input("Please Enter to continue")
        self.tlMovies.append(TLMovie(slicedTLFiles,self.moviesRelPath,self.speedup,self.leastImages))
        print ("Warning: calcGaps not run __LINE__")
        #self.calcGaps()
    
        
class TLMovie:
    tlFiles  = [] 
    disjointThreshold = datetime.timedelta(hours=1)       # minutes. Gaps greater than this are considered disjoint
    bitrate="2000k" # str for ffmpeg
    movieDir = ""
    speedup = 0
    leastImages = 100
    customMovieFilename = ""
    verbose = False
    motion=False
    motionTimeDeltaMax =  datetime.timedelta(hours=1)   # if longer than this, cannot really compute motion
    fpsMax = None # if unset, use all frames; if set, select frames to achieve this fps


    def __init__(self,tlFiles, movieDir=".",speedup=None,leastImages=None,motion=None,suffix="",fpsMax=None,verbose=None):
        self.tlFiles = tlFiles
        if movieDir: self.movieDir = movieDir
        if speedup: self.speedup = speedup
        if leastImages is not None: self.leastImages = leastImages
        if motion: self.motion = motion
        if verbose: self.verbose = verbose
        self.suffix = suffix
        self.calcGaps()
        if fpsMax and self.fpsVideo()>fpsMax:
            if verbose: print ("Set fpsMax to %f" % fpsMax)
            self.fpsMax= fpsMax
            self.selectTLFilesToSuitMaxFPS()


    
    def __str__(self):
        return  "TLMovie: filename={} speedup={} fpsVideo={:.1f} br={} djt={} frames={} spfReal={:.1f} leastImages={} motion:{} ".format(self.movieFilename(),self.speedup,self.fpsVideo(),self.bitrate,self.disjointThreshold,len(self.tlFiles),self.spfReal(),self.leastImages,self.motion)
    
        
    def ls(self):
        s = ""
        for tlf in self.tlFiles:
            s += str(tlf) + "\n"
        return s

    # Uses self.TLFiles as a source of images to construct a NEW self.TLFiles with just enough images to achieve videoFPS
    def selectTLFilesToSuitMaxFPS(self):
        if (self.verbose):
            print("selectTLFilesToSuitMaxFPS: realStart: %s realEnd: %s" % (self.firstDateTime(), self.lastDateTime()))
        frameTime = self.firstDateTime()
        spfVideoToSet = 1 / self.fpsMax
        spfRealToSet = spfVideoToSet * self.speedup
        newTLFiles = []
        # Run through real time, stepping per-frame-to-be and find the nearest frame in time to use
        while frameTime < self.lastDateTime():
            frameTime += datetime.timedelta(seconds=spfRealToSet)
            tlf = min(self.tlFiles, key=lambda x: abs(x.datetimeTaken - frameTime))
            tlf.durationReal = datetime.timedelta(seconds=spfRealToSet)
            if (self.verbose):
                pass
                #print ("frameTime %s" % frameTime)
                #print ("found %s at %s" % (tlf,tlf.datetimeTaken))
            newTLFiles.append(tlf)
        self.tlFiles = newTLFiles
        if (self.verbose):
            dv = self.durationVideo()
            print("selectTLFilesToSuitMaxFPS: maxFps=%f fps= %f duration = %s newTLFiles = %d" % (self.fpsMax,self.fpsVideo(),self.lastDateTime() - self.firstDateTime(),len(newTLFiles)))


    def calcGaps(self):

        for prev,item,nextitem in neighborhood(self.tlFiles):
            if prev is not None:
                item.durationReal = item.datetimeTaken - prev.datetimeTaken

            if prev is None or item.durationReal > self.disjointThreshold:
                # if there is a massive disjoint in the images' datetakens, skip this in the video (ie. set durationReal from BIG to a small value)
                item.durationReal = datetime.timedelta(milliseconds=100) #(seconds=666)
                item.isFirst=True



    # Since frames' time may be disjoint, add the gaps between all frames; this ignores disjoint frames (see "calcgaps")
    def durationReal(self):
        dr=datetime.timedelta()
        for tlf in self.tlFiles:
            dr += tlf.durationReal
        return dr
    
    def firstDateTime(self):
        return self.tlFiles[0].datetimeTaken

    def lastDateTime(self):
        return self.tlFiles[-1].datetimeTaken
    
    def durationVideo(self):
        return self.durationReal() / self.speedup
    
    def fpsVideo(self):
        if len(self.tlFiles)==0: return 0
        if  self.durationVideo().total_seconds()==0 :return 0
        return len(self.tlFiles) / self.durationVideo().total_seconds()
    
    def addTLFiles(self, tlfiles):
        # concat list
        self.tlFiles.append(tlfiles)
        pass    
    
    def fpsReal(self):
        if len(self.tlFiles)==0: return 0
        if  self.durationReal().total_seconds()==0 :return 0
        return len(self.tlFiles) / self.durationReal().total_seconds()
    
    def spfReal(self):
        if self.fpsReal()==0: return 0
        return 1 / self.fpsReal()
    #
    # Compare image before to present image and mark if present one is quite diff-erent
    # 
    #
    def senseMotion(self):
        print ("Sensing motion for m:{}".format(self))
        # expect smaller gaps because the motion senser will cut-up the video into sensed fragments.
        # set the disjoint threshold low, so that the video run with out long pauses between fragments
        self.disjointThreshold = datetime.timedelta(minutes=1)

        #self.verbose = True
        for prev,item,nextitem in neighborhood(self.tlFiles):
            if (self.verbose):
                print("Sensing motion for TLFile: %s with prev=%s next=%s" % (item, prev, nextitem))
            if prev is not None:
                if item.durationReal < self.motionTimeDeltaMax:
                    item.senseMotion(prev)
                else:
                    pass
                    # mark as "keep" as it is the start of new item period
        #if self.verbose:
            # show the plots of motion
        cv2.destroyAllWindows()    
        

        motionList = list(tlf.motion for tlf in self.tlFiles)
        percentile95 = numpy.percentile(motionList,99)
        if self.verbose: print ("Motion 95 percentile = %f" % percentile95)
        motionList95=[]
        for m in motionList:
            if m > percentile95: 
                #print ("Truncating {} to {}".format(m,percentile95))
                m = percentile95
            motionList95.append(m)
            #  SMOOTH
        fpm = self.fpsReal()*60
        fts = int(fpm * 10)+1 # avoid zero
        #print ("fpm={} fts={}".format(fpm,fts))
        showMotionPlots = False
        if showMotionPlots:
            mathutil.plot1d([motionList95,mathutil.smoothList(motionList,motionList95,degree=fts),mathutil.smoothListGaussian(motionList95,degree=fts),mathutil.smoothListTriangle(motionList95,degree=fts),mathutil.smoothListTriangle(motionList95,degree=fts)])
        # Set back smoothes values to tlFiles
        motionTotal =0
        motionThreshold = 0.00015
        for i,motion in enumerate(mathutil.smoothListGaussian(motionList95,degree=fts)):
                self.tlFiles[i].motion = motion
        preMotionFilterNFiles = len(self.tlFiles)
        # THRESHOLD
        filterMotionImages= True
        if (filterMotionImages):
            self.tlFiles = [item for item in self.tlFiles if item.motion >= motionThreshold]
            self.calcGaps()
        
        addMotionText=True
        if (addMotionText):
            for tlf in self.tlFiles:
                if tlf.motion >= motionThreshold:
                    tlf.addText("MOTION DETECTED")
    

        print ("Detected smoothed motion in {} of {}".format(len(self.tlFiles),preMotionFilterNFiles ))

    
    def write(self):
        if len(self.tlFiles)<self.leastImages:
            if self.verbose: print ("Skipping {} as only got {} images".format(self.movieBasename(),len(self.tlFiles)))
            return False

        self.writeImageList()
        
        if self.verbose: 
            print ("TLMovie.write(): writing {} images to {} durationReal = {}s (={}) durationVideo= {}s (={}) ".format(len(self.tlFiles),self.moviePathname(),self.durationReal().total_seconds(),self.durationReal(),self.durationVideo().total_seconds(),self.durationVideo()))
            print("TLMovie.write(): self = {}".format(self))
            print("TLMovie.write(): abspath = %s" % os.path.abspath(self.moviePathname()))
        logFile = open(self.logFilename(),"w")
        #p = subprocess.Popen(["ffmpeg.exe","-y","-f","concat","-i",self.listFilename(),"-b:v",str(self.bitrate),"-r",str(self.fpsVideo),self.moviePathname()],stdout=logFile,stderr=logFile)
        #textcmd =  ''' drawtext=x=(w-text_w)/2: y=(h-text_h-line_h)/2:fontcolor=white:fontfile=/Windows/Fonts/arial.ttf:text=************ MOTION ***************'''
        
        r = subprocess.call(["ffmpeg.exe","-y","-f","concat","-i",self.listFilename(),"-b:v",str(self.bitrate),"-r",str(self.fpsVideo()),self.moviePathname()],stdout=logFile,stderr=logFile)
        logFile.close()
        #(stdoutdata, stderrdata) = p.communicate()
        #if (p.returncode == 0):
        if r == 0:
            if self.verbose: print("Wrote {} images to {}".format(len(self.tlFiles),self.moviePathname()))
            return True
        else:
            print("*** FAILED on writing {} images to {}. Logged to {}".format(len(self.tlFiles),self.moviePathname(),self.logFilename()))
            print(open(self.logFilename()).read())
        return False
    
    def writeImageList(self):
        f = open(self.listFilename(),'w')
        for tlf in self.tlFiles:
            f.write("file '" + tlf.filename + "'\n")
            f.write("duration " + str(tlf.durationReal / self.speedup) + "\n")     
        f.close()
    def logFilename(self):
        return os.path.join(self.movieDir,"tlmm.log")
    
    def listFilename(self):
        return os.path.join(self.movieDir,self.movieBasename() + ".list")
    
    def movieFilename(self):
        return self.movieBasename() + ".avi"
    
    def moviePathname(self):
        return os.path.join(self.movieDir,self.movieFilename())
    
    def movieBasename(self):
        bn = self.customMovieFilename
        if bn=="": 
            if len(self.tlFiles)>0:
                bn = str(self.tlFiles[0].datetimeTaken.date())+"_to_" +str(self.tlFiles[-1].datetimeTaken.date())
            bn += "-" + self.suffix

        return bn
       
class TLFile:
    durationReal = datetime.timedelta()
    filename=""
    datetimeTaken=None
    tags=[]
    isFirst=False   # of a sequence
    isLast=False    # of a sequence - there will be gap after (or end)
    motion = 0      # 0 to 1
    def __repr__(self):
        return '{}\t\t{}\t\t{}\t{}'.format(self.datetimeTaken,self.durationReal,self.filename,self.isFirst if self.isFirst else "    ")
    
    def __str__(self):
        return '{}\t\t{}\t\t{}\t{}'.format(self.datetimeTaken,self.durationReal,self.filename,self.isFirst if self.isFirst else "    ")
    def __init__(self,filename,datetimeTaken,tags=None):
        self.filename = filename
        self.datetimeTaken = datetimeTaken
        self.tags = tags
    def __gt__(self, o2):
        return self.datetimeTaken > o2.datetimeTaken
    def __eq__(self, o2):
        return self.datetimeTaken == o2.datetimeTaken
        pass
    def __add__(self, other):
        return self.durationReal + other.durationReal
    def senseMotion(self,prevTLF):
        testimg = cv2.imread(self.filename, 0)
        selfImg = cv2.blur(crop(cv2.imread(self.filename,0),bottom=50),(5,5))
        prevImg = cv2.blur(crop(cv2.imread(prevTLF.filename,0),bottom=50),(5,5))
        diffImg  =cv2.blur(crop( cv2.absdiff(selfImg,prevImg) ,bottom=50),(5,5))
        retval,diffImg = cv2.threshold(diffImg, thresh=64,maxval=10,type=cv2.THRESH_TOZERO)
        maxDiff = selfImg.size * 255
        diffPC = cv2.sumElems(diffImg)[0] / maxDiff
        cv2.putText(selfImg,"Mottion={:.2%}".format(diffPC),(10,500), cv2.FONT_HERSHEY_PLAIN, 1,(255,255,255),2,cv2.LINE_AA)
        if diffPC>0.0005:
            cv2.putText(selfImg,"Motion!",(10,400), cv2.FONT_HERSHEY_PLAIN, 3,(255,255,255),3,cv2.LINE_AA)
        self.motion = diffPC
        if False:
            cv2.imshow('self',selfImg)
            cv2.imshow('prev',prevImg)
            cv2.imshow('diff',diffImg )
        #if cv2.waitKey() == ord('q'):
        #    sys.exit()     
    def addText(self,s):
        #
        # WILL WRITE OVER THE FILES!
        #

        font = ImageFont.truetype("/Windows/Fonts/arial.ttf",25)
        img=Image.open(self.filename)
        # THIS CAUSES A WARNING "UNCLOSED FILE"
        draw = ImageDraw.Draw(img)
        draw.text((0, 0),s,(255,255,0),font=font)
        #draw = ImageDraw.Draw(img)
        #draw = ImageDraw.Draw(img)
        self.filename = os.path.join(tempfile.gettempdir(),os.path.basename(self.filename))
        img.save(self.filename)
        img.close()
            
            
if __name__ == "__main__":
    parser = argparse.ArgumentParser("Make timelapse movies")
    parser.add_argument("fileGlob",nargs='+')
    parser.add_argument("--verbose",action='store_true',default=False)
    parser.add_argument("--dryrun",action='store_true',default=False)
    parser.add_argument("--moviesRelPath", default="", type=str)
    parser.add_argument("--nocache",action='store_true',default=False)
    parser.add_argument("--slicetype",choices=SliceType.names(),default="day")
    parser.add_argument("--speedup",default=300,type=int)
    parser.add_argument("--leastimages",default=100,type=int)
    parser.add_argument("--fpsmax", default=None, type=int)
    parser.add_argument("--daystarttime",default="0:00",type=str)
    parser.add_argument("--dayendtime",default="23:59",type=str)
    parser.add_argument("--minutesperday",default=None,type=int,help="For hour or dayhour slice types, minutes to show per day")
    parser.add_argument("--motion",action='store_true',default=False,help="Filter to include only motiony images")
    parser.add_argument("--suffix",default="",type=str)
    
    args = (parser.parse_args())

    mm = str_to_class("TLMovieMaker" + args.slicetype.title())()
    mm.moviesRelPath = args.moviesRelPath
    mm.suffix = args.suffix
    mm.verbose = args.verbose
    mm.fileListFromGlob(args.fileGlob)
    mm.speedup = args.speedup
    mm.dayStartTime = datetime.datetime.strptime(args.daystarttime,"%H:%M").time()
    mm.dayEndTime = datetime.datetime.strptime(args.dayendtime,"%H:%M").time()
    mm.leastImages = args.leastimages
    mm.motion = args.motion
    if args.minutesperday:
        mm.daySliceLength = datetime.timedelta(minutes=args.minutesperday)
    mm.cache = not args.nocache
    mm.fpsMax  = args.fpsmax

    if mm.verbose:
        pass
        print("Loading movies using: {} ...".format(mm))
    mm.loadMovies()
    
    if mm.motion:
        mm.senseMotion()
    if mm.verbose:
        print("Loaded movies {}".format(mm))
    #    [print(m) for m in  mm.tlMovies]
    if not args.dryrun:
        if mm.verbose: print("Saving movies...")
        mm.saveMovies()
    
