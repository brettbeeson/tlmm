#!/usr/bin/env python
#
import traceback

from tl import *
import logging
import dateparser
import argparse

logger = logging.getLogger(__name__)


def unlink_safe(f):
    try:
        os.unlink(f)
        return True
    except BaseException:
        return False


def date_list(start_date, end_date):
    days = []
    delta = end_date - start_date
    for i in range(delta.days + 1):
        days.append((start_date + timedelta(days=i)))
    return days


def find_matching_files(date_list, video_files):
    matches = []
    for d in date_list:
        try:
            # match if filename starts with the date
            match = next(video for video in video_files if d == filename_datetime(video).date())
            matches.append(match)
        except BaseException as e1:
            logger.info("No video for {}".format(d))  # not found

    return matches


def ffmpeg_concat_rel_speed(filenames, filenames_file, output_file, rel_speed):
    # Auto name FIRST_to_LAST
    if output_file is None:
        first_date = filename_datetime(filenames[0]).date()
        last_date = filename_datetime(filenames[-1]).date()
        ext = os.path.splitext(filenames[0])[1]
        output_file = first_date.isoformat() + "_to_" + last_date.isoformat()

    if rel_speed == 1:
        cl = "ffmpeg -hide_banner -y -f concat -safe 0 -i " + filenames_file + " -c copy " + output_file + ext
    else:
        output_file += "_x" + "{0:.1f}".format(rel_speed)
        factor = 1 / rel_speed
        cl = "ffmpeg -hide_banner -y -f concat -safe 0 -i " + filenames_file + " -preset veryfast -filter:v setpts=" + str(
            factor) + "*PTS " + output_file + ext
    the_call = cl.split(" ")
    # use abs path to easily report errors directing user to log
    log_filename = os.path.abspath(os.path.basename(output_file) + ".ffmpeg")
    p_log = open(log_filename, "w")
    p_log.write("called: {}\n".format(' '.join(the_call)))
    logger.info("calling: {}\n".format(' '.join(the_call)))

    r = subprocess.call(
        the_call,
        stdout=p_log,
        stderr=subprocess.STDOUT)
    if r == 0:
        print(output_file + ext)
        unlink_safe(log_filename)
    else:
        raise RuntimeError(
            "Failed on ffmpeg concat. Check log:{} Called:'{}' Return:{}".format(log_filename, ' '.join(the_call), r))


def ffmpeg_concat_abs_speed(input_filenames_file, output_file, abs_speed):
    raise NotImplemented()

def files_from_glob(file_glob):
    try:
        basestring
    except NameError:
        basestring = str
    assert not isinstance(file_glob, basestring)
    file_list = []
    for fg in file_glob:
        file_list.extend(glob.glob(fg))
    file_list.sort()
    logger.info("Globbed  %d files" % (len(file_list)))
    return file_list


if __name__ == "__main__":

    parser = argparse.ArgumentParser("Combine timelapse videos")
    parser.add_argument("start", help="eg. \"2 days ago\", 10/1/2000")
    parser.add_argument("end", help="eg. Today, 10/1/2000")

    parser.add_argument("input_movies", nargs="+", help="All possible movie files to search")
    parser.add_argument("--output", help="Force the output filename, instead of automatically assigned based on dates.")
    speed_group = parser.add_mutually_exclusive_group()
    speed_group.add_argument("--speed-rel", default=1,
                             help="Relative speed multipler. "
                                  "e.g. 1 is no change, 2 is twice as fast, 0.5 is twice as slow.")
    speed_group.add_argument("--speed-abs", default=None,
                             help="Absolute speed (real time / video time)")
    parser.add_argument('--log-level', default='WARNING', dest='log_level', type=log_level_string_to_int, nargs='?',
                        help='Set the logging output level. {0}'.format(LOG_LEVEL_STRINGS))

    args = (parser.parse_args())

    try:
        logging.basicConfig(format='%(levelname)s:%(message)s')
        logger.setLevel(args.log_level)
        logging.getLogger("tl").setLevel(args.log_level)
        start_datetime = dateparser.parse(args.start)
        end_datetime = dateparser.parse(args.end)
        if start_datetime is None or end_datetime is None:
            raise SyntaxError("Couldn't understand dates: {}, {}".format(start_datetime, end_datetime))
        logger.info("Searching {} to {}".format(start_datetime.isoformat(), end_datetime.isoformat()))


        #video_files = glob.glob(args.input_movies)
        video_files = args.input_movies
        invalid_videos = []
        for v in video_files:
            if not valid_video(v) or filename_datetime(v,throw=False) is None:
                invalid_videos.append(v)

        if len(invalid_videos):
            logger.warning("Ignoring {} invalid videos: {}".format(len(invalid_videos), invalid_videos))

        video_files = list(set(video_files) - set(invalid_videos))

        video_files_in_range = \
            [v for v in video_files if start_datetime.date() <= filename_datetime(v).date() <= end_datetime.date()]


        if len(video_files_in_range) < 1:
            logger.debug("No videos found. video_files: {}".format(','.join(video_files)))
            raise RuntimeError("No videos found to concat")
        video_files_in_range.sort() # probably redundant as ls returns in alphabetical order
        logger.info("concat'ing: {}".format('\n'.join(video_files_in_range)))
        videos_filename = 'filelist.txt'
        with open(videos_filename, 'w') as f:
            f.write("# Auto-generated from tlmc.py\n")
            for video in video_files_in_range:
                f.write("file '%s'\n" % str(video))

        if (args.speed_abs is not None):
            ffmpeg_concat_abs_speed(videos_filename, args.output, float(args.speed_abs))
        else:
            ffmpeg_concat_rel_speed(video_files_in_range, videos_filename, args.output, float(args.speed_rel))
        unlink_safe(videos_filename)
    except Exception as e:
        # print(e)
        traceback.print_exc(limit=2)
        exit(1)
