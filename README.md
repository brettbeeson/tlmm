# tlmm
Time Lapse Movie Maker in Python using Command Line

## Purpose

Combine a list of image files into a movie. Reads files from glob ("\*.jpg"), and checks EXIF data for dates. Filenames are not used. Creates a H264 encoded video file/s. 

Various options to speedup, drop frames, etc. 

## Install overview

1. Check requirements.txt.
2. ffmpeg with lib264

## Install dependancies on EC2

>python get-pip.py
>pip install exifread
>pip install nptime
>pip install numpy
>pip install Pillow
>wget https://johnvansickle.com/ffmpeg/builds/ffmpeg-git-amd64-static.tar.xz
>tar -xf ffmpeg-git-amd64-static.tar.xz
>cp ffmpeg-git-20190605-amd64-static/ffmpeg /usr/local/bin/

Note: It's a good candidate for a batch-job compute bill model (instead of on-demand)

## Run

>tlmm.py video *.jpg

## Notes

- tlmm.py is self-contained
- other files are tests for motion detection, etc.
