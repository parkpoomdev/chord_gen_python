#!/usr/bin/env python3
"""
Generate a MIDI file for "Over the Years" - Dream Pop / Shoegaze style
Tempo: 80 BPM, Time Signature: 4/4, Key: C Major
"""

import os
import re

import mido
from mido import MidiFile, MidiTrack, Message, MetaMessage

# Chord definitions (notes in MIDI format, C4 = 60)
CHORDS = {
    'Cmaj7': [60, 64, 67, 71],  # C, E, G, B
    'Am7': [57, 60, 64, 67],    # A, C, E, G
    'Fmaj7': [53, 57, 60, 64],  # F, A, C, E
    'G': [55, 59, 62],          # G, B, D
}

# Song structure
SONG_STRUCTURE = [
    ('Intro', ['Cmaj7', 'Am7', 'Fmaj7', 'G']),
    ('Verse 1', ['Cmaj7', 'Am7', 'Fmaj7', 'G', 'Cmaj7', 'Am7', 'Fmaj7', 'G']),
    ('Pre-Chorus', ['Am7', 'G', 'Fmaj7', 'G']),
    ('Chorus', ['Cmaj7', 'Am7', 'Fmaj7', 'G', 'Cmaj7', 'Am7', 'Fmaj7', 'G']),
    ('Verse 2', ['Cmaj7', 'Am7', 'Fmaj7', 'G', 'Cmaj7', 'Am7', 'Fmaj7', 'G']),
    ('Chorus', ['Cmaj7', 'Am7', 'Fmaj7', 'G', 'Cmaj7', 'Am7', 'Fmaj7', 'G']),
    ('Outro', ['Cmaj7', 'Am7', 'Fmaj7', 'Cmaj7']),
]

# MIDI settings
TEMPO = 80  # BPM
TICKS_PER_BEAT = 480
BEATS_PER_BAR = 4
TICKS_PER_BAR = TICKS_PER_BEAT * BEATS_PER_BAR

def _slugify(name: str) -> str:
    slug = re.sub(r'[^a-zA-Z0-9]+', '_', name.strip().lower()).strip('_')
    return slug or "segment"


def _format_progression_for_name(chords: list[str], group: int = 4) -> str:
    """
    Format a chord list for use inside a MIDI track name.
    Example: ["Cmaj7","Am7","Fmaj7","G","Cmaj7","Am7","Fmaj7","G"]
      -> "Cmaj7 Am7 Fmaj7 G | Cmaj7 Am7 Fmaj7 G"
    """
    if not chords:
        return ""
    if group <= 0:
        return " ".join(chords)
    parts = []
    for i in range(0, len(chords), group):
        parts.append(" ".join(chords[i : i + group]))
    return " | ".join(parts)


def _append_header(track: MidiTrack) -> None:
    # Set tempo (microseconds per quarter note)
    # 60,000,000 microseconds per minute / BPM = microseconds per quarter note
    tempo = int(60000000 / TEMPO)
    track.append(MetaMessage('set_tempo', tempo=tempo, time=0))

    # Set time signature (4/4)
    track.append(MetaMessage('time_signature', numerator=4, denominator=4, time=0))

    # Set key signature (C Major)
    track.append(MetaMessage('key_signature', key='C', time=0))


def _append_chord_for_one_bar(track: MidiTrack, chord_name: str, velocity: int = 80) -> None:
    chord_notes = CHORDS[chord_name]

    # Note on: all notes at the same tick
    for note in chord_notes:
        track.append(Message('note_on', channel=0, note=note, velocity=velocity, time=0))

    # Note off: first one advances time by a bar, the rest happen at the same tick
    for i, note in enumerate(chord_notes):
        track.append(
            Message(
                'note_off',
                channel=0,
                note=note,
                velocity=0,
                time=TICKS_PER_BAR if i == 0 else 0,
            )
        )


def _append_chords(track: MidiTrack, chords: list[str], start_offset_ticks: int = 0, velocity: int = 80) -> None:
    """Append chord blocks to a track; optionally offset the start in time."""
    if not chords:
        return

    first_chord = True
    for chord_name in chords:
        chord_notes = CHORDS[chord_name]

        # Note on: all notes at the same tick; first chord can be time-offset.
        for j, note in enumerate(chord_notes):
            track.append(
                Message(
                    'note_on',
                    channel=0,
                    note=note,
                    velocity=velocity,
                    time=start_offset_ticks if (first_chord and j == 0) else 0,
                )
            )

        # Note off: first one advances time by a bar, the rest happen at the same tick
        for j, note in enumerate(chord_notes):
            track.append(
                Message(
                    'note_off',
                    channel=0,
                    note=note,
                    velocity=0,
                    time=TICKS_PER_BAR if j == 0 else 0,
                )
            )

        first_chord = False


def build_midi_from_chords(chords: list[str]) -> MidiFile:
    """Create a MIDI file from a list of chord symbols (one chord per bar)."""
    mid = MidiFile(ticks_per_beat=TICKS_PER_BEAT)
    track = MidiTrack()
    mid.tracks.append(track)

    _append_header(track)

    _append_chords(track, chords, start_offset_ticks=0)

    # Safety: ensure all notes are released
    track.append(Message('note_off', channel=0, note=0, velocity=0, time=0))
    return mid


