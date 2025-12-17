# chord_gensong

Generate **MIDI** and **MusicXML** chord-chart exports for the song **"Over the Years"** (Dream Pop / Shoegaze vibe).

- **Tempo**: 80 BPM  
- **Time signature**: 4/4  
- **Key**: C Major  

## Files

- `generate_midi.py`
  - Generates:
    - `over_the_years.mid` (full song, single chord track)
    - `over_the_years_with_markers.mid` (full song + section markers)
    - `over_the_years_section_tracks.mid` (**best for DAW import**: one track per section, aligned on the timeline; track names include chord progressions)
    - `segments/*.mid` (one MIDI per section)
- `generate_musicxml.py`
  - Generates:
    - `over_the_years.musicxml` (full song; one chord per bar; section labels)
    - `segments_xml/*.musicxml` (one MusicXML per section)

## Setup

Install dependency (for MIDI):

```bash
python3 -m pip install -r requirements.txt
```

## Generate MIDI

```bash
python3 generate_midi.py
```

## Generate MusicXML

```bash
python3 generate_musicxml.py
```

## Import tips

- Import **`over_the_years_section_tracks.mid`** for the cleanest “split regions” feel (each section is its own track).
- Track names include: `Section Name - Chord Progression: ...`
- When import use **Ctrol + Shift + T** to move all to focus tracked.


