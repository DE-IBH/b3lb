#!/bin/sh

cd indir

for directory in */; do
  meetingid="${directory%/}"
  echo "MeetingID: $meetingid"
  cd /usr/src/app
  ./make-xges.py indir/${meetingid} outdir/${meetingid}.xges --annotations
  ges-launch-1.0 --load outdir/${meetingid}.xges -o outdir/${meetingid}.mp4
  rm  outdir/${meetingid}.xges
done
