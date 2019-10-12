#!/usr/bin/env python
# NOT DEVELOPED YET. USING TLMM.PY INSTEAD
#
# tlmmd: Daemon to continous process images into movies
#
# - Monitors one directory for files
# - Maintains a sorted list of files' time-taken (via filename or EXIF)
# - Take an "interval" argument (Hour or Day)
# - When the latest file time > last interval boundary:
# ---- Run tlmm.py on batches of files (within intervals) and delete images
# ---- Optionally: join movies together to get a "everything to date" or "everything today" movie

from __future__ import division
import tempfile
from operator import xor
import os
import argparse
import glob
import subprocess
import exifread
from enum import Enum
import datetime  # module!
from datetime import datetime  # class!
from datetime import timedelta  # class!
from datetime import time  # class!
import os.path
import inspect
import sys
import itertools
import nptime
import logging
from nptime import nptime
from PIL import ImageFont
from PIL import Image
from PIL import ImageDraw

from collections import OrderedDict

_LOG_LEVEL_STRINGS = ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG']

logger = logging.getLogger(__name__)


def _log_level_string_to_int(log_level_string):
    if not log_level_string in _LOG_LEVEL_STRINGS:
        message = 'invalid choice: {0} (choose from {1})'.format(
            log_level_string, _LOG_LEVEL_STRINGS)
        raise argparse.ArgumentTypeError(message)

    log_level_int = getattr(logging, log_level_string, logging.INFO)
    # check the logging log_level_choices have not changed from our expected
    # values
    assert isinstance(log_level_int, int)

    return log_level_int


# Get datetime from EXIF
def exif_datetime_taken(filename):  # -> datetime.datetime:
    f = open(filename, 'rb')
    tags = exifread.process_file(f, details=False)
    f.close()
    datetime_taken_exif_str = tags["EXIF DateTimeOriginal"]
    return datetime.strptime(
        str(datetime_taken_exif_str), r'%Y:%m:%d %H:%M:%S')

# Assume filenames are number equal to epoch seconds
# Last restore
def epoch_datetime_taken(filename): # -> datetime.dateime
    seconds_from_epoch_str=""
    for c in os.path.basename(filename):
        if c.isdigit():
            seconds_from_epoch_str = seconds_from_epoch_str + c
    seconds_from_epoch = int(seconds_from_epoch_str)
    return datetime.fromtimestamp(seconds_from_epoch)

#
# Return a datetime. Ignores non-digits.
# length: 14 = 4,2,2,2,2,2
#
def filename_datetime(filename, pattern="%Y%m%d%H%M%S", length=14):
    datetime_digits = ''
    for c in os.path.basename(filename):
        if c.isdigit():
            datetime_digits = datetime_digits + c
    datetime_digits = datetime_digits[0:length]
    return datetime.strptime(datetime_digits, pattern)


def crop(image, top=0, bottom=0, left=0, right=0):
    if bottom == 0:
        bottom = image.shape[0]
    else:
        bottom = -bottom
    if right == 0:
        right = image.shape[1]
    else:
        right = -right

    return image[top:bottom, left:right]


def str_to_class(str):
    return getattr(sys.modules[__name__], str)


def neighborhood(iterable):
    iterator = iter(iterable)
    prev = None
    item = next(iterator)  # throws StopIteration if empty.
    for nextone in iterator:
        yield (prev, item, nextone)
        prev = item
        item = nextone
    yield (prev, item, None)


def defname():
    try:
        return inspect.stack()[1][3]
    except BaseException:
        pass


class VSyncType(Enum):
    vfr = 1
    cfr_pad = 2
    cfr_even = 3

    @staticmethod
    def fromStr(name):
        return getattr(VSyncType, name)

    @staticmethod
    def names():
        return list(map(lambda x: x.name, list(VSyncType)))


class SliceType(Enum):
    Day = 1
    Hour = 2
    DayHour = 3
    Concat = 4

    @staticmethod
    def fromStr(name):
        return getattr(SliceType, name)

    @staticmethod
    def names():
        return list(map(lambda x: x.name, list(SliceType)))
    # names = staticmethod(names_static)