def export_segments(segments_dir: str = "segments") -> list[str]:
    os.makedirs(segments_dir, exist_ok=True)
    exported: list[str] = []

    for idx, (section_name, chord_progression) in enumerate(SONG_STRUCTURE, start=1):
        midi = build_midi_from_chords(chord_progression)
        filename = f"{idx:02d}_{_slugify(section_name)}.mid"
        path = os.path.join(segments_dir, filename)
        midi.save(path)
        exported.append(path)
        print(f"✓ Segment exported: {path}")

    return exported


def export_full_song(output_file: str = "over_the_years.mid") -> str:
    all_chords: list[str] = []
    for section_name, chord_progression in SONG_STRUCTURE:
        print(f"Adding {section_name}: {chord_progression}")
        all_chords.extend(chord_progression)

    mid = build_midi_from_chords(all_chords)
    mid.save(output_file)
    return output_file


def export_full_song_with_markers(output_file: str = "over_the_years_with_markers.mid") -> str:
    """
    Export a full-song MIDI with a marker track that labels section boundaries.
    Many DAWs show these as timeline markers.
    """
    mid = MidiFile(type=1, ticks_per_beat=TICKS_PER_BEAT)

    marker_track = MidiTrack()
    chord_track = MidiTrack()
    mid.tracks.append(marker_track)
    mid.tracks.append(chord_track)

    marker_track.append(MetaMessage('track_name', name='Markers', time=0))
    _append_header(marker_track)

    chord_track.append(MetaMessage('track_name', name='Chords', time=0))

    # Markers at the *start* of each section
    prev_section_bars = 0
    first = True
    for idx, (section_name, chord_progression) in enumerate(SONG_STRUCTURE, start=1):
        marker_track.append(
            MetaMessage(
                'marker',
                text=f"{idx:02d} {section_name} ({len(chord_progression)} bars)",
                time=0 if first else prev_section_bars * TICKS_PER_BAR,
            )
        )
        first = False
        prev_section_bars = len(chord_progression)

    # Chords for the full arrangement
    all_chords: list[str] = []
    for _, chord_progression in SONG_STRUCTURE:
        all_chords.extend(chord_progression)
    _append_chords(chord_track, all_chords, start_offset_ticks=0)

    mid.save(output_file)
    return output_file


def export_full_song_as_section_tracks(output_file: str = "over_the_years_section_tracks.mid") -> str:
    """
    Export a full-song MIDI where each section is its own track, aligned on the
    global timeline. This feels closest to 'split regions' when imported into a DAW.
    """
    mid = MidiFile(type=1, ticks_per_beat=TICKS_PER_BEAT)

    header_track = MidiTrack()
    mid.tracks.append(header_track)
    header_track.append(MetaMessage('track_name', name='Song Info', time=0))
    _append_header(header_track)

    bars_before = 0
    for idx, (section_name, chord_progression) in enumerate(SONG_STRUCTURE, start=1):
        t = MidiTrack()
        mid.tracks.append(t)
        progression_text = _format_progression_for_name(chord_progression, group=4)
        t.append(
            MetaMessage(
                'track_name',
                name=f"{idx:02d} {section_name} - Chord Progression: {progression_text}",
                time=0,
            )
        )

        start_offset = bars_before * TICKS_PER_BAR
        _append_chords(t, chord_progression, start_offset_ticks=start_offset)

        bars_before += len(chord_progression)

    mid.save(output_file)
    return output_file

def main():
    """Main function to generate the MIDI file"""
    print("Generating MIDI file for 'Over the Years'...")
    print(f"Style: Dream Pop / Shoegaze")
    print(f"Tempo: {TEMPO} BPM")
    print(f"Time Signature: 4/4")
    print(f"Key: C Major\n")

    output_file = export_full_song("over_the_years.mid")
    marker_file = export_full_song_with_markers("over_the_years_with_markers.mid")
    tracks_file = export_full_song_as_section_tracks("over_the_years_section_tracks.mid")
    exported_segments = export_segments("segments")

    # Calculate song duration
    total_bars = sum(len(chords) for _, chords in SONG_STRUCTURE)
    duration_seconds = (total_bars * BEATS_PER_BAR * 60) / TEMPO
    
    print(f"\n✓ MIDI file created: {output_file}")
    print(f"✓ Full song w/ markers: {marker_file}")
    print(f"✓ Full song w/ section tracks: {tracks_file}")
    print(f"  Total bars: {total_bars}")
    print(f"  Duration: {duration_seconds:.1f} seconds ({duration_seconds/60:.2f} minutes)")
    print(f"  Segments exported: {len(exported_segments)} files in ./segments/")
    print(r"═══════════════ [  ♪  MIDI EXPORT COMPLETE  ♪  ] ═══════════════")
    
    return output_file

if __name__ == '__main__':
    main()

