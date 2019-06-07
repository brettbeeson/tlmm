mkdir raw
mkdir 1080
mv *.JPG raw
mogrify -path 1080/ -resize 1920x1080\! raw/*.JPG
tlmm.py video --fps 20 --suffix 20fps 1080/*.JPG