class VideoMaker:
    def __init__(self):
        self.tl_videos = []
        self.speedup = 60
        self.fps_requested = None

        self.file_glob = ""
        self.file_list = []
        self.tl_files = []
        self.motion = False
        self.day_start_time = time(0)
        self.day_end_time = time(23)
        self.day_slice_length = None

    def __str__(self):
        return "{}: videos:{}  SpeedUp:{} FpsRequested:{} day_slice_length:{} file_list:{} ".format(type(self).__name__,
                                                                                                    len(
                                                                                                        self.tl_videos),
                                                                                                    self.speedup,
                                                                                                    self.fps_requested,
                                                                                                    self.day_slice_length,
                                                                                                    len(self.file_list))

    def configure(self, args):
        self.files_from_glob(args.file_glob)
        self.day_start_time = datetime.strptime(
            args.daystarttime, "%H:%M").time()
        self.day_end_time = datetime.strptime(args.dayendtime, "%H:%M").time()
        self.motion = args.motion
        if args.minutesperday:
            self.day_slice_length = datetime.timedelta(
                minutes=args.minutesperday)

    def ls(self):
        s = ""
        for m in self.tl_videos:
            s = s & m.ls()
        return s

    def read_image_times(self):
        self.tl_files = []
        n_errors = 0
        logger.debug("Reading dates of {} files...".format(
            len(self.file_list)))

        for fn in self.file_list:
            # Using second resolution can lead to *variable* intervals. For instance, if the interval is 4.1s,
            # the durations with be 4/300 (0.0133) but then each 10 frames 5/300
            # It's therefore better to use constant frame rate, or to adjust this function
            # to millisecond resolution and/or round
            try:
                try:
                    # Filename date
                    datetime_taken = filename_datetime(fn)
                except ValueError as e:
                    # Try to get EXIF
                    try:
                        datetime_taken = exif_datetime_taken(fn)
                    except KeyError as e:
                        datetime_taken = epoch_datetime_taken(fn)

                tlf = TLFile(fn, datetime_taken)
                self.tl_files.append(tlf)
            except RuntimeError as e:
                n_errors += 1
                print ("Error getting date for %s: %s" % (fn, e))

        logger.debug(
            "Got {} timelapse images from {} files with {} errors".format(len(self.tl_files), len(self.file_list),
                                                                          n_errors))
        if n_errors:
            logger.warn(
                "No dates available for {}/{}. Ignoring them.".format(n_errors, len(self.file_list)))
        return self.tl_files.sort()

    def sense_motion(self):
        logger.info("Sensing motion in {} videos".format(len(self.tl_videos)))
        for tlm in self.tl_videos:
            tlm.sense_motion()

    def files_from_glob(self, file_glob):
        assert not isinstance(file_glob, basestring)
        self.file_list = []
        self.file_glob = file_glob
        for fg in file_glob:
            self.file_list.extend(glob.glob(fg))
        self.file_list.sort()
        logger.info("Processing %d files" % (len(self.file_list)))

    def load_videos(self):
        del (self.tl_videos[:])
        self.read_image_times()

    def write_videos(self, vsync="cfr-even", speedup=None, fps=None,
                     suffix="", force=False, m_interpolate=False, dry_run=False):
        for m in self.tl_videos:
            m.write_video(vsync=vsync, fps=fps, speedup=speedup,
                          suffix=suffix, m_interpolate=m_interpolate,
                          dry_run=dry_run, force=force, )

        if not logger.isEnabledFor(logging.DEBUG):
            m.cleanup()

    def delete_images(self):
        n = 0
        for m in self.tl_videos:
            if m.written:
                for tlf in m.tlFiles:
                    os.unlink(tlf.filename)
                    n += 1
        return n

    def stamp_images(self):
        n = 0
        for m in self.tl_videos:
            for tlf in m.tlFiles:
                tlf.stamp()
                n += 1
        return n

    def rename_images(self):
        n = 0
        for m in self.tl_videos:
            for tlf in m.tlFiles:
                tlf.rename()
                n += 1
        return n


class VideoMakerConcat(VideoMaker):
    def load_videos(self):
        VideoMaker.load_videos(self)
        self.tl_videos.append(TLVideo(self.tl_files))


