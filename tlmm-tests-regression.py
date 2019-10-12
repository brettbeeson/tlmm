import subprocess
from inspect import getsourcefile
from os.path import abspath
import os
import unittest
import datetime
import tlmm
from tlmm import VideoMakerConcat, VideoMakerDay, VideoMakerHour
import warnings
import shutil
import logging


class Test(unittest.TestCase):

    def datadir(self):
        mydir = os.path.dirname(abspath(getsourcefile(lambda: 0)))
        return os.path.join(mydir, "testdata")

    def setUp(self):
     #   warnings.simplefilter("ignore", ResourceWarning)
        os.chdir(self.datadir())
        tlmm.logger.setLevel(logging.DEBUG)
        logging.basicConfig(format='%(levelname)s:%(message)s')

    def tearDown(self):
        pass

    def test_vsync_cont(self):

        mm = VideoMakerDay()
        logging.info("DISCONTINUOUS SET | CFR-PADDED")
        mm.files_from_glob(["discont-stamped/*.jpg"])  # 228 files
        mm.load_videos()
        nfiles = len(mm.tl_videos[0].tl_files)

        self.assertEqual(nfiles, 228)
#        mm.write_videos(suffix="-dis-cfr-padded",vsync="cfr-padded",speedup=60,force=True)
 #       f = frames("2019-03-19T13_to_2019-03-19T13-dis-cfr-padded.mp4")
  #      logging.info("Write {} and read {}. fps_avg={} fps_max={}"
   #                  .format(nfiles, f, mm.tl_videos[0].fps_video_avg(speedup=60), mm.tl_videos[0].fps_video_max(speedup=60)))
       # self.assertEqual(228, f, "Got {} frames instead of expected 404".format(f))

        logging.info("DISCONTINUOUS SET | CFR-EVEN")
        mm.write_videos(suffix="-dis-cfr-even",vsync="cfr-even",force=True,speedup=60)
        f = frames("2019-03-19T13_to_2019-03-19T13-dis-cfr-padded.mp4")
        logging.info("Write {} and read {}. fps_avg={} fps_max={}"
                     .format(nfiles, f, mm.tl_videos[0].fps_video_avg(speedup=60), mm.tl_videos[0].fps_video_max(speedup=60)))

        logging.info("DISCONTINUOUS SET | VFR")
        mm.write_videos(suffix="-dis-vfr", vsync="vfr", force=True, speedup=60)
        nfiles = len(mm.tl_videos[0].tl_files)
        f = frames("2019-03-19T13_to_2019-03-19T13-dis-vfr.mp4")
        logging.info("Write {} and read {}. fps_avg={} fps_max={}"
                     .format(nfiles, f, mm.tl_videos[0].fps_video_avg(speedup=60), mm.tl_videos[0].fps_video_max(speedup=60)))
        self.assertEqual(228, f, "Got {} frames instead of expected 404".format(f))

        logging.info("CONTINUOUS SET | CFR")
        mm = VideoMakerDay()
        mm.files_from_glob(["cont-stamped/*.jpg"])
        mm.load_videos()
        mm.write_videos(
            suffix="-con-cfr-even",
            vsync="cfr-even",
            force=True,
            speedup=60)
        m = mm.tl_videos[0]
        nfiles = len(m.tl_files)
        f = frames("2019-03-19T13_to_2019-03-19T13-con-cfr-even.mp4")
        logging.info("Write {} and read {}. fps_avg={} fps_max={}"
                     .format(nfiles, f, m.fps_video_avg(speedup=60), m.fps_video_max(speedup=60)))
        self.assertEqual(nfiles,f,"Got {} frames, expected {}".format(f,nfiles))
        logging.info("CONTINUOUS SET | VFR")
        mm.write_videos(suffix="-con-vfr", vsync="vfr", force=True, speedup=60)
        nfiles = len(mm.tl_videos[0].tl_files)
        m = mm.tl_videos[0]
        f = frames("2019-03-19T13_to_2019-03-19T13-con-vfr.mp4")
        #efs = m.fps_video_max(speedup=60) * mm.tl_videos[0].duration_real().total_seconds()
        logging.info("Write {} and read {}. fps_avg={} fps_max={} "
                     .format(nfiles, f, m.fps_video_avg(speedup=60), m.fps_video_max(speedup=60) / 60))
        #self.assertAlmostEqual(efs, f, msg="Got {} frames, expected {}".format(f, efs), delta=5)


