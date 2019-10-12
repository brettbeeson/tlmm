#!/usr/bin/env python
import traceback

from tl import *


logger = logging.getLogger(__name__)



if __name__ == "__main__":
    parser = argparse.ArgumentParser("Make timelapse videos. Outputs filename(s) of resultant video(s).")
    parser.add_argument(
        "command",
        choices=[
            'video',
            'rename',
            'addexif',
            'stamp',
            'graph',
            'rm'],
        help="Select one of these commands")
    parser.add_argument("file_glob", nargs='+')
    parser.add_argument('--log-level', default='INFO', dest='log_level', type=log_level_string_to_int, nargs='?',
                        help='Set the logging output level. {0}'.format(LOG_LEVEL_STRINGS))
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
    parser.add_argument("--ignorelast", action='store_true', default=False,
                        help="Ignore the last videos which may be incomplete. Only with interval SliceTypes (Day,Hour).")
    group2 = parser.add_mutually_exclusive_group()
    group2.add_argument("--deleteimages", action='store_true', default=False,
                        help="After successful video creation, delete the images")
    group2.add_argument("--moveimages", action='store_true', default=None,
                        help="After successful video creation, move the images to specified directory")
    #parser.add_argument("--fpsmax", default=None, type=int,
    #                    help="Drop frames to meet this fps")
    parser.add_argument("--vsync", default="cfr-even", choices=['cfr-even', 'cfr-padded', 'vfr'], type=str,
                        help="cfr-even uses start and end time, and makes frames are equally spaced. cfr-padded uses maximum framerate and pads slow bits. vfr uses exact time of each frame (less robust)")
    parser.add_argument("--daystarttime", default="00:00", type=str)
    parser.add_argument("--dayendtime", default="23:59", type=str)
    parser.add_argument("--graphinterval", default=10, type=int,help="Using wih graph command. In minutes.")
    parser.add_argument("--minutesperday", default=None, type=int,
                        help="For hour or dayhour slice types, minutes to show per day")
    parser.add_argument("--motion", action='store_true', default=False,
                        help="Image selection to include only motiony images")
    parser.add_argument("--minterpolate", action='store_true', default=False,
                        help="FFMPEG Filter to motion-blur video to reduce jerkiness. Ya jerk.")
    parser.add_argument("--suffix", default="", type=str)
    parser.add_argument("--dest", default="", type=str,help="Destination folder for output. Default is cwd.")

    parser.add_argument("--start", default=None, type=str, help="Date of first image")

    parser.add_argument('--first', default=datetime.min, type=lambda s: datetime.strptime(s, '%Y-%m-%dT%H:%M:%S'), help="First image to consider. Format: 2010-12-01T13:00:01")
    parser.add_argument('--last', default=datetime.max, type=lambda s: datetime.strptime(s, '%Y-%m-%dT%H:%M:%S'),
                        help="Last image to consider. Format: 2010-12-01T13:00:01")

    args = (parser.parse_args())
    logger.setLevel(args.log_level)
    logging.getLogger("tl").setLevel(args.log_level)
    logging.basicConfig(format='%(levelname)s:%(message)s')

    mm = str_to_class("VideoMaker" + args.slicetype.title())()
    mm.configure(args)
    mm.load_videos()

    try:

        if args.command == "video":
            if mm.motion:
                mm.sense_motion()
            mm.write_videos(dest=args.dest, suffix=args.suffix, speedup=args.speedup,vsync=args.vsync, fps=args.fps,force=args.force, m_interpolate=args.minterpolate,
                            dry_run=args.dryrun)
            written_videos = [ m.wrote_to_video_filename for m in mm.tl_videos]
            print ("\n".join(written_videos))
        elif args.command == "rename":
            mm.rename_images()
        elif args.command == "addexif":
            raise NotImplemented()
        elif args.command == "stamp":
            mm.stamp_images()
        elif args.command == "graph":
            mm.graph_intervals(timedelta(minutes=args.graphinterval))
        else:
            pass
        if args.deleteimages:
            i = mm.delete_images()
            logger.info("Deleted {} files...".format(i))
    except BaseException as e:
        logging.exception("Exception")
        #print(e,file=sys.stderr)
        traceback.print_exc(limit=2) # stderr
        sys.exit(1)
    sys.exit(0)