#
# Make one video per hour
#
class VideoMakerHour(VideoMaker):
    def __str__(self):
        return "{}: videos:{}  SpeedUp:{} file_list:{} range={} to {} motion:{}".format(
            type(self).__name__, len(
                self.tl_videos), self.speedup, len(
                self.file_list), self.day_start_time,
            self.day_end_time, self.motion)

    def ls(self):
        s = ""
        for m in self.tl_videos:
            s += m.ls()
        return s

    def video_duration_real_expected(self):
        return datetime.timedelta(hours=1)

    def load_videos(self):
        VideoMaker.load_videos(self)
        groupedByTimeTLFiles = self.group_by_time(
            self.tl_files)  # ,TimeDelta(1h))

        # @todo s
        # remove out-of-time hours
        for h in groupedByTimeTLFiles:

            logger.debug("VideoMakerHourly: Loading video for {} with {} files from {} total files ".format(h, len(
                groupedByTimeTLFiles[h]), len(self.tl_files)))

            tlm = TLVideo(groupedByTimeTLFiles[h])
            self.tl_videos.append(tlm)
            if len(tlm.tl_files) > 0:
                tlm.video_filename = (datetime.datetime.combine(tlm.tl_files[0].datetimeTaken.date(),
                                                                datetime.time(tlm.tl_files[0].datetimeTaken.hour, 0,
                                                                              0, 0))).strftime("%Y-%m-%dT%H-00-00")

                # pprint.pprint(grouped_tl_files)

    @staticmethod
    def group_by_time(localTLFiles):
        grouped_tl_files = OrderedDict()
        for day_hour, day_files in itertools.groupby(localTLFiles,
                                                     lambda x: datetime.datetime.combine(x.datetimeTaken.date(),
                                                                                         datetime.time(
                                                         x.datetimeTaken.hour, 0, 0,
                                                         0))):
            logger.debug("Hour {}".format(day_hour))
            grouped_tl_files[day_hour] = []
            for tlf in sorted(day_files):
                grouped_tl_files[day_hour].append(tlf)
            #    print ("\t{}".format(tlf.filename))
            # grouped_tl_files = sorted(grouped_tl_files)
        return grouped_tl_files


class VideoMakerDay(VideoMaker):
    def __str__(self):
        return "{}: videos:{} file_list:{} range:{} to {} day_slice_length:{} motion:{}".format(
            type(self).__name__, len(
                self.tl_videos), len(
                self.file_list), self.day_start_time,
            self.day_end_time, self.day_slice_length, self.motion)

    def ls(self):
        s = ""
        for m in self.tl_videos:
            s += m.ls()
        return s

    def load_videos(self):
        VideoMaker.load_videos(self)
        grouped_by_day_tl_files = self.group_by_day(self.tl_files)
        for day in grouped_by_day_tl_files:
            day_files_filtered = self.filter_by_hour(
                grouped_by_day_tl_files[day], self.day_start_time, self.day_end_time)
            logger.info(
                "Loading video for {} with {} filtered files from {} total files ".format(day, len(day_files_filtered),
                                                                                          len(grouped_by_day_tl_files[
                                                                                              day])))
            self.tl_videos.append(TLVideo(day_files_filtered))

    @staticmethod
    def filter_by_hour(localTLFiles, localStartTime=None, localEndTime=None):
        ret = localTLFiles
        logger.debug(
            "Filtering from {} to {}".format(
                localStartTime,
                localEndTime))
        logger.debug("Starting with {} files".format(len(ret)))
        if localStartTime is not None:
            ret = list(
                filter(
                    lambda x: x.datetimeTaken.time() >= localStartTime,
                    ret))
        if localEndTime is not None:
            # print(localEndTime)
            for i in ret:
                ret = list(
                    filter(
                        lambda x: x.datetimeTaken.time() <= localEndTime,
                        ret))
        logger.debug("After end {} files".format(len(ret)))
        return ret

    @staticmethod
    def group_by_day(localTLFiles):
        grouped_tl_files = OrderedDict()
        for day, dayFiles in itertools.groupby(
                localTLFiles, lambda x: x.datetimeTaken.date()):
            # print ("Day {}".format(day))
            grouped_tl_files[day] = []
            for tlf in sorted(dayFiles):
                grouped_tl_files[day].append(tlf)
            #    print ("\t{}".format(tlf.filename))
        # grouped_tl_files = sorted(grouped_tl_files)
        return grouped_tl_files


