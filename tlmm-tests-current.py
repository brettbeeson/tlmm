import subprocess
from inspect import getsourcefile
from os.path import abspath
import unittest
from tl import *
import shutil
import logging
from datetime import timedelta  # class!

import filebyday

logger = logging.getLogger(__name__)


class Test(unittest.TestCase):

    def datadir(self):
        mydir = os.path.dirname(abspath(getsourcefile(lambda: 0)))
        return os.path.join(mydir, "testdata")

    def setUp(self):
     #   warnings.simplefilter("ignore", ResourceWarning)
        os.chdir(self.datadir())

    def test_filebydate(self):
        try:
            shutil.rmtree("temp-filebyday")
        
        except Exception as e:
            print (e)
        pass
        shutil.copytree("filebyday","temp-filebyday")
        __name__ = "main"
        filebyday
            


    def tearDown(self):
        pass

    def test_ignore_valid(self):
        l = logging.getLogger("tl").level
        # expect warnings of invalid files
        logging.getLogger("tl").setLevel(logging.ERROR)
        mm = VideoMakerDay()
        mm.files_from_glob(["invalid/*.jpg"])
        mm.load_videos()
        logging.getLogger("tl").setLevel(l)

    def test_ignore_last(self):
        return
        mm = VideoMakerDay()
        mm.ignore_last = True
        mm.files_from_glob(["3days1h/*.jpg"])
        mm.load_videos()
        print(mm)


    def test_graph(self):
        return
        mm = VideoMakerConcat()
        mm.files_from_glob(["3days1m/*.jpg"])
        mm.load_videos()
        mm.graph_intervals(timedelta(seconds=3600))

    def test_frames(self):
        self.assertEqual(frames("samplemovies/sample1.mp4"),55)
        self.assertEqual(frames("samplemovies/sample2.mp4"), 444)

    def test_fps(self):
        self.assertEqual(fps("samplemovies/sample1.mp4"),1)
        self.assertEqual(fps("samplemovies/sample2.mp4"), 20)



if __name__ == "__main__":
    print("Starting unit tests")
    # import sys;sys.argv = ['', 'Test.testHelp']
    logger.setLevel(logging.DEBUG)
    logging.basicConfig(format='%(levelname)s:%(message)s')
    unittest.main(verbosity=2)
