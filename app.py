import os
import subprocess
import json
import io
import tempfile

from litellm import completion
from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    send_file,
    send_from_directory,
)
from midiutil import MIDIFile

app = Flask(__name__)


def find_soundfont():
    """Find a usable soundfont file.

    Search order:
    1. soundfonts.txt — if present, try each uncommented line as a path
       (relative to the project directory). Lines starting with # are skipped.
       The first existing file wins.
    2. Hard-coded local filenames in the project directory.
    3. Common system paths (package-manager-installed soundfonts).
    """
    # 1. User-configurable soundfonts.txt
    soundfonts_txt = "soundfonts.txt"
    if os.path.isfile(soundfonts_txt):
        try:
            with open(soundfonts_txt, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    # Resolve relative to project directory
                    candidate = os.path.normpath(line)
                    if os.path.isfile(candidate):
                        print(f"Soundfont (from soundfonts.txt): {candidate}")
                        return candidate
                    else:
                        print(f"soundfonts.txt: '{line}' not found, skipping")
        except Exception as e:
            print(f"Warning: could not read {soundfonts_txt}: {e}")

    # 2. Project directory (well-known filenames)
    local_candidates = [
        "GeneralUserGS.sf3",
        "GeneralUserGS.sf2",
        "GeneralUser-GS.sf3",
        "GeneralUser-GS.sf2",
    ]
    for sf in local_candidates:
        if os.path.exists(sf):
            return sf

    # Common system paths (installed via package manager)
    system_candidates = [
        "/usr/share/sounds/sf2/FluidR3_GM.sf2",
        "/usr/share/sounds/sf3/MuseScore_General.sf3",
        "/usr/share/sounds/sf2/default-GM.sf2",
        "/usr/share/sounds/sf3/default-GM.sf3",
        "/usr/share/sounds/sf2/TimGM6mb.sf2",
        "/usr/share/sounds/sf3/MuseScore_General_Lite.sf3",
        "/usr/share/soundfonts/FluidR3_GM.sf2",          # Fedora/Arch
        "/usr/share/soundfonts/default.sf2",              # Arch
    ]
    for sf in system_candidates:
        if os.path.exists(sf):
            return sf

    return None


SOUNDFONT = find_soundfont()
if SOUNDFONT:
    print(f"Soundfont: {SOUNDFONT}")
else:
    print("WARNING: No soundfont found. MIDI to WAV conversion will not work.")
    print("Install FluidSynth soundfonts (e.g. 'sudo apt install fluid-soundfont-gm')")
    print("or place a .sf2/.sf3 file in the project directory.")

# --- CONFIGURATION ---

# In-memory store for last debug responses (keyed by variation_seed)
# Only populated when debug mode is enabled. Not persistent.
_debug_responses = {}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/debug_response/<int:variation_seed>")
def get_debug_response(variation_seed):
    """Return the raw LLM response for a given variation (debug mode only)."""
    raw = _debug_responses.get(variation_seed)
    if raw is None:
        return jsonify({"error": "No debug data available"}), 404
    return jsonify({"raw_response": raw})


@app.route("/static/samples/<path:filename>")
def serve_sample(filename):
    """Serve sample audio files from templates/samples directory"""
    return send_from_directory(
        "samples",
        filename,
        mimetype="audio/wav",
    )


@app.route("/static/presets.json")
def serve_presets():
    """Serve presets.json file"""
    return send_file("presets.json", mimetype="application/json")


def build_full_prompt(user_prompt, length_instruction, loop_instruction, variation_instruction):
    """Build the full prompt with complete GM instrument list (for cloud/large models)."""
    return (
        f"""You are a confident composer for music generation.
You specialize in creating musical compositions and melodies using MIDI.
Return as JSON object of tracks, each representing a MIDI track for this description: "{user_prompt}".

Rules:
- Return ONLY the JSON object. Do not add comments (no // or /* */ style comments inside the JSON).
- Each object has 'instrument': Integer 0-127 (General MIDI).
- 'volume': Integer 0-127 (loudness of the track). Balance track volumes accordingly (not all maxed out. For example, use 100 for leads, 80 for pads, and 70 for bass).
- 'notes': Array of objects.
- 'pitch': Integer 0-127 (60 is Middle C).
- 'duration': Float (length in beats).
- 'time': Float (start time in beats).
- {length_instruction}
- 'tempo': Integer (BPM), set on the first track.
- For drum/percussion tracks, set "channel": 9 so drums play correctly.
{loop_instruction}
{variation_instruction}

***
"""
        + GM_INSTRUMENT_LIST
        + """
***

JSON Schema:
{{
    "tracks": [
        {{
            "tempo": 120,
            "instrument": 0,
            "volume": 100,
            "notes": [
                {{"pitch": 60, "duration": 1.0, "time": 0.0}},
                {{"pitch": 64, "duration": 1.0, "time": 1.0}}
            ]
        }},
        {{
            "instrument": 33,
            "volume": 80,
            "notes": [
                {{"pitch": 36, "duration": 2.0, "time": 0.0}}
            ]
        }},
        {{
            "instrument": 118,
            "volume": 90,
            "channel": 9,
            "notes": [
                {{"pitch": 36, "duration": 0.5, "time": 0.0}},
                {{"pitch": 38, "duration": 0.5, "time": 1.0}}
            ]
        }}
    ]
}}
"""
    )


def build_lite_prompt(user_prompt, length_instruction, loop_instruction, variation_instruction):
    """Build a compact prompt for small local models (less tokens, concrete example)."""
    return f"""You create MIDI music as JSON. Return ONLY valid JSON, no markdown, no code fences, no explanation, no comments (no // or /* */ inside the JSON).

Create music for: "{user_prompt}"

{length_instruction}
{loop_instruction}
{variation_instruction}

Each track has: instrument (number), volume (0-127), notes (array of pitch/duration/time).
First track must include tempo (BPM). For drum tracks, add "channel": 9.

Available instruments (number=name):
0=Acoustic Grand Piano, 4=Electric Piano, 5=Electric Piano 2,
11=Vibraphone, 12=Marimba,
16=Hammond Organ, 19=Church Organ, 22=Harmonica,
24=Nylon Guitar, 25=Steel Guitar, 27=Clean Electric Guitar, 29=Overdriven Guitar, 30=Distortion Guitar,
32=Acoustic Bass, 33=Electric Bass (Finger), 38=Synth Bass 1,
40=Violin, 42=Cello, 46=Orchestral Harp, 48=String Ensemble,
52=Choir Aahs,
56=Trumpet, 57=Trombone, 60=French Horn, 61=Brass Section,
65=Alto Sax, 66=Tenor Sax, 71=Clarinet, 73=Flute,
80=Synth Lead (Square), 81=Synth Lead (Sawtooth),
88=Pad (New Age), 89=Pad (Warm),
104=Sitar, 105=Banjo, 108=Kalimba, 114=Steel Drums

Here is a complete example of valid output (a short 2-track piece):
{{
    "tracks": [
        {{
            "tempo": 120,
            "instrument": 0,
            "volume": 100,
            "notes": [
                {{"pitch": 60, "duration": 1.0, "time": 0.0}},
                {{"pitch": 64, "duration": 1.0, "time": 1.0}},
                {{"pitch": 67, "duration": 1.0, "time": 2.0}},
                {{"pitch": 72, "duration": 2.0, "time": 3.0}}
            ]
        }},
        {{
            "instrument": 33,
            "volume": 80,
            "notes": [
                {{"pitch": 36, "duration": 2.0, "time": 0.0}},
                {{"pitch": 36, "duration": 2.0, "time": 2.0}},
                {{"pitch": 43, "duration": 1.0, "time": 4.0}}
            ]
        }}
    ]
}}

Now create a more complex and musical piece for: "{user_prompt}"
Return ONLY the JSON object."""


# Full General MIDI instrument list (kept as a constant to avoid cluttering the function)
GM_INSTRUMENT_LIST = """## General MIDI Instrument List (0-127)

### 1. Piano (0-7)
| # | Instrument |
|---|---|
| 0 | Acoustic Grand Piano |
| 1 | Bright Acoustic Piano |
| 2 | Electric Grand Piano |
| 3 | Honky-tonk Piano |
| 4 | Electric Piano 1 (Rhodes) |
| 5 | Electric Piano 2 |
| 6 | Harpsichord |
| 7 | Clavinet |

### 2. Chromatic Percussion (8-15)
| # | Instrument |
|---|---|
| 8 | Celesta |
| 9 | Glockenspiel |
| 10 | Music Box |
| 11 | Vibraphone |
| 12 | Marimba |
| 13 | Xylophone |
| 14 | Tubular Bells |
| 15 | Dulcimer |

### 3. Organ (16-23)
| # | Instrument |
|---|---|
| 16 | Drawbar Organ (Hammond) |
| 17 | Percussive Organ |
| 18 | Rock Organ |
| 19 | Church Organ |
| 20 | Reed Organ |
| 21 | Accordion |
| 22 | Harmonica |
| 23 | Tango Accordion |

### 4. Guitar (24-31)
| # | Instrument |
|---|---|
| 24 | Acoustic Guitar (Nylon) |
| 25 | Acoustic Guitar (Steel) |
| 26 | Electric Guitar (Jazz) |
| 27 | Electric Guitar (Clean) |
| 28 | Electric Guitar (Muted) |
| 29 | Overdriven Guitar |
| 30 | Distortion Guitar |
| 31 | Guitar Harmonics |

### 5. Bass (32-39)
| # | Instrument |
|---|---|
| 32 | Acoustic Bass |
| 33 | Electric Bass (Finger) |
| 34 | Electric Bass (Pick) |
| 35 | Fretless Bass |
| 36 | Slap Bass 1 |
| 37 | Slap Bass 2 |
| 38 | Synth Bass 1 |
| 39 | Synth Bass 2 |

### 6. Strings (40-47)
| # | Instrument |
|---|---|
| 40 | Violin |
| 41 | Viola |
| 42 | Cello |
| 43 | Contrabass |
| 44 | Tremolo Strings |
| 45 | Pizzicato Strings |
| 46 | Orchestral Harp |
| 47 | Timpani |

### 7. Ensemble (48-55)
| # | Instrument |
|---|---|
| 48 | String Ensemble 1 |
| 49 | String Ensemble 2 |
| 50 | Synth Strings 1 |
| 51 | Synth Strings 2 |
| 52 | Choir Aahs |
| 53 | Voice Oohs |
| 54 | Synth Voice |
| 55 | Orchestra Hit |

### 8. Brass (56-63)
| # | Instrument |
|---|---|
| 56 | Trumpet |
| 57 | Trombone |
| 58 | Tuba |
| 59 | Muted Trumpet |
| 60 | French Horn |
| 61 | Brass Section |
| 62 | Synth Brass 1 |
| 63 | Synth Brass 2 |

### 9. Reed (64-71)
| # | Instrument |
|---|---|
| 64 | Soprano Sax |
| 65 | Alto Sax |
| 66 | Tenor Sax |
| 67 | Baritone Sax |
| 68 | Oboe |
| 69 | English Horn |
| 70 | Bassoon |
| 71 | Clarinet |

### 10. Pipe (72-79)
| # | Instrument |
|---|---|
| 72 | Piccolo |
| 73 | Flute |
| 74 | Recorder |
| 75 | Pan Flute |
| 76 | Blown Bottle |
| 77 | Shakuhachi |
| 78 | Whistle |
| 79 | Ocarina |

### 11. Synth Lead (80-87)
| # | Instrument |
|---|---|
| 80 | Lead 1 (Square) |
| 81 | Lead 2 (Sawtooth) |
| 82 | Lead 3 (Calliope) |
| 83 | Lead 4 (Chiff) |
| 84 | Lead 5 (Charang) |
| 85 | Lead 6 (Voice) |
| 86 | Lead 7 (5th) |
| 87 | Lead 8 (Bass + Lead) |

### 12. Synth Pad (88-95)
| # | Instrument |
|---|---|
| 88 | Pad 1 (New Age) |
| 89 | Pad 2 (Warm) |
| 90 | Pad 3 (Polysynth) |
| 91 | Pad 4 (Choir) |
| 92 | Pad 5 (Bowed) |
| 93 | Pad 6 (Metallic) |
| 94 | Pad 7 (Halo) |
| 95 | Pad 8 (Sweep) |

### 13. Synth SFX (96-103)
| # | Instrument |
|---|---|
| 96 | FX 1 (Rain) |
| 97 | FX 2 (Soundtrack) |
| 98 | FX 3 (Crystal) |
| 99 | FX 4 (Atmosphere) |
| 100 | FX 5 (Brightness) |
| 101 | FX 6 (Goblins) |
| 102 | FX 7 (Echoes) |
| 103 | FX 8 (Sci-Fi) |

### 14. Ethnic (104-111)
| # | Instrument |
|---|---|
| 104 | Sitar |
| 105 | Banjo |
| 106 | Shamisen |
| 107 | Koto |
| 108 | Kalimba |
| 109 | Bagpipe |
| 110 | Fiddle |
| 111 | Shanai |

### 15. Percussive (112-119)
| # | Instrument |
|---|---|
| 112 | Tinkle Bell |
| 113 | Agogo |
| 114 | Steel Drums |
| 115 | Woodblock |
| 116 | Taiko Drum |
| 117 | Melodic Tom |
| 118 | Synth Drum |
| 119 | Reverse Cymbal |

### 16. Sound Effects (120-127)
| # | Instrument |
|---|---|
| 120 | Guitar Fret Noise |
| 121 | Breath Noise |
| 122 | Seashore |
| 123 | Bird Tweet |
| 124 | Telephone Ring |
| 125 | Helicopter |
| 126 | Applause |
| 127 | Gunshot |
"""


def strip_json_comments(text):
    """Remove JavaScript-style // line comments from JSON text.
    Some LLMs (notably Gemini Flash) insert // comments inside JSON output,
    which makes it invalid. This strips them while preserving strings that
    contain // (e.g. URLs like http://example.com).
    """
    result = []
    in_string = False
    escape_next = False
    i = 0
    while i < len(text):
        ch = text[i]
        if escape_next:
            result.append(ch)
            escape_next = False
            i += 1
            continue
        if ch == '\\' and in_string:
            result.append(ch)
            escape_next = True
            i += 1
            continue
        if ch == '"' and not escape_next:
            in_string = not in_string
            result.append(ch)
            i += 1
            continue
        if not in_string and ch == '/' and i + 1 < len(text) and text[i + 1] == '/':
            # Skip until end of line
            while i < len(text) and text[i] != '\n':
                i += 1
            continue
        result.append(ch)
        i += 1
    return ''.join(result)


def extract_json_from_response(raw):
    """Try multiple strategies to extract valid JSON from an LLM response.
    Returns (parsed_dict, error_detail) tuple. error_detail is None on success."""

    # Strategy 1: Direct JSON parse
    try:
        return json.loads(raw), None
    except json.JSONDecodeError:
        pass

    # Strategy 2: Extract from ```json ... ``` code fences
    try:
        start = raw.index("```json") + 7
        end = raw.rindex("```")
        return json.loads(raw[start:end].strip()), None
    except (ValueError, json.JSONDecodeError):
        pass

    # Strategy 3: Extract from ``` ... ``` code fences (without json tag)
    try:
        start = raw.index("```") + 3
        end = raw.rindex("```")
        candidate = raw[start:end].strip()
        # Skip the language tag if present on first line
        if candidate and not candidate.startswith("{"):
            first_brace = candidate.index("{")
            candidate = candidate[first_brace:]
        return json.loads(candidate), None
    except (ValueError, json.JSONDecodeError):
        pass

    # Strategy 4: Find first { and last } (model returned text around JSON)
    try:
        first_brace = raw.index("{")
        last_brace = raw.rindex("}")
        candidate = raw[first_brace:last_brace + 1]
        return json.loads(candidate), None
    except (ValueError, json.JSONDecodeError):
        pass

    # Strategy 5: Find first [ and last ] (model returned array directly)
    try:
        first_bracket = raw.index("[")
        last_bracket = raw.rindex("]")
        candidate = raw[first_bracket:last_bracket + 1]
        parsed = json.loads(candidate)
        if isinstance(parsed, list):
            return {"tracks": parsed}, None
    except (ValueError, json.JSONDecodeError):
        pass

    # Strategy 6: Strip JavaScript-style // comments and retry all strategies.
    # Some models (notably Gemini Flash) insert // comments inside JSON output.
    cleaned = strip_json_comments(raw)
    if cleaned != raw:
        # Direct parse of cleaned text
        try:
            return json.loads(cleaned), None
        except json.JSONDecodeError:
            pass
        # Code fences in cleaned text
        try:
            start = cleaned.index("```json") + 7
            end = cleaned.rindex("```")
            return json.loads(cleaned[start:end].strip()), None
        except (ValueError, json.JSONDecodeError):
            pass
        try:
            start = cleaned.index("```") + 3
            end = cleaned.rindex("```")
            candidate = cleaned[start:end].strip()
            if candidate and not candidate.startswith("{"):
                first_brace = candidate.index("{")
                candidate = candidate[first_brace:]
            return json.loads(candidate), None
        except (ValueError, json.JSONDecodeError):
            pass
        # Brace-matching in cleaned text
        try:
            first_brace = cleaned.index("{")
            last_brace = cleaned.rindex("}")
            candidate = cleaned[first_brace:last_brace + 1]
            return json.loads(candidate), None
        except (ValueError, json.JSONDecodeError):
            pass
        # Array-matching in cleaned text
        try:
            first_bracket = cleaned.index("[")
            last_bracket = cleaned.rindex("]")
            candidate = cleaned[first_bracket:last_bracket + 1]
            parsed = json.loads(candidate)
            if isinstance(parsed, list):
                return {"tracks": parsed}, None
        except (ValueError, json.JSONDecodeError):
            pass

    # All strategies failed - provide diagnostic info
    raw_preview = raw[:200] + ("..." if len(raw) > 200 else "")
    if not raw.strip():
        detail = "LLM returned an empty response."
    elif "{" not in raw and "[" not in raw:
        detail = f"LLM returned plain text (no JSON found): {raw_preview}"
    else:
        # Try to identify the JSON error location
        try:
            # Find the most promising JSON candidate
            start = raw.index("{")
            end = raw.rindex("}") + 1
            json.loads(raw[start:end])
        except json.JSONDecodeError as e:
            detail = f"JSON syntax error: {e.msg} at position {e.pos}. Response preview: {raw_preview}"
        except ValueError:
            detail = f"Could not locate valid JSON boundaries. Response preview: {raw_preview}"
    
    return None, detail


@app.route("/generate_midi", methods=["POST"])
def generate_midi():
    data = request.json
    user_prompt = data.get("prompt")
    loop_mode = data.get("loop", False)
    variation_seed = data.get("variation_seed", 0)
    length_setting = data.get("length", "medium")
    lite_mode = data.get("lite_mode", False)
    llm_settings = data.get("llm_settings", {})
    debug_mode = llm_settings.get("debug", False)

    # Get LLM configuration from client or fallback to server env
    api_key = llm_settings.get("apiKey")
    model_name = llm_settings.get("modelName")
    provider = llm_settings.get("provider", "gemini")
    base_url = llm_settings.get("baseUrl", "").strip()

    if not api_key and provider != "ollama":
        return (
            jsonify({"error": "API key not provided. Please configure in settings."}),
            400,
        )

    # Construct full model name with provider prefix
    if provider == "gemini":
        model_name = f"gemini/{model_name}"
    elif provider == "gemini_direct":
        model_name = f"openai/{model_name}"
        if not base_url:
            base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
    elif provider == "openai":
        model_name = model_name
    elif provider == "anthropic":
        model_name = f"anthropic/{model_name}"
    elif provider == "ollama":
        model_name = f"openai/{model_name}"
        if not base_url:
            base_url = "http://localhost:11434/v1"
        if not api_key:
            api_key = "ollama"  # Ollama doesn't need a real API key
    else:
        model_name = "openai/" + model_name

    # Build loop instruction if enabled
    loop_instruction = ""
    if loop_mode:
        loop_instruction = (
            "- IMPORTANT: Make this a seamless loop. "
            "The last notes should transition naturally back to the first notes. "
            "End on the same chord as the beginning."
        )

    # Add variation instruction for diversity
    variation_instruction = (
        f"- Variation #{variation_seed + 1}: Be creative and make this unique! "
        "Try different rhythms, instruments, or note patterns."
    )

    # Length instruction based on user selection
    length_instructions = {
        "short": "Create a short piece (4-8 bars). Keep it concise but complete.",
        "medium": "Create an engaging piece (8-16 bars).",
        "long": "Create a longer composition (16-32 bars). Develop musical ideas fully.",
        "verylong": "Create an extended composition (32-64 bars). Include development, variation, and multiple sections."
    }
    length_instruction = length_instructions.get(length_setting, length_instructions["medium"])

    # Build prompt based on lite mode setting
    if lite_mode:
        prompt = build_lite_prompt(user_prompt, length_instruction, loop_instruction, variation_instruction)
    else:
        prompt = build_full_prompt(user_prompt, length_instruction, loop_instruction, variation_instruction)

    raw = None  # Store raw LLM response for debug mode

    try:
        # Prepare completion parameters
        completion_params = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "api_key": api_key,
        }

        # Add base_url if provided
        if base_url:
            completion_params["api_base"] = base_url

        # Request JSON output format from providers that support it
        if provider == "ollama":
            completion_params["response_format"] = {"type": "json_object"}

        if debug_mode:
            print(f"[DEBUG] provider={provider}, model={completion_params['model']}, "
                  f"api_base={completion_params.get('api_base', '(none)')}, "
                  f"lite_mode={lite_mode}")

        response = completion(**completion_params)
        raw = (
            response.choices[0]
            .message.content.replace("\\n", "\n")
            .replace("\\", "")
            .strip()
        )

        if debug_mode:
            print(f"[DEBUG LLM RAW] {raw[:2000]}{'...' if len(raw) > 2000 else ''}")
            _debug_responses[variation_seed] = raw

        # Robust JSON extraction with multiple fallback strategies
        midi_data, parse_error = extract_json_from_response(raw)
        if midi_data is None:
            error_msg = f"Failed to parse LLM response as JSON. {parse_error}"
            if debug_mode:
                print(f"[DEBUG PARSE ERROR] {parse_error}")
            resp = {"error": error_msg}
            if debug_mode:
                resp["raw_response"] = raw
            return jsonify(resp), 500

        # Ensure midi_data has tracks
        if isinstance(midi_data, list):
            midi_data = {"tracks": midi_data}
        if not isinstance(midi_data, dict) or "tracks" not in midi_data:
            # Try to find tracks-like structure
            for key in midi_data:
                if isinstance(midi_data[key], list):
                    midi_data = {"tracks": midi_data[key]}
                    break
            else:
                error_msg = f"LLM response is valid JSON but missing 'tracks' key. Found keys: {list(midi_data.keys())}"
                resp = {"error": error_msg}
                if debug_mode:
                    resp["raw_response"] = raw
                return jsonify(resp), 500

        tracks = midi_data.get("tracks", [])
        if not tracks:
            error_msg = "LLM returned an empty tracks array."
            resp = {"error": error_msg}
            if debug_mode:
                resp["raw_response"] = raw
            return jsonify(resp), 500

        # 4. Create MIDI File using MidiUtil
        num_tracks = len(tracks)
        MyMIDI = MIDIFile(num_tracks)

        # Build channel assignments: skip channel 9 for melodic tracks,
        # but use channel 9 for any track the LLM explicitly marked as drums
        available_channels = [ch for ch in range(16) if ch != 9]
        channel_idx = 0

        for track_idx, track_data in enumerate(tracks):
            time = 0  # In beats
            tempo = track_data.get("tempo", 120)
            program = track_data.get("instrument", 0)
            volume = track_data.get("volume", 100)

            # Sanitize program number (must be 0-127)
            program = max(0, min(127, int(program)))

            # Determine channel: use 9 for drum tracks, sequential for others
            explicit_channel = track_data.get("channel")
            if explicit_channel == 9 or explicit_channel == 10:
                # LLM requested drum channel (accept both 9 and 10 as "drum channel")
                channel = 9
            elif program >= 112 and program <= 119:
                # Percussive instruments (112-119) → drum channel
                channel = 9
            else:
                if channel_idx < len(available_channels):
                    channel = available_channels[channel_idx]
                    channel_idx += 1
                else:
                    channel = 0  # Fallback if too many tracks

            # Set tempo only on the first track
            if track_idx == 0:
                MyMIDI.addTempo(track_idx, time, tempo)
            MyMIDI.addProgramChange(track_idx, channel, time, program)

            for note in track_data.get("notes", []):
                try:
                    p = int(note.get("pitch", 60))
                    d = float(note.get("duration", 1))
                    t = float(note.get("time", 0))
                except (ValueError, TypeError):
                    continue  # Skip malformed notes instead of crashing
                # Sanitize pitch (0-127)
                p = max(0, min(127, p))
                # Sanitize duration and time (must be positive)
                d = max(0.1, d)
                t = max(0.0, t)

                MyMIDI.addNote(track_idx, channel, p, t, d, volume)

        # 5. Save to memory buffer
        mem_file = io.BytesIO()
        MyMIDI.writeFile(mem_file)
        mem_file.seek(0)

        response_obj = send_file(
            mem_file,
            mimetype="audio/midi",
            as_attachment=True,
            download_name="gemini_music.mid",
        )

        # Attach debug info as custom header if debug mode is on
        if debug_mode and raw:
            # Truncate for header safety (full response available via debug panel)
            response_obj.headers["X-Debug-Raw-Length"] = str(len(raw))

        return response_obj

    except Exception as e:
        print(f"Error: {e}")
        resp = {"error": str(e)}
        if debug_mode and raw:
            resp["raw_response"] = raw
        return jsonify(resp), 500


