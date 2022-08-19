#!/bin/sh

FOLDER="$1"
shift

EXTENSION="$1"
shift

./make-xges.py $FOLDER/in/ $FOLDER/out/video.xges $@
ges-launch-1.0 --load $FOLDER/out/video.xges -o $FOLDER/out/video.$EXTENSION
