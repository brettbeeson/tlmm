#!/usr/bin/env python

# Given a list of files (via a glob), read their dates (from filename or exif) and put them in folder by date
# eg
# filebyday.py *.jpg
# 2001-01-01-11-00-00.jpg
# 2001-01-01-12-00-00.jpg
# 2001-01-02-11-00-00.jpg
# will make:
# |- 2001-01-01
#       - 2001-01-01-11-00-00.jpg
#       - 2001-01-01-12-00-00.jpg
# |- 2001-01-02
#       - 2001-01-02-11-00-00.jpg
#
#

from __future__ import division
import os
import argparse
import glob
import shutil
#import subprocess
import exifread
from enum import Enum
import datetime  # module!
from datetime import datetime  # class!
#from datetime import timedelta  # class!
from datetime import time  # class!
import os.path
#import inspect
import sys
#import itertools
import logging


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
# Last resort
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


def copy_files_by_day(file_list,dest,move):
    tl_files = []
    n_errors = 0
    n_moved = 0
    logger.debug("Reading dates of {} files...".format(len(file_list)))
    for fn in file_list:
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
            # got a date. Move it
            n_moved += 1
            folder_name = os.path.join(dest,str(datetime_taken.date()))
            move_to = os.path.join(folder_name,os.path.basename(fn))
            if not os.path.exists(folder_name):
                os.mkdir(folder_name)
            logger.info("Copying {} to {}".format(fn, folder_name))
            shutil.copyfile(fn,move_to)

            if (move):
                logger.info("Deleting {}".format(fn))
                os.unlink(fn)

        except Exception as e:
            n_errors += 1
            logger.warn ("Error getting date for %s: %s" % (fn, e))

    logger.debug("Got {} dated file from {} files with {} errors".format(n_moved,len(file_list),n_errors))
    if n_errors:
        logger.warn(
            "No dates available for {}/{}. Ignoring them.".format(n_errors, len(file_list)))

def files_from_glob(file_glob):
    #assert not isinstance(file_glob, basestring)
    file_list = []
    
    for fg in file_glob:
        file_list.extend(glob.glob(fg))
    #file_list.sort()
    logger.info("Globbed %d files" % (len(file_list)))
    return file_list

    
if __name__ == "__main__":
    parser = argparse.ArgumentParser("Make timelapse videos")
    parser.add_argument("file_glob", nargs='+')
    parser.add_argument('--log-level', default='WARNING', dest='log_level', type=_log_level_string_to_int, nargs='?',
                        help='Set the logging output level. {0}'.format(_LOG_LEVEL_STRINGS))
    parser.add_argument("--dryrun", action='store_true', default=False)
    parser.add_argument("--move", action='store_true', default=False,
                        help="After successful copy, delete the original")
    parser.add_argument("--dest", default='.',
                        help="root folder to store filed files(!)")

    args = (parser.parse_args())
    logger.setLevel(args.log_level)
    logging.basicConfig(format='%(levelname)s:%(message)s')

    file_list = files_from_glob(args.file_glob)
    if not os.path.exists(args.dest):
        os.mkdir(args.dest)
    copy_files_by_day(file_list, args.dest, args.move)


    