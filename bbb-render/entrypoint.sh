#!/bin/sh

./make-xges.py indir/ outdir/video.xges --annotations
ges-launch-1.0 --load outdir/video.xges -o outdir/video.mp4