def separate_channels_and_render(input_midi, soundfont, output_wav, gain=0.6):
    """
    Convert MIDI to WAV using FluidSynth.
    
    Args:
        input_midi: Path to input MIDI file
        soundfont: Path to soundfont file  
        output_wav: Path to output WAV file
        gain: FluidSynth gain value (0.0-1.0). Lower values prevent clipping.
              Default 0.6 is a safe balance for multi-track pieces.
    """
    command = [
        "fluidsynth",
        "-ni",
        soundfont,
        input_midi,
        "-F",
        output_wav,
        "-r",
        "44100",
        "-g",
        str(gain),
        "-o",
        "synth.polyphony=512",
    ]

    try:
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"Success! Saved to {output_wav}")
        else:
            print("FluidSynth Error:", result.stderr)
    finally:
        if os.path.exists(input_midi):
            os.remove(input_midi)


@app.route("/convert_midi_to_wav", methods=["POST"])
def convert_midi_to_wav():
    """
    Convert MIDI to WAV. Accepts optional 'gain' parameter.
    If not provided, uses default 0.6 for downloads.
    For preview playback, the client can send a custom gain value.
    """
    try:
        if not SOUNDFONT:
            return jsonify({"error": "No soundfont found. Install FluidSynth soundfonts or place a .sf2/.sf3 file in the project directory."}), 500

        # Get the MIDI file from the request
        midi_file = request.files["midi_file"]
        midi_data = midi_file.read()
        
        # Get optional gain parameter (default to 0.6 for downloads)
        gain = float(request.form.get("gain", 0.6))
        # Clamp gain to safe range
        gain = max(0.1, min(1.0, gain))

        # Use unique temp files to avoid race conditions with parallel requests
        with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as tmp_mid:
            tmp_mid.write(midi_data)
            tmp_mid_path = tmp_mid.name
        
        tmp_wav_path = tmp_mid_path.replace(".mid", ".wav")

        # Convert MIDI to WAV with specified gain
        separate_channels_and_render(
            input_midi=tmp_mid_path,
            soundfont=SOUNDFONT,
            output_wav=tmp_wav_path,
            gain=gain,
        )

        # Return the WAV file
        response = send_file(
            tmp_wav_path,
            mimetype="audio/wav",
            as_attachment=True,
            download_name="output.wav",
        )
        
        # Clean up WAV temp file after sending
        @response.call_on_close
        def cleanup():
            if os.path.exists(tmp_wav_path):
                os.remove(tmp_wav_path)
        
        return response

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)
