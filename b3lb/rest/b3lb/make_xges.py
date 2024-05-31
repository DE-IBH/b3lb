"""
This file is a modified version of https://github.com/plugorgau/bbb-render/blob/master/make-xges.py,
originally created by James Henstridge under the MIT License.

Modified for B3LB special rendering use case.
"""

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstPbutils', '1.0')
gi.require_version('GES', '1.0')
from gi.repository import GLib, GObject, Gst, GstPbutils, GES

from operator import add as operator_add
from collections import namedtuple
from intervaltree import IntervalTree
from os.path import join, realpath
from xml.etree import ElementTree
from rest.models import RecordProfile
from typing import List

# GStreamer's content detection doesn't work well with ElementTree's
# automatically assigned namespace prefixes.
ElementTree.register_namespace("", "http://www.w3.org/2000/svg")


SlideInfo = namedtuple('SlideInfo', ['id', 'width', 'height', 'start', 'end'])
CursorEvent = namedtuple('CursorEvent', ['x', 'y', 'start'])


def file_to_uri(path):
    path = realpath(path)
    return 'file://' + path

class OPTS:
    start: int  # seconds, no in use by b3lb
    end: None  # seconds or None, not in use by b3lb
    width: int = 1920
    height: int = 1080
    webcam_size: int = 25
    crop_webcam: bool = False
    stretch_webcam: bool = False
    backdrop: str
    opening_credits: List[str] = []  # list of file paths, not in use by b3lb
    closing_credits: List[str] = []  # list of file paths, not in use by b3lb
    annotations: bool = False
    basedir: str = ""
    project: str = ""

    def __init__(self, in_dir: str, out_dir: str, record_profile: RecordProfile):
        self.start = 0
        self.end = None
        self.width = record_profile.width
        self.height = record_profile.height
        self.webcam_size = record_profile.webcam_size
        self.crop_webcam = record_profile.crop_webcam
        self.stretch_webcam = record_profile.stretch_webcam
        self.backdrop = record_profile.backdrop
        self.opening_credits = []
        self.closing_credits = []
        self.annotations = record_profile.annotations
        self.basedir = in_dir
        self.project = out_dir