class VideoDayHour(VideoMakerDay):
    def load_videos(self):
        sliced_tl_files = []
        VideoMaker.load_videos(self)

        grouped_by_day = self.group_by_day(self.tl_files)
        # work out minutesPerDay to be continuous
        if self.day_slice_length is None:
            self.day_slice_length = (nptime.nptime.from_time(self.day_end_time) - nptime.nptime.from_time(
                self.day_start_time)) / len(grouped_by_day)
            logger.info(
                "Autoset day_slice_length to {}".format(
                    self.day_slice_length))

        daily_time_delta = nptime.from_time(
            self.day_end_time) - nptime.from_time(self.day_start_time)
        daily_time_delta = daily_time_delta - self.day_slice_length
        daily_time_delta /= len(grouped_by_day) - 1
        # print(daily_time_delta)
        start = nptime.from_time(self.day_start_time)

        for day in sorted(grouped_by_day.keys()):
            end_date_time = start + self.day_slice_length
            day_tl_files = self.filter_by_hour(
                grouped_by_day[day], start, end_date_time)
            logger.debug("Day {}: {} to {} ({}/{} files)".format(day, start, end_date_time, len(day_tl_files),
                                                                 len(grouped_by_day[day])))
            sliced_tl_files.extend(list(day_tl_files))
            start += daily_time_delta
        sliced_tl_files.sort()
        self.tl_videos.append(TLVideo(sliced_tl_files, self.speedup))
        logger.warn("Warning: calc_gaps not run at __LINE__")
        # self.calc_gaps()


