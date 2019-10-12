#!/usr/bin/env python
#

import argparse
import dateparser
import subprocess
import exifread
import datetime  # module!
from datetime import datetime  # class!
from datetime import timedelta  # class!
from datetime import time  # class!
import logging
from nptime import nptime
import os

logger = logging.getLogger(__name__)


def round_time_down(dt=None, round_to=60):
    if dt is None:
        dt = datetime.datetime.now()
    seconds = (dt - dt.min).seconds
    rounding = seconds // round_to * round_to
    return dt + timedelta(0,rounding-seconds, -dt.microsecond)


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


if __name__ == "__main__":
    parser = argparse.ArgumentParser("Make timelapse videos",add_help="Generate a list of dates in ISO format (2011-02-28) between two arbitary dates")
    parser.add_argument("start")
    parser.add_argument("end")
    #parser.add_argument('--first', default=datetime.min, type=lambda s: datetime.strptime(s, '%Y-%m-%dT%H:%M:%S'), help="First image to consider. Format: 2010-12-01T13:00:01")
    #arser.add_argument('--last', default=datetime.max, type=lambda s: datetime.strptime(s, '%Y-%m-%dT%H:%M:%S'),
      #                  help="Last image to consider. Format: 2010-12-01T13:00:01")
    args = (parser.parse_args())
    #print(args.first)
    logger.setLevel(logging.DEBUG)
    logging.basicConfig(format='%(levelname)s:%(message)s')
    #settings = {'DATE_ORDER': 'YMD'}

    try:
        start_datetime = dateparser.parse(args.start)
        end_datetime = dateparser.parse(args.end)
        if start_datetime is None or end_datetime is None:
            raise SyntaxError("Couldn't understand dates: {}, {}".format(start_datetime,end_datetime))
        logger.debug (start_datetime)
        logger.debug (end_datetime)
        delta = end_datetime - start_datetime
        for i in range(delta.days + 1):
            day = start_datetime + timedelta(days=i)
            print (day.date())
    except Exception as e:
        print(e)


