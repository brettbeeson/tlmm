#!/usr/bin/env python


# Module "tl" (Time Lapse)  Details
# -------------------------------
# TLVideos are collections of TLFiles. Each TLFile is a photo with a timestamp and duration.
# Duration is the timedelta to the next frame.
#
# _real suffix is the original images, in real time
# _video suffix is the ... video.
#
# Each video has the following constant values
# - duration_real : end-start frame
# - n_frames : number of frames
# - fps_real_avg : duration_real / n_frames
# - fps_real_max :  1/min(frame_duration)
#
# fps_real_avg is the average. The maximum (fps_real_max) could be higher, as frame intervals can
# be non-homogenous. Imagine photo intervals:
# +    +    +    ++++++    +    +    +    +
# The maximum will be within the +++++, while the average will be +   + (i.e. slightly smaller than typical internal)
#
# Each video has a speedup factor set. This determines the fps_video. This encompasses VFR and CFR video speedup.
# - speedup = length_real / length_video
#           = duration_real * fps_video / nframes
#
# VFR: This is a "compressed" version of the real.
#              : Determined by duration of frames / speedup factor.
#              : fps_video = varies
#
# CFR: This is an idealised version of the real.
# - CFR-EVEN: each frame duration = duration_video / nframes
#             : this evenly spaces frames
#             : fps_video (avg) = speedup * duration_real / n_frames
# - CFR-PADDED    : runs at the maximum frame rate, and pads 'slower' areas with frames
#             : fps_video (max) = speedup * fps_real_max = speedup * 1/min[frame_duration]
#
#

from __future__ import division
import tempfile
from operator import xor
import os
import argparse
import glob
import subprocess
import exifread
import imghdr
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

from ascii_graph import Pyasciigraph    # graph command

from collections import OrderedDict

logger = logging.getLogger(__name__)

LOG_LEVEL_STRINGS = ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG']

def log_level_string_to_int(log_level_string):

    if not log_level_string in LOG_LEVEL_STRINGS:
        message = 'invalid choice: {0} (choose from {1})'.format(
            log_level_string, LOG_LEVEL_STRINGS)
        raise argparse.ArgumentTypeError(message)

    log_level_int = getattr(logging, log_level_string, logging.INFO)
    # check the logging log_level_choices have not changed from our expected
    # values
    assert isinstance(log_level_int, int)

    return log_level_int

def fps(input_filename):
    cl = "ffprobe -v 0 -of csv=p=0 -select_streams v:0 -show_entries stream=r_frame_rate" + " " + input_filename
    # will be 25/1 or 223/1
    output = process_output(cl)
    nom, dom = output.split("/")
    return float(nom) / float(dom)


def valid_video(input_filename):
    try:
        return frames(input_filename)>0
    except OSError as e:
        return False

def frames(input_filename):
    cl = "ffprobe -v error -select_streams v:0 -show_entries stream=nb_frames -of default=nokey=1:noprint_wrappers=1 " + str(input_filename)
    return int(process_output(cl))