class TLVideo:
    # minutes. Gaps greater than this are considered disjoint
    disjointThreshold = timedelta(hours=1)
    # self.motionTimeDeltaMax = datetime.timedelta(hours=1)  # if longer than
    # this, cannot really compute motion

    def __init__(self, tl_files):
        self.tl_files = tl_files
        self.wrote_to_video_filename = None
        self.calc_gaps()

    def __str__(self):
        return "TLVideo: filename:{} frames:{} spfReal:{:.1f}".format(
            self.default_video_filename(), len(self.tl_files), self.spf_real_avg())

    def ls(self):
        s = ""
        for tlf in self.tl_files:
            s += str(tlf) + "\n"
        return s

    def cleanup(self):
        if self.wrote_to_video_filename:
            try:
                os.unlink(os.path.basename(self.wrote_to_video_filename) + ".images")
                os.unlink(os.path.basename(self.wrote_to_video_filename) + ".ffmpeg")
            except BaseException:
                pass

    # Uses self.TLFiles as a source of images to construct a NEW self.TLFiles with just enough images to achieve videoFPS
    # Only required for VFR, as when using CFR, ffmpeg will drop frames as
    # required
    def selectTLFilesToSuitMaxFPS(self, speedup, fps_upper_bound):
        raise NotImplemented("To check")
        logger.debug("realStart:%s realEnd:%s " % (self.first(), self.last()))
        logger.debug("realDuration:%s files:%d" % (self.last() - self.first(), len(self.tl_files)))
        frameTime = self.first()
        spfVideoToSet = 1 / fps_upper_bound
        spfRealToSet = spfVideoToSet * speedup
        newTLFiles = []
        # Run through real time, stepping per-frame-to-be and find the nearest frame in time to use
        while frameTime < self.last():
            frameTime += datetime.timedelta(seconds=spfRealToSet)
            tlf = min(
                self.tl_files,
                key=lambda x: abs(
                    x.datetimeTaken -
                    frameTime))
            tlf.duration_real = datetime.timedelta(seconds=spfRealToSet)
            # logger.debug("frameTime %s" % frameTime)
            # logger.debug("found %s at %s" % (tlf,tlf.datetimeTaken))
            newTLFiles.append(tlf)
        self.tl_files = newTLFiles

        dv = self.durationVideo()
        logger.info("fps_upper_bound:%f fps_max:%f duration:%s files:%d" % (
            fps_upper_bound, self.fps_video_max(), self.last() - self.first(), len(newTLFiles)))

    # Set duration_real for each frame. This is the time difference between this and the next's frame timeTaken
    # Gaps are used for VFR videos
    def calc_gaps(self):
        if len(self.tl_files) <= 1:
            return
        for prev, item, next_item in neighborhood(self.tl_files):
            if next_item is not None:
                item.duration_real = next_item.datetimeTaken - item.datetimeTaken

            if next_item is None:
                # last item's duration is unknown. assume is equal to
                # penultimates's duration
                item.is_last = True
                item.duration_real = prev.duration_real

            if item.duration_real > self.disjointThreshold:
                # if there is a massive disjoint in the images' datetakens, skip this in the video
                # (ie. set duration_real from BIG to a small value)
                item.duration_real = timedelta(
                    milliseconds=1000)  # (seconds=666)

    # Since frames' time may be disjoint, add the gaps between all frames; see
    # "calc_gaps"
    def duration_real(self):
        dr = timedelta()
        for tlf in self.tl_files:
            dr += tlf.duration_real
        return dr

    def first(self):
        if len(self.tl_files) < 1:
            return None
        return self.tl_files[0].datetimeTaken

    def last(self):
        if len(self.tl_files) < 1:
            return None
        return self.tl_files[-1].datetimeTaken

    def duration_video(self, speedup):
        # Run-around to avoid "TypeError: unsupported operand type(s) for /:
        # 'datetime.timedelta' and 'int'"
        return timedelta(
            seconds=self.duration_real().total_seconds() / speedup)

    def fps_video_max(self, speedup):
        return self.fps_real_max() * speedup

    def fps_video_avg(self, speedup):
        return self.fps_real_avg() * speedup

    def fps_real_avg(self):
        if len(self.tl_files) == 0:
            return 0
        if self.duration_real().total_seconds() == 0:
            return 0
        return len(self.tl_files) / self.duration_real().total_seconds()

    def fps_real_max(self):
        if len(self.tl_files) == 0:
            return 0
        if self.duration_real().total_seconds() == 0:
            return 0
        min_frame_duration = min(
            self.tl_files,
            key=lambda x: x.duration_real).duration_real.total_seconds()
        return 1 / min_frame_duration

    def spf_real_avg(self):
        if self.fps_real_avg() == 0:
            return 0
        return 1 / self.fps_real_avg()

    #
    # Compare image before to present image and mark if present one is quite diff-erent
    #
    def sense_motion(self):
        pass

    def write_video(self, force=False, vsync="cfr-even", video_filename=None, suffix="", m_interpolate=False,
                    dry_run=False, fps=None, speedup=None):

        if len(self.tl_files) < 1:
            logger.warn("No images to write")
            return False
        if not video_filename:
            video_filename = self.default_video_filename(suffix)
        if not force and os.path.isfile(video_filename):
            logger.info("Not overwriting {}".format(video_filename))
            return False
        if vsync == 'vfr':
            # input frame rate is defined by the duration of each frame
            assert not fps, "Cannot specify fps *and* vfr"
            assert speedup, "Must specify speed for vfr"
            list_filename = self.write_images_list_vfr(video_filename, speedup)
            # set to the maximum
            fps = self.fps_video_max(speedup)
            input_parameters = []
        elif vsync == 'cfr-even':
            # assume frames are equally spaced between start and end time
            vsync = 'cfr'
            list_filename = self.write_images_list_cfr(video_filename)
            if fps:
                # use this fps value. calc speedup for reporting only
                speedup = self.duration_real().total_seconds() / len(self.tl_files) * fps
                pass
            elif speedup:
                fps = self.fps_video_avg(speedup)
            else:
                raise RuntimeError("Specify cfr-even with fps *or* speedup")
            input_parameters = ["-r", str(round(fps, 0))]
        elif vsync == 'cfr-padded':
            raise NotImplementedError()
            # use a constant framerate, but pad 'slow' sections to reproduce original intervals
            # use max framerate for fastest section, pad other bits
            vsync = 'cfr'
            list_filename = self.write_images_list_vfr(video_filename, speedup)
            fps = self.fps_video_max(speedup)
            # set the input-frame-rate (images) and output-frame-rate (video) to be the same
            # otherwise defaults to 25 (?)
            # input_parameters = ["-r", str(round(fps,0))]
            input_parameters = []
        else:
            raise KeyError("Unknown type of vsync: {}".format(vsync))
        logger.info("TLVideo.writing:{} speedup:{} fps_video:{} mspf_real/speedup:{:.0f}".format(
            self, speedup, fps, 0 if speedup is None else 1000 * self.spf_real_avg() / speedup))

        dfs = max(5, int(fps / 2.0))  # deflicker size. smooth across 0.5s

        # filter to add 2 seconds to end
        # tpad=stop_mode=clone:stop_duration=2,
        if m_interpolate:
            output_parameters = ["-vf", "deflicker" + "," + "minterpolate"]
            fps *= 2
        else:
            output_parameters = ["-vf", "deflicker"]  # =size=" + str(dfs)

        safe_filenames = "0"  # 0 = disable safe 1 = enable safe

        the_call = ["ffmpeg", "-hide_banner", "-loglevel", "verbose", "-y", "-f", "concat", "-vsync", vsync, "-safe",
                    safe_filenames]  # global
        the_call.extend(input_parameters)
        the_call.extend(["-i", list_filename])  # input frames
        the_call.extend(output_parameters)
        the_call.extend(["-vcodec", "libx264", "-r",
                         str(round(fps, 0)), video_filename])  # output video
        plog = open(os.path.basename(video_filename) + ".ffmpeg", "w")
        plog.write("called: {}\n".format(' '.join(the_call)))
        plog.write("called: {}\n".format(the_call))
        if dry_run:
            r = 0
            logger.info("Dryrun: {}\n".format(' '.join(the_call)))
        else:
            r = subprocess.call(
                the_call,
                stdout=plog,
                stderr=subprocess.STDOUT)

        if r == 0:
            self.wrote_to_video_filename = video_filename
            logger.info("Wrote {} images to {}. fps:{} speedup:{}\n ".format(len(self.tl_files), video_filename, fps,
                                                                                 speedup))
            return True
        else:
            self.wrote_to_video_filename = None
            logger.error(
                "Failed on writing {} images to {}.\n Call:{}\n Return:{}".format(len(self.tl_files), video_filename,
                                                                                  str(the_call), r))
            return False

    def write_images_list_vfr(self, video_filename, speedup):
        f = open(os.path.basename(video_filename) + ".images", 'w')
        for tlf in self.tl_files:
            f.write("file '" + tlf.filename + "'\n")
            f.write(
                "duration " + str(timedelta(seconds=tlf.duration_real.total_seconds() / speedup)) + "\n")
        f.close()
        return os.path.basename(video_filename) + ".images"

    #
    # List of filenames only, without duration. Duration of each frame constant and defined by FPS
    #
    def write_images_list_cfr(self, video_filename):
        f = open(os.path.basename(video_filename) + ".images", 'w')
        for tlf in self.tl_files:
            f.write("file '" + tlf.filename + "'\n")
        f.close()
        return os.path.basename(video_filename) + ".images"

    def default_video_filename(self, suffix=""):
        if len(self.tl_files) == 0:
            bn = "empty"
        else:
            bn = self.tl_files[0].datetimeTaken.strftime("%Y-%m-%dT%H") + "_to_" + self.tl_files[
                -1].datetimeTaken.strftime("%Y-%m-%dT%H")
        return bn + suffix + ".mp4"


