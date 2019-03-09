from inspect import getsourcefile
from os.path import abspath
import os
import unittest
import datetime
from tlmm import TLMovieMaker, TLMovieMakerConcat,    TLMovieMakerDay, TLMovieMakerDayhour
import warnings

class Test(unittest.TestCase):

    def datadir(self):
        mydir =os.path.dirname(abspath(getsourcefile(lambda:0)))
        return os.path.join(mydir,"testdata")
        
    def setUp(self):
        warnings.simplefilter("ignore", ResourceWarning)
        os.chdir(self.datadir())


    def tearDown(self):
        pass

    def testFPS(self):
        mm = TLMovieMakerDay()
        mm.cache = False
        mm.leastImages = 0
        mm.fileListFromGlob(["3\*.jpg"])

        #mm.fpsMax = .1
        mm.verbose = True
        mm.loadMovies()
        mm.saveMovies()
        print("%s"%mm)
        [print(m) for m in  mm.tlMovies]
#        self.assertEqual(len(mm.tlMovies), 3)

def testConcat1(self):
    mm = TLMovieMakerConcat()
    mm.cache = False
    mm.fileListFromGlob(["*.jpg"])
    mm.loadMovies()
    mm.saveMovies()
    #print("%s"%mm)
    #[print(m) for m in  mm.tlMovies]
    self.assertEqual(len(mm.tlMovies[0].tlFiles), 91)

def testConcat2(self):
    mm = TLMovieMakerConcat()
    mm.fileListFromGlob(["**\*.jpg"])
    mm.cache = False
    mm.loadMovies()

    mm.saveMovies()
    #print("%s"%mm)
    #[print(m) for m in  mm.tlMovies]
    self.assertEqual(len(mm.tlMovies[0].tlFiles), 195)

def testDayMaker(self):
    mm = TLMovieMakerDay()
    mm.cache = False
    mm.fileListFromGlob(["**\*.jpg"])
    mm.loadMovies()
    mm.saveMovies()
    #print("%s"%mm)
    #[print(m) for m in  mm.tlMovies]
    self.assertEqual(len(mm.tlMovies), 3)

def testDayHourMaker(self):
    mm = TLMovieMakerDayhour()
    mm.fileListFromGlob(["**\*.jpg"])
    mm.cache = False
    #mm.dayStartTime = datetime.time(8)
    #mm.dayEndTime = datetime.time(8)
    mm.verbose = True
    mm.dayStartTime = datetime.time(8)
    mm.dayEndTime = datetime.time(17)
    mm.daySliceLength = datetime.timedelta(hours=3)
    mm.loadMovies()
    mm.saveMovies()

    print("%s"%mm)
    #[print(m) for m in  mm.tlMovies]
    self.assertEqual(len(mm.tlMovies), 1)
    self.assertEqual(len(mm.tlMovies[0].tlFiles),122)
    self.assertEqual(mm.tlMovies[0].tlFiles[29].datetimeTaken.date(),datetime.date(2015,7,3))
    self.assertEqual(mm.tlMovies[0].tlFiles[30].datetimeTaken.date(),datetime.date(2015,7,4))


def testMotion(self):
    mm = TLMovieMakerDay()
    mm.cache = False
    mm.motion = True
    mm.verbose = True
    mm.leastImages = 1

    mm.fileListFromGlob(["**\*.jpg"])
    mm.loadMovies()
    mm.senseMotion()
    mm.saveMovies()
    print("%s" % mm)
    [print(m) for m in mm.tlMovies]
    self.assertEqual(len(mm.tlMovies), 3)


if __name__ == "__main__":
    print("Starting unit tests")
    #import sys;sys.argv = ['', 'Test.testHelp']
    unittest.main()