def process_output(cl):
    try:
        proc = subprocess.run(cl.split(" "), encoding="UTF-8", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError as e:
        raise OSError("Subprocess failed to run. Command: '" + cl + "' Exception: " + str(e))

    #logger.debug("Command: '" + cl + "' Code: " + str(
    #    proc.returncode) + " Stdout: " + proc.stdout + " Stderr: " + proc.stderr)

    if proc.returncode == 0:
        return str(proc.stdout)
    else:
        raise OSError("Subprocess ran but failed. Command: '" + cl + "' Code: " + str(
            proc.returncode) + " Stdout: " + proc.stdout + " Stderr: " + proc.stderr )

def round_time_down(dt=None, round_to=60):
    if dt is None:
        dt = datetime.datetime.now()
    seconds = (dt - dt.min).seconds
    rounding = (seconds) // round_to * round_to #
    return dt + timedelta(0,rounding-seconds,-dt.microsecond)

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
# If no time is available, use 00:00:00
# length: 14 = 4,2,2,2,2,2
#
def filename_datetime(filename, throw = True):
    datetime_pattern = "%Y%m%d%H%M%S"
    datetime_length = 14
    date_pattern = "%Y%m%d"
    date_length = 8
    datetime_digits = ''
    date_digits = ''

    for c in os.path.basename(filename):
        if c.isdigit():
            datetime_digits = datetime_digits + c
    datetime_digits = datetime_digits[0:datetime_length]
    date_digits = datetime_digits[0:date_length]
    try:
        file_datetime = datetime.strptime(datetime_digits, datetime_pattern)
        return file_datetime
    except ValueError as e:
        try:
            #logger.warning(e)
            file_date_only = datetime.strptime(date_digits, date_pattern)
            return file_date_only
        except ValueError:
            if throw:
                raise
            else:
                return None



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
        self.ignore_last = False
        self.first_image = datetime.min
        self.last_image = datetime.max

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
        self.ignore_last = args.ignorelast
        if args.minutesperday:
            self.day_slice_length = datetime.timedelta(
                minutes=args.minutesperday)
        self.first_image = args.first
        self.last_image = args.last


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

                if (datetime_taken.time() >= self.day_start_time and datetime_taken.time() <= self.day_end_time and
                    datetime_taken >= self.first_image and datetime_taken <= self.last_image):
                    tlf = TLFile(fn, datetime_taken)
                    if tlf.valid():
                        self.tl_files.append(tlf)
                    else:
                        raise Exception("Ignoring invalid image: {}".format(tlf))

            except Exception as e:
                n_errors += 1
                logger.warning("Error getting image %s: %s" % (fn, e))

        logger.debug(
            "Got {} timelapse images from {} files with {} errors".format(len(self.tl_files), len(self.file_list),
                                                                          n_errors))
        if n_errors:
            logger.warning(
                "No dates available for {}/{}. Ignoring them.".format(n_errors, len(self.file_list)))
        return self.tl_files.sort()

    def sense_motion(self):
        logger.info("Sensing motion in {} videos".format(len(self.tl_videos)))
        for tlm in self.tl_videos:
            tlm.sense_motion()

    def files_from_glob(self, file_glob):
        try:
            basestring
        except NameError:
            basestring = str
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

    def check_ignore_last(self):
        if (self.ignore_last and len(self.tl_videos)>0):
            logger.info("Ignoring last item: {}".format(self.tl_videos[-1]))
            del(self.tl_videos[-1])


    def write_videos(self, dest = "", vsync="cfr-even", speedup=None, fps=None,
                     suffix="", force=False, m_interpolate=False, dry_run=False):

        for m in self.tl_videos:
            ret = m.write_video(dest=dest, vsync=vsync, fps=fps, speedup=speedup,
                          suffix=suffix, m_interpolate=m_interpolate,
                          dry_run=dry_run, force=force, )


        if not logger.isEnabledFor(logging.DEBUG):
            m.cleanup()



    def delete_images(self):
        n = 0
        for m in self.tl_videos:
            if m.written:
                for tlf in m.tl_files:
                    os.unlink(tlf.filename)
                    n += 1
        return n

    def stamp_images(self):
        n = 0
        for m in self.tl_videos:
            for tlf in m.tl_files:
                tlf.stamp()
                n += 1
        return n

    def graph_intervals(self,interval):
        for m in self.tl_videos:
            m.graph_intervals(interval)
        return

    def rename_images(self):
        n = 0
        for m in self.tl_videos:
            for tlf in m.tl_files:
                tlf.rename()
                n += 1
        return n


class VideoMakerConcat(VideoMaker):
    def load_videos(self):
        VideoMaker.load_videos(self)
        self.tl_videos.append(TLVideo(self.tl_files))
        self.check_ignore_last()


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
                tlm.video_filename = (datetime.combine(tlm.tl_files[0].datetimeTaken.date(),
                                                                time(tlm.tl_files[0].datetimeTaken.hour, 0,
                                                                              0, 0))).strftime("%Y-%m-%dT%H-00-00")

                # pprint.pprint(grouped_tl_files)
        self.check_ignore_last()

    @staticmethod
    def group_by_time(localTLFiles):
        grouped_tl_files = OrderedDict()
        for day_hour, day_files in itertools.groupby(localTLFiles,
                                                     lambda x: datetime.combine(x.datetimeTaken.date(),
                                                                                         time(
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
            logger.info("Loading video for {} with {} files".format(day, len(grouped_by_day_tl_files[day])))
            self.tl_videos.append(TLVideo(grouped_by_day_tl_files[day]))
        self.check_ignore_last()

    # Not used
    @staticmethod
    def filter_by_hour(localTLFiles, localStartTime=None, localEndTime=None):
        raise NotImplementedError()
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
            day_tl_files = grouped_by_day[day]
            logger.debug("Day {}: {} to {} ({}/{} files)".format(day, start, end_date_time, len(day_tl_files),
                                                                 len(grouped_by_day[day])))
            sliced_tl_files.extend(list(day_tl_files))
            start += daily_time_delta
        sliced_tl_files.sort()
        self.tl_videos.append(TLVideo(sliced_tl_files, self.speedup))
        logger.warning("Warning: calc_gaps not run at __LINE__")
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
    # UNUSED
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



    # Plot ascii frequency of photos per bin (defaults: 1 hour)
    def graph_intervals(self, interval):
        freq = {}
        for tlf in self.tl_files:
            rounded = round_time_down(tlf.datetimeTaken,interval.total_seconds())
            if not rounded in freq:
                freq[rounded] = 0
            freq[rounded] += 1
            #print("{}:{}".format(hour,tlf.datetimeTaken))
        graphable = []
        for h in sorted(freq):
            #print("{}:{}".format(h,freq[h]))
            graphable.append(tuple((h.isoformat(),freq[h])))
            #print (graphable)
        graph = Pyasciigraph()

        for line in graph.graph('Frequency per {}'.format(interval), graphable):
            print(line)


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

    def write_video(self, dest="", force=False, vsync="cfr-even", video_filename=None, suffix="", m_interpolate=False,
                    dry_run=False, fps=None, speedup=None):
        pts_factor = 1
        if len(self.tl_files) < 1:
            logger.warning("No images to write")
            return False
        if not video_filename:
            video_filename = self.default_video_filename(suffix)
        video_filename = os.path.join(dest,video_filename)
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
            # if fps(output) is specified:
            # - and if speedup is not specified, find the implied speedup (= duration_real / duration_video)
            # - and speed is specified, change the video playback speed (via PTS). PTS factor = desired_speedup / implied_speedup
            # if speed is specified:
            # - and nothing else, set output fps to achieve the desired speedup

            if fps:
                if speedup:
                    implied_speedup = self.duration_real().total_seconds() / len(self.tl_files) * fps
                    pts_factor = speedup / implied_speedup
                else:
                    # use this fps value. calc speedup for reporting only
                    speedup = self.duration_real().total_seconds() / len(self.tl_files) * fps
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
        logger.info("TLVideo.writing:{} speedup:{} fps_video:{} video:{}s real:{}s speedup:{}".format(
            self, speedup, fps, self.duration_video(speedup).total_seconds(), self.duration_real().total_seconds(), speedup))

        dfs = max(5, int(fps / 2.0))  # deflicker size. smooth across 0.5s

        # filter to add 2 seconds to end
        # tpad=stop_mode=clone:stop_duration=2,
        if m_interpolate:
            #output_parameters = ["-vf", "deflicker,minterpolate,setpts=PTS*"+pts_factor]
            output_parameters = ["-vf", "deflicker,minterpolate","-preset","veryfast",]
            fps *= 2
        else:
            output_parameters = ["-vf", "deflicker,setpts=PTS*{:.3f}".format(pts_factor),"-preset","veryfast"]

        safe_filenames = "0"  # 0 = disable safe 1 = enable safe
        metadata = [""] # todo
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
            err_msg = "Failed on writing {} images to {}.\n Call:{}\n Return:{}".format(
                len(self.tl_files), video_filename,str(the_call), r)
            #logger.error(err_msg)
            raise RuntimeError(err_msg)


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

    # Quick header check to see if valid
    def valid(self):
        image_header = imghdr.what(self.filename)
        return image_header # i.e. not None and not ""

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
        self.duration_real = timedelta()
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

