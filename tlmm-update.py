# UNFINISHED!!!!!

import os
import argparse
import glob
import subprocess
import datetime
import os.path
import sys
import itertools

from tlmm import TLMovieMaker, TLMovieMakerConcat,    TLMovieMakerDay, TLMovieMakerDayhour


def get_immediate_subdirectories(a_dir):
    return [name for name in os.listdir(a_dir)
            if os.path.isdir(os.path.join(a_dir, name))]


if __name__ == "__main__":
    parser = argparse.ArgumentParser("Update timelapse movies recursively in the cwd. If AVI file exists, don't make a movie. Pass all supplied arguments to the per-folder command.")
    parser.add_argument("argGLob", nargs='+')


    # args = (parser.parse_args())
for d in get_immediate_subdirectories(os.getcwd()):
    print(d + " : ",end='')
    # find if there is a moive:
    if not glob.glob(os.path.join(d, '*.avi')):
        print("Make a movie!")
    else:
        print("No movie!")
        # if not, make one with d/*



