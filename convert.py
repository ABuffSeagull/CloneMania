#! /bin/env python3
import re
import sys
from argparse import ArgumentParser
from typing import List, Optional, Match, Dict, cast


class Note:
    def __init__(
        self, resolution: float, beat: float, direction: int, duration: float = 0
    ):
        self.beat = beat
        self.direction = direction
        self.tick = round(resolution * beat)
        self.duration = duration

    def __str__(self) -> str:
        return f"Beat: {self.beat}, Direction: {self.direction}, Tick: {self.tick}, Duration: {self.duration}"

    def set_duration(self, resolution: float, ending_beat: float) -> None:
        self.duration = round((ending_beat - self.beat) * resolution)


def reverse_find_direction(arr: List[Note], direction: int) -> Note:
    for note in arr[::-1]:
        if note.direction == direction:
            return note
    print(
        f"Couldn't find a start for a hold, direction: {direction}, current array: {arr}",
        file=sys.stderr,
    )
    exit(1)


parser = ArgumentParser()
parser.add_argument("input_file")
parser.add_argument("-o", "--output", default="notes.chart", help="path of output file")
args = parser.parse_args()

OUTPUT_FILE = open(args.output, mode="w")
stepfile = open(args.input_file).read().strip()

# Setup song info
print("[Song]\r\n{", file=OUTPUT_FILE)

name = cast(Match[str], re.search(r"#TITLE:(.*?);", stepfile)).group(1)
print(f'\tName = "{name}"', file=OUTPUT_FILE)

offset = float(cast(Match[str], re.search(r"#OFFSET:(.*?);", stepfile)).group(1)) * 1000
if offset > 0:
    print(f"\tOffset = {offset}", file=OUTPUT_FILE)
    offset = 0
else:
    print(f"\tOffset = 0", file=OUTPUT_FILE)

RESOLUTION = 192
print(f"\tResolution = {RESOLUTION}", file=OUTPUT_FILE)

print('\tMusicStream = "song.ogg"', file=OUTPUT_FILE)

preview_start = float(
    cast(Match[str], re.search(r"#SAMPLESTART:([0-9.]+);", stepfile)).group(1)
)
preview_length = float(
    cast(Match[str], re.search(r"#SAMPLELENGTH:([0-9.]+);", stepfile)).group(1)
)
print(f"\tPreviewStart = {preview_start}", file=OUTPUT_FILE)
print(f"\tPreviewEnd = {preview_start + preview_length}", file=OUTPUT_FILE)

print("}", file=OUTPUT_FILE)

# Sync track stuff
print("[SyncTrack]\n{", file=OUTPUT_FILE)
print("\t0 = TS 4", file=OUTPUT_FILE)

bpms = cast(Match[str], re.search(r"#BPMS:(.*?);", stepfile)).group(1)
bpm_map: Dict[float, float] = {}
for item in bpms.split(","):
    (start_str, value_str) = item.split("=")
    bpm_map[float(start_str)] = float(value_str)

tick_offset = offset / 1000 / 60 * bpm_map[0] * RESOLUTION


def beats_to_ticks(beats: float) -> int:
    return round(beats * RESOLUTION + tick_offset)


for start, value in bpm_map.items():
    offset = max(tick_offset, 0)
    print(
        f"\t{max(beats_to_ticks(start), 0)} = B {round(float(value) * 1000)}",
        file=OUTPUT_FILE,
    )

print("}", file=OUTPUT_FILE)

stops = cast(Match[str], re.search(r"(?s)#STOPS:(.*?);", stepfile)).group(1)
stops = stops.strip().replace("\n", "")
stops_map: Dict[float, float] = {}
if len(stops) != 0:
    for item in stops.split(","):
        (start_str, value_str) = item.split("=")
        stops_map[float(start_str)] = float(value_str)


def get_stop_offset(current_beat: int) -> float:
    current_bpm = 0.0
    for start, value in bpm_map.items():
        if current_beat >= start:
            current_bpm = value
        else:
            break
    current_offset = 0.0
    for start, value in stops_map.items():
        if current_beat >= start:
            current_offset += value
        else:
            break
    return beats_to_ticks(current_offset * (current_bpm * 60))


# NOTES
note_list: List[Note] = []
bars_full = (
    cast(Match[str], re.search(r"#NOTES.*?(\d{4}.*?);", stepfile, re.DOTALL))
    .group(1)
    .split(",")
)
bars = [single_bar.strip().split() for single_bar in bars_full]

print("[ExpertSingle]\n{\n\t0 = E PART GUITAR\n\t0 = E play", file=OUTPUT_FILE)
for bar_index, single_bar in enumerate(bars):
    metric = 4 / len(single_bar)
    for beat_index, beat in enumerate(single_bar):
        if beat.count("0") == 4:
            continue
        ticks = beats_to_ticks(bar_index * 4 + beat_index * metric)
        for dir_index, isHit in enumerate(beat):
            if isHit == "1" or isHit == "2" or isHit == "4":
                note_list.append(
                    Note(RESOLUTION, bar_index * 4 + beat_index * metric, dir_index)
                )
            elif isHit == "3":
                note = reverse_find_direction(note_list, dir_index)
                note.set_duration(RESOLUTION, bar_index * 4 + beat_index * metric)

for note in note_list:
    tick = round(note.tick + tick_offset)
    print(f"\t{tick} = N {note.direction} {note.duration}", file=OUTPUT_FILE)
    print(f"\t{tick} = N 6 0", file=OUTPUT_FILE)

print("}", file=OUTPUT_FILE)
