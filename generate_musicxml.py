#!/usr/bin/env python3
"""
Generate a MusicXML file for "Over the Years"
Style: Dream Pop / Shoegaze (harmonic chart export)
Tempo: 80 BPM, Time Signature: 4/4, Key: C Major

This exports:
  - over_the_years.musicxml (full song, one chord per measure, with section labels)
  - segments_xml/*.musicxml (each SONG_STRUCTURE section as its own file)
"""

from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET

# Song structure (one chord symbol per bar)
SONG_STRUCTURE: list[tuple[str, list[str]]] = [
    ("Intro", ["Cmaj7", "Am7", "Fmaj7", "G"]),
    ("Verse 1", ["Cmaj7", "Am7", "Fmaj7", "G", "Cmaj7", "Am7", "Fmaj7", "G"]),
    ("Pre-Chorus", ["Am7", "G", "Fmaj7", "G"]),
    ("Chorus", ["Cmaj7", "Am7", "Fmaj7", "G", "Cmaj7", "Am7", "Fmaj7", "G"]),
    ("Verse 2", ["Cmaj7", "Am7", "Fmaj7", "G", "Cmaj7", "Am7", "Fmaj7", "G"]),
    ("Chorus", ["Cmaj7", "Am7", "Fmaj7", "G", "Cmaj7", "Am7", "Fmaj7", "G"]),
    ("Outro", ["Cmaj7", "Am7", "Fmaj7", "Cmaj7"]),
]

TEMPO_BPM = 80
TIME_NUM = 4
TIME_DEN = 4
KEY_FIFTHS = 0  # C major


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", name.strip().lower()).strip("_")
    return slug or "segment"


def _pretty_xml(elem: ET.Element) -> str:
    # Python 3.9+: ET.indent exists; fall back gracefully.
    try:
        ET.indent(elem, space="  ", level=0)  # type: ignore[attr-defined]
    except Exception:
        pass
    xml = ET.tostring(elem, encoding="utf-8", xml_declaration=True).decode("utf-8")
    doctype = '<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">'
    return xml.replace("?>", "?>\n" + doctype, 1)


def _chord_to_harmony(chord: str) -> tuple[str, int, str]:
    """
    Return (root_step, root_alter, kind_value) for MusicXML <harmony>.
    Supports: Cmaj7, Am7, Fmaj7, G, etc.
    """
    m = re.match(r"^([A-Ga-g])([#b]?)(.*)$", chord.strip())
    if not m:
        raise ValueError(f"Unsupported chord symbol: {chord!r}")

    step = m.group(1).upper()
    accidental = m.group(2)
    qual = m.group(3).lower()

    alter = 0
    if accidental == "#":
        alter = 1
    elif accidental == "b":
        alter = -1

    # Map common qualities to MusicXML kind values
    if qual in ("", "maj", "major"):
        kind = "major"
    elif qual in ("m", "min", "minor"):
        kind = "minor"
    elif qual in ("7", "dom7"):
        kind = "dominant"
    elif qual in ("maj7", "ma7"):
        kind = "major-seventh"
    elif qual in ("m7", "min7"):
        kind = "minor-seventh"
    else:
        # Default to major if unknown; still preserves the root.
        kind = "major"

    return step, alter, kind


def _add_direction_words(measure: ET.Element, text: str) -> None:
    direction = ET.SubElement(measure, "direction", placement="above")
    direction_type = ET.SubElement(direction, "direction-type")
    ET.SubElement(direction_type, "words").text = text


def _add_tempo(measure: ET.Element, bpm: int) -> None:
    direction = ET.SubElement(measure, "direction", placement="above")
    direction_type = ET.SubElement(direction, "direction-type")
    metronome = ET.SubElement(direction_type, "metronome")
    ET.SubElement(metronome, "beat-unit").text = "quarter"
    ET.SubElement(metronome, "per-minute").text = str(bpm)
    ET.SubElement(direction, "sound", tempo=str(bpm))


def _add_harmony(measure: ET.Element, chord_symbol: str) -> None:
    step, alter, kind = _chord_to_harmony(chord_symbol)
    harmony = ET.SubElement(measure, "harmony")
    root = ET.SubElement(harmony, "root")
    ET.SubElement(root, "root-step").text = step
    if alter != 0:
        ET.SubElement(root, "root-alter").text = str(alter)
    ET.SubElement(harmony, "kind").text = kind