class TLFile:
    i = 0  # Simple counter, static
    #
    # Draw a moving circle on the image for continuity in video checking

    def stamp(self):
        assert (os.path.exists(self.filename))
        img = Image.open(self.filename)
        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/freefont/FreeMono.ttf", 20)

        draw.pieslice([(0, 0), (100, 100)], self.ith %
                      360, self.ith %
                      360, fill=None, outline=None)
        draw.arc([(0, 0), (100, 100)], 0, 360)
        w, h = img.size
        # draw.text((  (self.ith*10) % w, h - 10), "*", (255, 255, 255), font=font)
        draw.text((w - 40, h - 40), str(self.ith), (255, 255, 255), font=font)
        draw.text((w - 300, h - 60), self.filename, (255, 255, 255), font=font)
        logger.debug("Stamping: {} : {}x{}".format(self.filename, w, h))
        img.save(self.filename, )

    # Get the exif date and rename the file to that
    def rename(self, pattern="%Y-%m-%dT%H-%M-%S"):
        assert (os.path.exists(self.filename))
        dtt = exif_datetime_taken(self.filename)
        date_filename = os.path.join(os.path.dirname(self.filename),
                                     dtt.strftime(pattern) + os.path.splitext(self.filename)[1])
        logger.debug("Renaming {} to {}".format(self.filename, date_filename))
        os.rename(self.filename, date_filename)

    def __repr__(self):
        return '{}\t\t{}\t\t{}\t{}'.format(self.datetimeTaken, self.duration_real, self.filename,
                                           self.is_first if self.is_first else "    ")

    def __str__(self):
        return '{}\t\t{}\t\t{}\t{}'.format(self.datetimeTaken, self.duration_real, self.filename,
                                           self.is_first if self.is_first else "    ")

    def __init__(self, filename, datetimeTaken, tags=None):
        self.filename = filename
        self.datetimeTaken = datetimeTaken
        self.tags = tags
        TLFile.i += 1
        self.ith = TLFile.i
        self.duration_real = timedelta
        self.is_first = False  # of a sequence
        # of a sequence - there will be gap after (or end)
        self.is_last = False
        self.motion = 0  # 0 to 1

    def __gt__(self, o2):
        return self.datetimeTaken > o2.datetimeTaken

    def __eq__(self, o2):
        return self.datetimeTaken == o2.datetimeTaken
        pass

    def __add__(self, other):
        return self.duration_real + other.duration_real

    def sense_motion(self, prevTLF):
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser("Make timelapse videos")
    parser.add_argument(
        "command",
        choices=[
            'video',
            'rename',
            'addexif',
            'stamp'],
        help="Select one of these commands")
    parser.add_argument("file_glob", nargs='+')
    parser.add_argument('--log-level', default='INFO', dest='log_level', type=_log_level_string_to_int, nargs='?',
                        help='Set the logging output level. {0}'.format(_LOG_LEVEL_STRINGS))
    parser.add_argument("--dryrun", action='store_true', default=False)
    parser.add_argument("--stampimages", action='store_true', default=False)
    parser.add_argument(
        "--force",
        action='store_true',
        default=False,
        help="Force overwrite of existing videos")
    parser.add_argument(
        "--slicetype",
        choices=SliceType.names(),
        default="Concat")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--fps", default=25, type=int,
                       help="Mux images at this Frames Per Second. (Implies --vsync cfr).")
    group.add_argument(
        "--speedup",
        default=None,
        type=int,
        help="Using timestamps, speed up video by this much")
    parser.add_argument("--ignorepartial", action='store_true', default=False,
                        help="Ignore videos without full time range (e.g. 14:00 to 14:59 for hourly")
    parser.add_argument("--deleteimages", action='store_true', default=False,
                        help="After successful video creation, delete the images")
    #parser.add_argument("--fpsmax", default=None, type=int,
    #                    help="Drop frames to meet this fps")
    parser.add_argument("--vsync", default="cfr-even", choices=['cfr-even', 'cfr-padded', 'vfr'], type=str,
                        help="cfr-even uses start and end time, and makes frames are equally spaced. cfr-padded uses maximum framerate and pads slow bits. vfr uses exact time of each frame (less robust)")
    parser.add_argument("--daystarttime", default="00:00", type=str)
    parser.add_argument("--dayendtime", default="23:59", type=str)
    parser.add_argument("--minutesperday", default=None, type=int,
                        help="For hour or dayhour slice types, minutes to show per day")
    parser.add_argument("--motion", action='store_true', default=False,
                        help="Image selection to include only motiony images")
    parser.add_argument("--minterpolate", action='store_true', default=False,
                        help="FFMPEG Filter to motion-blur video to reduce jerkiness. Ya jerk.")
    parser.add_argument("--suffix", default="", type=str)

    args = (parser.parse_args())

    logger.setLevel(args.log_level)
    logger.setLevel(args.log_level)
    logging.basicConfig(format='%(levelname)s:%(message)s')

    mm = str_to_class("VideoMaker" + args.slicetype.title())()
    mm.configure(args)
    mm.load_videos()

    if args.command == "video":
        if mm.motion:
            mm.sense_motion()
        mm.write_videos(suffix=args.suffix, speedup=args.speedup,vsync=args.vsync, fps=args.fps,force=args.force, m_interpolate=args.minterpolate,
                        dry_run=args.dryrun)
    elif args.command == "rename":
        mm.rename_images()
    elif args.command == "addexif":
        raise NotImplemented()
    elif args.command == "stamp":
        mm.stamp_images()
    else:
        pass

    if args.deleteimages:
        i = mm.delete_images()
        logger.info("Deleted {} files...".format(i))
