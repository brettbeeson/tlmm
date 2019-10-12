#!/usr/bin/env python
#

from tl import *
import logging
import dateparser
import argparse

logger = logging.getLogger(__name__)

def date_list(start_date, end_date):
    days = []
    delta = end_date - start_date
    for i in range(delta.days + 1):
        days.append((start_date + timedelta(days=i)))
    return days

def find_files(date_globs):
    matches = []
    match = []
    for date_glob in date_globs:
        match = (glob.glob(date_glob))
        if len(match):
            matches.extend(match)
    return matches

def ffmpeg_concat_rel_speed(filenames_file,output_file,rel_speed):
    #"ffmpeg -f concat -safe 0 -i mylist.txt -filter:v "setpts=0.5*PTS"  outputx2_filter.mp4"
    if (rel_speed ==1):
        cl = "ffmpeg -hidebanner -f concat -safe 0 -i " + filenames_file + " -c copy " + output_file
    else:
        factor = 1/rel_speed
        cl = "ffmpeg -hidebanner -f concat -safe 0 -i " + filenames_file + "-filter:v setpts=" + factor + "*PTS " + output_file
    the_call = cl.split(" ")
    log_filename = os.path.basename(output_file) + ".ffmpeg"
    plog = open(log_filename, "w")
    plog.write("called: {}\n".format(' '.join(the_call)))
    #plog.write("called: {}\n".format(the_call))
    r = subprocess.call(
        the_call,
        stdout=plog,
        stderr=subprocess.STDOUT)
    if r == 0:
        return True
    else:
        logger.error("Failed on ffmpeg concat. Check log:{} Called:'{}' Return:{}".format(log_filename,' '.join(the_call), r))
        return False

def ffmpeg_concat_abs_speed(input_filenames_file,output_file,abs_speed):
    raise NotImplemented()
    the_call = ["ffmpeg", "-hide_banner", "-loglevel", "verbose", "-f", "concat", "-safe","0","-i",input_filenames_file,"-c","copy",output_file]
    #the_call.extend(["-vcodec", "libx264", "-r",                     str(round(fps, 0)), video_filename])  # output video
    log_filename = os.path.basename(output_file) + ".ffmpeg"
    plog = open(log_filename, "w")
    plog.write("called: {}\n".format(' '.join(the_call)))
    #plog.write("called: {}\n".format(the_call))
    r = subprocess.call(
        the_call,
        stdout=plog,
        stderr=subprocess.STDOUT)
    if r == 0:
        return True
    else:
        logger.error("Failed on ffmpeg concat. Check log:{} Called:'{}' Return:{}".format(log_filename,' '.join(the_call), r))
        return False

if __name__ == "__main__":
    logger.setLevel(logging.DEBUG)
    logging.basicConfig(format='%(levelname)s:%(message)s')

    parser = argparse.ArgumentParser("Combine timelapse videos")
    parser.add_argument("start")
    parser.add_argument("end")
    parser.add_argument("output")
    parser.add_argument("--extension", default="mp4")
    speed_group = parser.add_mutually_exclusive_group()
    speed_group.add_argument("--speed-rel", default=1,
                        help="Relative speed multipler. e.g. 1 is no change, 2 is twice as fast, 0.5 is twice as slow.")
    speed_group.add_argument("--speed-abs", default=None,
                             help="Absolute speed (real time / video time)")
    parser.add_argument("--dir", default=".")

    args = (parser.parse_args())


    try:
        start_datetime = dateparser.parse(args.start)
        end_datetime = dateparser.parse(args.end)
        if start_datetime is None or end_datetime is None:
            raise SyntaxError("Couldn't understand dates: {}, {}".format(start_datetime,end_datetime))
        logger.debug (start_datetime)
        logger.debug (end_datetime)
        dates = date_list(start_datetime.date(),end_datetime.date())
        logger.debug(dates)
        date_globs=[]
        for date in dates:
            date_globs.append(os.path.join(args.dir, date.isoformat() + "*." + args.extension))
        logger.debug(date_globs)
        videos = find_files(date_globs)
        logger.debug(videos)
        videos_filename = 'filelist.txt'
        with open(videos_filename,'w') as f:
            f.write("# Auto-generated from tlmc.py\n")
            for video in videos:
                f.write("file '%s'\n" % str(video))
        if (abs_speed is not None):
            ffmpeg_concat_abs_speed(videos_filename, args.output, args.abs_speed)
        else
            ffmpeg_concat_rel_speed(videos_filename, args.output, args.rel_speed)

    except Exception as e:
        print(e)