class Presentation:
    def __init__(self, opts: OPTS):
        self.opts = opts
        self.cam_width = round(opts.width * opts.webcam_size / 100)
        self.slides_width = opts.width - self.cam_width

        self.timeline = GES.Timeline.new_audio_video()

        # Get the timeline's two tracks
        self.video_track, self.audio_track = self.timeline.get_tracks()
        if self.video_track.type == GES.TrackType.AUDIO:
            self.video_track, self.audio_track = self.audio_track, self.video_track
        self.project = self.timeline.get_asset()
        self._assets = {}

        self.start_time = round(self.opts.start * Gst.SECOND)
        self.end_time = 0

        # Offset for the opening credits
        self.opening_length = 0

        # Construct the presentation
        self.set_track_caps()
        self.set_project_metadata()
        self.add_webcams()
        self.add_slides()
        self.add_deskshare()

    def _add_layer(self, name):
        layer = self.timeline.append_layer()
        layer.register_meta_string(GES.MetaFlag.READWRITE, 'video::name', name)
        return layer

    def _get_asset(self, path):
        asset = self._assets.get(path)
        if asset is None:
            asset = GES.UriClipAsset.request_sync(file_to_uri(path))
            self.project.add_asset(asset)
            self._assets[path] = asset
        return asset

    @staticmethod
    def _get_dimensions(asset):
        info = asset.get_info()
        video_info = info.get_video_streams()[0]
        return video_info.get_width(), video_info.get_height()

    @staticmethod
    def _constrain(dimensions, bounds):
        width, height = dimensions
        max_width, max_height = bounds
        new_height = round(height * max_width / width)
        if new_height <= max_height:
            return max_width, new_height
        return round(width * max_height / height), max_height

    def _add_clip(self, layer, asset, start, inpoint, duration, posx, posy, width, height, trim_end=True):
        if trim_end:
            # Skip clips entirely after the end point
            if start > self.end_time:
                return
            # Truncate clips that go past the end point
            duration = min(duration, self.end_time - start)

        # Skip clips entirely before the start point
        if start + duration < self.start_time:
            return
        # Rewrite start, inpoint, and duration to account for time skip
        start -= self.start_time
        if start < 0:
            duration += start
            if not asset.is_image():
                inpoint += -start
            start = 0

        # Offset start point by the length of the opening credits
        start += self.opening_length

        clip = layer.add_asset(asset, start, inpoint, duration,
                               GES.TrackType.UNKNOWN)
        for element in clip.find_track_elements(
                self.video_track, GES.TrackType.VIDEO, GObject.TYPE_NONE):
            element.set_child_property("posx", posx)
            element.set_child_property("posy", posy)
            element.set_child_property("width", width)
            element.set_child_property("height", height)
        return clip

    def set_track_caps(self):
        # Set frame rate and audio rate based on webcam capture
        asset = self._get_asset(join(self.opts.basedir, 'video/webcams.webm'))
        info = asset.get_info()

        video_info = info.get_video_streams()[0]
        self.video_track.props.restriction_caps = Gst.Caps.from_string(
            'video/x-raw(ANY), width=(int){}, height=(int){}, '
            'framerate=(fraction){}/{}'.format(
                self.opts.width, self.opts.height,
                video_info.get_framerate_num(),
                video_info.get_framerate_denom()))

        audio_info = info.get_audio_streams()[0]
        self.audio_track.props.restriction_caps = Gst.Caps.from_string(
            'audio/x-raw(ANY), rate=(int){}, channels=(int){}'.format(
                audio_info.get_sample_rate(), audio_info.get_channels()))

        # Set start and end time from options
        if not self.opts.end:
            self.end_time = asset.props.duration
        else:
            self.end_time = round(self.opts.end * Gst.SECOND)

        # Add an encoding profile for the benefit of Pitivi
        profile = GstPbutils.EncodingContainerProfile.new('MP4', 'bbb-render encoding profile', Gst.Caps.from_string('video/quicktime,variant=iso'))
        profile.add_profile(GstPbutils.EncodingVideoProfile.new(Gst.Caps.from_string('video/x-h264,profile=high'), None, self.video_track.props.restriction_caps, 0))
        profile.add_profile(GstPbutils.EncodingAudioProfile.new(Gst.Caps.from_string('audio/mpeg,mpegversion=4,base-profile=lc'), None, self.audio_track.props.restriction_caps, 0))
        self.project.add_encoding_profile(profile)

    def set_project_metadata(self):
        doc = ElementTree.parse(join(self.opts.basedir, 'metadata.xml'))
        name = doc.find('./meta/name')
        if name is not None:
            self.project.register_meta_string(
                GES.MetaFlag.READWRITE, 'name', name.text.strip())

    def add_webcams(self):
        layer = self._add_layer('Camera')
        asset = self._get_asset(join(self.opts.basedir, 'video/webcams.webm'))
        dims = self._get_dimensions(asset)
        if self.opts.stretch_webcam or self.opts.crop_webcam:
            dims = (dims[0] * 16/12, dims[1])
        width, height = self._constrain(dims, (self.cam_width, self.opts.height))
        clip = self._add_clip(layer, asset, 0, 0, asset.props.duration, self.opts.width - width, 0, width, height)

        if self.opts.crop_webcam:
            effect = GES.Effect.new('aspectratiocrop aspect-ratio=16/9')
            clip.add(effect)

    def add_slides(self):
        layer = self._add_layer('Slides')
        doc = ElementTree.parse(join(self.opts.basedir, 'shapes.svg'))
        slides = {}
        slide_time = IntervalTree()
        for img in doc.iterfind('./{http://www.w3.org/2000/svg}image[@class="slide"]'):
            info = SlideInfo(
                id=img.get('id'),
                width=int(img.get('width')),
                height=int(img.get('height')),
                start=round(float(img.get('in')) * Gst.SECOND),
                end=round(float(img.get('out')) * Gst.SECOND),
            )
            slides[info.id] = info
            slide_time.addi(info.start, info.end, info)

            # Don't bother creating an asset for out of range slides
            if info.end < self.start_time or info.start > self.end_time:
                continue

            path = img.get('{http://www.w3.org/1999/xlink}href')
            # If this is a "deskshare" slide, don't show anything
            if path.endswith('/deskshare.png'):
                continue

            asset = self._get_asset(join(self.opts.basedir, path))
            width, height = self._constrain(self._get_dimensions(asset), (self.slides_width, self.opts.height))
            self._add_clip(layer, asset, info.start, 0, info.end - info.start, 0, 0, width, height)

        # If we're not processing annotations, then we're done.
        if not self.opts.annotations:
            return

        cursor_layer = self._add_layer('Cursor')
        # Move above the slides layer
        self.timeline.move_layer(cursor_layer, cursor_layer.get_priority() - 1)
        dot = self._get_asset('rest/b3lb/dot.png')
        dot_width, dot_height = self._get_dimensions(dot)
        cursor_doc = ElementTree.parse(join(self.opts.basedir, 'cursor.xml'))
        events = []
        for event in cursor_doc.iterfind('./event'):
            x, y = event.find('./cursor').text.split()
            start = round(float(event.attrib['timestamp']) * Gst.SECOND)
            events.append(CursorEvent(float(x), float(y), start))

        for i, pos in enumerate(events):
            # negative positions are used to indicate that no cursor
            # should be displayed.
            if pos.x < 0 and pos.y < 0:
                continue

            # Show cursor until next event or if it is the last event,
            # the end of recording.
            if i + 1 < len(events):
                end = events[i + 1].start
            else:
                end = self.end_time

            # Find the width/height of the slide corresponding to this
            # point in time
            info_list = [i.data for i in slide_time.at(pos.start)]
            if info_list:
                info = info_list[0]
                width, height = self._constrain(
                    (info.width, info.height),
                    (self.slides_width, self.opts.height))

                self._add_clip(cursor_layer, dot, pos.start, 0, end - pos.start, round(width*pos.x - dot_width/2), round(height*pos.y - dot_height / 2), dot_width, dot_height)

        layer = self._add_layer('Annotations')
        # Move above the slides layer
        self.timeline.move_layer(layer, layer.get_priority() - 1)

        for canvas in doc.iterfind('./{http://www.w3.org/2000/svg}g[@class="canvas"]'):
            info = slides[canvas.get('image')]
            t = IntervalTree()
            for index, shape in enumerate(canvas.iterfind('./{http://www.w3.org/2000/svg}g[@class="shape"]')):
                shape.set('style', shape.get('style').replace(
                    'visibility:hidden;', ''))
                timestamp = round(float(shape.get('timestamp')) * Gst.SECOND)
                undo = round(float(shape.get('undo')) * Gst.SECOND)
                if undo < 0:
                    undo = info.end

                # Clip timestamps to slide visibility
                start = min(max(timestamp, info.start), info.end)
                end = min(max(undo, info.start), info.end)

                # Don't bother creating annotations for out of range times
                if end < self.start_time or start > self.end_time:
                    continue

                t.addi(start, end, [(index, shape)])

            t.split_overlaps()
            t.merge_overlaps(strict=True, data_reducer=operator_add)
            for interval_index, interval in enumerate(sorted(t)):
                svg = ElementTree.Element('{http://www.w3.org/2000/svg}svg')
                svg.set('version', '1.1')
                svg.set('width', '{}px'.format(info.width))
                svg.set('height', '{}px'.format(info.height))
                svg.set('viewBox', '0 0 {} {}'.format(info.width, info.height))

                # We want to discard all but the last version of each
                # shape ID, which requires two passes.
                shapes = sorted(interval.data)
                shape_index = {}
                for index, shape in shapes:
                    shape_index[shape.get('shape')] = index
                for index, shape in shapes:
                    if shape_index[shape.get('shape')] != index: continue
                    svg.append(shape)

                path = join(self.opts.basedir, 'annotations-{}-{}.svg'.format(info.id, interval_index))
                with open(path, 'wb') as fp:
                    fp.write(ElementTree.tostring(svg, xml_declaration=True))

                asset = self._get_asset(path)
                width, height = self._constrain((info.width, info.height), (self.slides_width, self.opts.height))
                self._add_clip(layer, asset, interval.begin, 0, interval.end - interval.begin, 0, 0, width, height)

    def add_deskshare(self):
        doc = ElementTree.parse(join(self.opts.basedir, 'deskshare.xml'))
        events = doc.findall('./event')
        if len(events) == 0:
            return

        layer = self._add_layer('Deskshare')
        asset = self._get_asset(join(self.opts.basedir, 'deskshare/deskshare.webm'))
        width, height = self._constrain(self._get_dimensions(asset), (self.slides_width, self.opts.height))
        duration = asset.props.duration
        for event in events:
            start = round(float(event.get('start_timestamp')) * Gst.SECOND)
            end = round(float(event.get('stop_timestamp')) * Gst.SECOND)
            # Trim event to duration of video
            if start > duration:
                continue
            end = min(end, duration)
            self._add_clip(layer, asset, start, start, end - start, 0, 0, width, height)

    def save(self):
        self.timeline.commit_sync()
        self.timeline.save_to_uri(file_to_uri(self.opts.project), None, True)


def render_xges(in_dir: str, out_dir: str, record_profile: RecordProfile):
    opts = OPTS(in_dir, out_dir, record_profile)
    Gst.init(None)
    GES.init()
    p = Presentation(opts)
    p.save()
