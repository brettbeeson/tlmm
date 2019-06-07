# tlmm
Time Lapse Movie Maker in Python using Command Line

## Purpose

Combine a list of image files into a movie. Reads files from glob ("\*.jpg"), and checks EXIF data for dates. Filenames are not used. Creates a H264 encoded video file/s. 

Various options to speedup, drop frames, etc. 

## Install

1. Check requirements.txt.
2. ffmpeg with lib264

## Run

>tlmm.py *.jpg

## Notes

- tlmm.py is self-contained
- other files are tests for motion detection, etc.