def test_rename(self):
    print(os.getcwd())
    try:
        shutil.rmtree("temp-renamed")
    except Exception as e:
        print (e)
        pass
    shutil.copytree("rename", "temp-renamed")
    mm = VideoMakerDay()
    mm.files_from_glob(["temp-renamed/*.JPG"])
    mm.loadvideos()
    mm.rename_images()


def test_frames(self):
    #f = frames("2019-03-19T13_to_2019-03-19T13-con-cfr.mp4")
    #self.assertEqual(404,f,"Got {} frames instead of expected 404".format(f))
    pass


def frames(video_filename):
    the_call = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=nb_frames",
        "-of",
        "default=nokey=1:noprint_wrappers=1",
        video_filename]
    logging.debug("ffmpeg: {}".format(the_call))
    r = subprocess.check_output(the_call)
    return int(r)


def test_Stamp(self):
    print(os.getcwd())
    try:
        shutil.rmtree("temp-stamped")
    except Exception as e:
        print (e)
        pass
    shutil.copytree("tostamp", "temp-stamped")
    mm = VideoMakerDay()
    mm.files_from_glob(["temp-stamped/*.jpg"])
    mm.loadvideos()
    mm.stamp_images()


def test_FPS(self):
    mm = VideoMakerDay()
    mm.cache = False
    mm.leastImages = 0
    mm.files_from_glob([r"3\*.jpg"])

    #mm.fpsMax = .1
    mm.verbose = True
    mm.loadvideos()
    mm.savevideos()
    print("%s" % mm)
  #  [print(m) for m in  mm.tl_videos]
#        self.assertEqual(len(mm.tl_videos), 3)


def testConcat1(self):
    mm = VideoMakerConcat()
    mm.cache = False
    mm.files_from_glob(["*.jpg"])
    mm.loadvideos()
    mm.savevideos()
    # print("%s"%mm)
    # [print(m) for m in  mm.tl_videos]
    self.assertEqual(len(mm.tl_videos[0].tl_files), 91)


def testConcat2(self):
    mm = VideoMakerConcat()
    mm.files_from_glob([r"**\*.jpg"])
    mm.cache = False
    mm.loadvideos()

    mm.savevideos()
    # print("%s"%mm)
    # [print(m) for m in  mm.tl_videos]
    self.assertEqual(len(mm.tl_videos[0].tl_files), 195)


def testDayMaker(self):
    mm = VideoMakerDay()
    mm.cache = False
    mm.files_from_glob([r"**\*.jpg"])
    mm.loadvideos()
    mm.savevideos()
    # print("%s"%mm)
    # [print(m) for m in  mm.tl_videos]
    self.assertEqual(len(mm.tl_videos), 3)


def testDayHourMaker(self):
    mm = VideoMakerDay()
    mm.files_from_glob([r"**\*.jpg"])
    mm.cache = False
    #mm.day_start_time = datetime.time(8)
    #mm.day_end_time = datetime.time(8)
    mm.verbose = True
    mm.dayStartTime = datetime.time(8)
    mm.dayEndTime = datetime.time(17)
    mm.daySliceLength = datetime.timedelta(hours=3)
    mm.loadvideos()
    mm.savevideos()

    print("%s" % mm)
    # [print(m) for m in  mm.tl_videos]
    self.assertEqual(len(mm.tl_videos), 1)
    self.assertEqual(len(mm.tl_videos[0].tl_files), 122)
    self.assertEqual(
        mm.tl_videos[0].tl_files[29].datetimeTaken.date(),
        datetime.date(
            2015,
            7,
            3))
    self.assertEqual(
        mm.tl_videos[0].tl_files[30].datetimeTaken.date(),
        datetime.date(
            2015,
            7,
            4))


def testMotion(self):
    mm = VideoMakerDay()
    mm.cache = False
    mm.motion = True
    mm.verbose = True
    mm.leastImages = 1

    mm.files_from_glob([r"**\*.jpg"])
    mm.loadvideos()
    mm.sense_motion()
    mm.savevideos()
    print("%s" % mm)
    # [print(m) for m in mm.tl_videos]
    self.assertEqual(len(mm.tl_videos), 3)


if __name__ == "__main__":
    print("Starting unit tests")
    #import sys;sys.argv = ['', 'Test.testHelp']
    unittest.main()
