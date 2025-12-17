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
CHORD_ROOT_OCTAVE = 3  # octave for chord playback notes (C3 = 48)
INCLUDE_CHORD_NOTES = True  # if True, write actual chord-tone notes (playback)


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


def _midi_to_pitch(midi_note: int) -> tuple[str, int, int]:
    """
    Convert MIDI note number to MusicXML pitch components: (step, alter, octave).
    Uses sharps for accidentals.
    """
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    name = names[midi_note % 12]
    step = name[0]
    alter = 1 if len(name) == 2 and name[1] == "#" else 0
    octave = (midi_note // 12) - 1
    return step, alter, octave


def _chord_to_midi_notes(chord_symbol: str) -> list[int]:
    """
    Convert a chord symbol into MIDI notes for playback (root-position voicing).
    """
    root_step, root_alter, kind = _chord_to_harmony(chord_symbol)

    step_to_pc = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
    root_pc = step_to_pc[root_step] + root_alter

    # Base root MIDI note
    root_midi = (CHORD_ROOT_OCTAVE + 1) * 12 + root_pc

    intervals_by_kind: dict[str, list[int]] = {
        "major": [0, 4, 7],
        "minor": [0, 3, 7],
        "dominant": [0, 4, 7, 10],
        "major-seventh": [0, 4, 7, 11],
        "minor-seventh": [0, 3, 7, 10],
    }
    intervals = intervals_by_kind.get(kind, [0, 4, 7])
    return [root_midi + i for i in intervals]


def _add_whole_rest(measure: ET.Element, duration_divisions: int) -> None:
    note = ET.SubElement(measure, "note")
    ET.SubElement(note, "rest")
    ET.SubElement(note, "duration").text = str(duration_divisions * TIME_NUM)  # whole = 4 quarters
    ET.SubElement(note, "voice").text = "1"
    ET.SubElement(note, "type").text = "whole"


def _add_chord_notes(measure: ET.Element, chord_symbol: str, duration_divisions: int) -> None:
    """
    Add actual notes for the chord so MusicXML playback/export-to-MIDI includes sound.
    Uses a chord (stacked notes) lasting one full measure.
    """
    midi_notes = _chord_to_midi_notes(chord_symbol)
    duration = duration_divisions * TIME_NUM  # whole measure in quarter divisions

    for i, midi_note in enumerate(midi_notes):
        note = ET.SubElement(measure, "note")
        if i > 0:
            ET.SubElement(note, "chord")
        pitch = ET.SubElement(note, "pitch")
        step, alter, octave = _midi_to_pitch(midi_note)
        ET.SubElement(pitch, "step").text = step
        if alter != 0:
            ET.SubElement(pitch, "alter").text = str(alter)
        ET.SubElement(pitch, "octave").text = str(octave)
        ET.SubElement(note, "duration").text = str(duration)
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
                ET.SubElement(clef, "sign").text = "F" if INCLUDE_CHORD_NOTES else "G"
                ET.SubElement(clef, "line").text = "4" if INCLUDE_CHORD_NOTES else "2"

                _add_tempo(measure, TEMPO_BPM)
                first_measure = False

            if i == 0:
                _add_direction_words(measure, section_name)

            _add_harmony(measure, chord_symbol)
            if INCLUDE_CHORD_NOTES:
                _add_chord_notes(measure, chord_symbol, divisions)
            else:
                _add_whole_rest(measure, divisions)

            measure_no += 1

    return _pretty_xml(score)


def _format_progression_for_name(chords: list[str], group: int = 4) -> str:
    if not chords:
        return ""
    if group <= 0:
        return " ".join(chords)
    parts = []
    for i in range(0, len(chords), group):
        parts.append(" ".join(chords[i : i + group]))
    return " | ".join(parts)


def build_musicxml_section_parts(sectioned_chords: list[tuple[str, list[str]]], title: str) -> str:
    """
    Build MusicXML with one PART per section, aligned to the full-song timeline.
    Measures outside a section are whole rests only; measures inside include <harmony>.
    """
    score = ET.Element("score-partwise", version="3.1")

    work = ET.SubElement(score, "work")
    ET.SubElement(work, "work-title").text = title

    identification = ET.SubElement(score, "identification")
    encoding = ET.SubElement(identification, "encoding")
    ET.SubElement(encoding, "software").text = "chord_gensong"

    # Use quarter-note divisions for simple durations.
    divisions = 1
    total_bars = sum(len(chords) for _, chords in sectioned_chords)

    # part-list
    part_list = ET.SubElement(score, "part-list")
    for idx, (section_name, chords) in enumerate(sectioned_chords, start=1):
        pid = f"P{idx}"
        score_part = ET.SubElement(part_list, "score-part", id=pid)
        prog = _format_progression_for_name(chords, group=4)
        # Keep ASCII-only for broad compatibility.
        ET.SubElement(score_part, "part-name").text = (
            f"{idx:02d} {section_name} - Chord Progression: {prog}"
        )

    # One part per section, aligned on the global bar timeline.
    bars_before = 0
    for idx, (section_name, chords) in enumerate(sectioned_chords, start=1):
        pid = f"P{idx}"
        part = ET.SubElement(score, "part", id=pid)

        start_bar = bars_before  # 0-based index of first bar in this section
        end_bar = start_bar + len(chords)  # exclusive
        bars_before += len(chords)

        for measure_no in range(1, total_bars + 1):
            bar_index = measure_no - 1
            measure = ET.SubElement(part, "measure", number=str(measure_no))

            if measure_no == 1:
                attributes = ET.SubElement(measure, "attributes")
                ET.SubElement(attributes, "divisions").text = str(divisions)

                key = ET.SubElement(attributes, "key")
                ET.SubElement(key, "fifths").text = str(KEY_FIFTHS)
                ET.SubElement(key, "mode").text = "major"

                time = ET.SubElement(attributes, "time")
                ET.SubElement(time, "beats").text = str(TIME_NUM)
                ET.SubElement(time, "beat-type").text = str(TIME_DEN)

                clef = ET.SubElement(attributes, "clef")
                ET.SubElement(clef, "sign").text = "F" if INCLUDE_CHORD_NOTES else "G"
                ET.SubElement(clef, "line").text = "4" if INCLUDE_CHORD_NOTES else "2"

                _add_tempo(measure, TEMPO_BPM)

            # Only emit harmony during the section's bar window.
            if start_bar <= bar_index < end_bar:
                chord_symbol = chords[bar_index - start_bar]
                if bar_index == start_bar:
                    _add_direction_words(measure, section_name)
                _add_harmony(measure, chord_symbol)
                if INCLUDE_CHORD_NOTES:
                    _add_chord_notes(measure, chord_symbol, divisions)
                else:
                    _add_whole_rest(measure, divisions)
            else:
                _add_whole_rest(measure, divisions)

    return _pretty_xml(score)


def export_full_song(output_file: str = "over_the_years.musicxml") -> str:
    xml = build_musicxml(SONG_STRUCTURE, title="Over the Years")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(xml)
    return output_file


def export_full_song_as_section_parts(output_file: str = "over_the_years_section_parts.musicxml") -> str:
    xml = build_musicxml_section_parts(SONG_STRUCTURE, title="Over the Years (Section Parts)")
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
    section_parts = export_full_song_as_section_parts("over_the_years_section_parts.musicxml")
    segs = export_segments("segments_xml")

    total_bars = sum(len(chords) for _, chords in SONG_STRUCTURE)
    duration_seconds = (total_bars * TIME_NUM * 60) / TEMPO_BPM

    print(f"\n✓ MusicXML created: {full}")
    print(f"✓ MusicXML section-parts created: {section_parts}")
    print(f"  Total bars: {total_bars}")
    print(f"  Duration: {duration_seconds:.1f} seconds ({duration_seconds/60:.2f} minutes)")
    print(f"  Segments exported: {len(segs)} files in ./segments_xml/")
    print(r"═══════════════ [  ♫  MUSICXML EXPORT COMPLETE  ♫  ] ═══════════════")


if __name__ == "__main__":
    main()