def _add_whole_rest(measure: ET.Element, duration_divisions: int) -> None:
    note = ET.SubElement(measure, "note")
    ET.SubElement(note, "rest")
    ET.SubElement(note, "duration").text = str(duration_divisions * TIME_NUM)  # whole = 4 quarters
    ET.SubElement(note, "voice").text = "1"
    ET.SubElement(note, "type").text = "whole"


def build_musicxml(sectioned_chords: list[tuple[str, list[str]]], title: str) -> str:
    """
    Build MusicXML as a string.
    One chord per measure, chord symbol as <harmony>, and a whole rest in the bar.
    Adds section labels at each section start.
    """
    score = ET.Element("score-partwise", version="3.1")

    work = ET.SubElement(score, "work")
    ET.SubElement(work, "work-title").text = title

    identification = ET.SubElement(score, "identification")
    encoding = ET.SubElement(identification, "encoding")
    ET.SubElement(encoding, "software").text = "chord_gensong"

    part_list = ET.SubElement(score, "part-list")
    score_part = ET.SubElement(part_list, "score-part", id="P1")
    ET.SubElement(score_part, "part-name").text = "Chords"

    part = ET.SubElement(score, "part", id="P1")

    # Use quarter-note divisions for simple durations.
    divisions = 1

    measure_no = 1
    first_measure = True
    for section_name, chords in sectioned_chords:
        for i, chord_symbol in enumerate(chords):
            measure = ET.SubElement(part, "measure", number=str(measure_no))

            if first_measure:
                attributes = ET.SubElement(measure, "attributes")
                ET.SubElement(attributes, "divisions").text = str(divisions)

                key = ET.SubElement(attributes, "key")
                ET.SubElement(key, "fifths").text = str(KEY_FIFTHS)
                ET.SubElement(key, "mode").text = "major"

                time = ET.SubElement(attributes, "time")
                ET.SubElement(time, "beats").text = str(TIME_NUM)
                ET.SubElement(time, "beat-type").text = str(TIME_DEN)

                clef = ET.SubElement(attributes, "clef")
                ET.SubElement(clef, "sign").text = "G"
                ET.SubElement(clef, "line").text = "2"

                _add_tempo(measure, TEMPO_BPM)
                first_measure = False

            if i == 0:
                _add_direction_words(measure, section_name)

            _add_harmony(measure, chord_symbol)
            _add_whole_rest(measure, divisions)

            measure_no += 1

    return _pretty_xml(score)


def export_full_song(output_file: str = "over_the_years.musicxml") -> str:
    xml = build_musicxml(SONG_STRUCTURE, title="Over the Years")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(xml)
    return output_file


def export_segments(output_dir: str = "segments_xml") -> list[str]:
    os.makedirs(output_dir, exist_ok=True)
    exported: list[str] = []
    for idx, (section_name, chords) in enumerate(SONG_STRUCTURE, start=1):
        xml = build_musicxml([(section_name, chords)], title=f"Over the Years - {section_name}")
        filename = f"{idx:02d}_{_slugify(section_name)}.musicxml"
        path = os.path.join(output_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(xml)
        exported.append(path)
        print(f"✓ MusicXML segment exported: {path}")
    return exported


def main() -> None:
    print("Generating MusicXML...")
    full = export_full_song("over_the_years.musicxml")
    segs = export_segments("segments_xml")

    total_bars = sum(len(chords) for _, chords in SONG_STRUCTURE)
    duration_seconds = (total_bars * TIME_NUM * 60) / TEMPO_BPM

    print(f"\n✓ MusicXML created: {full}")
    print(f"  Total bars: {total_bars}")
    print(f"  Duration: {duration_seconds:.1f} seconds ({duration_seconds/60:.2f} minutes)")
    print(f"  Segments exported: {len(segs)} files in ./segments_xml/")
    print(r"═══════════════ [  ♫  MUSICXML EXPORT COMPLETE  ♫  ] ═══════════════")


if __name__ == "__main__":
    main()


