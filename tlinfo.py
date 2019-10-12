#!/usr/bin/env python
#

from tl import *

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.setLevel(logging.DEBUG)
    logging.basicConfig(format='%(levelname)s:%(message)s')

    parser = argparse.ArgumentParser("Display info on videos")

    parser.add_argument(
        "command",
        choices=[
            'valid',
            'frames',
            'fps'],
        help="Select one of these commands")
    parser.add_argument("input")
    args = (parser.parse_args())
    logger.debug(args)
    try:
        if args.command == "frames":
            print(frames(args.input))
        elif args.command == "fps":
            print(fps(args.input))
        elif args.command == "valid":
            print(valid_video(args.input))
        else:
            pass

    except Exception as e:
        print(e)


