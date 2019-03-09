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
    args, unknownargs = parser.parse_known_args()
    movieFolder = os.path.join(os.getcwd(),  "movies")
    print ("Movies Folder = %s" % movieFolder)

for d in get_immediate_subdirectories(os.getcwd()):
    m = d + "_to_" + d + ".avi"
    print("Images in %s, looking for movie %s : " % (d,m), end='')
    # find if there is a moive:
    argstopass = ["py","C:\\Users\\bbeeson\\Dropbox\\IT\\Software\\Custom\\Python\\tlmm.py"] +  unknownargs + ["--moviesRelPath","..\movies","*.jpg"]
    if not glob.glob(os.path.join(movieFolder, m)):
        print("Action!")
        subprocess.run(argstopass,cwd=d)
    else:
        print("Take five!")



