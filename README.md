# MIDI Music Generator (Fork)

An AI music generator that creates MIDI compositions from text prompts using LLMs.

This is a fork of [addy999/midi-music-generator](https://github.com/addy999/midi-music-generator) with the following changes:

- **Preset system** — The original 12 hardcoded preset buttons have been replaced with a hierarchical two-dropdown menu (category → preset) powered by an external `presets.json` file. Includes 35 ready-made presets across multiple categories.
- **Additional LLM providers** — Added Gemini (Direct API) and Ollama (Local) as built-in provider options alongside the originals.
- **Lite mode** — A shorter, optimized prompt for small local models (Ollama). Reduces token count by ~80% while including a concrete JSON example to improve output reliability.
- **Debug mode** — Shows the raw LLM response for troubleshooting failed generations. Useful when testing different models.
- **Preset Editor** — An optional companion tool for creating and managing presets via a browser-based GUI.
- **Reliable drum tracks** — Drum and percussion instruments are correctly routed to MIDI channel 10, so generated compositions include working drum parts.
- **Bug fixes and improvements** — Robust JSON parsing, comment stripping, and more. See [CHANGELOG.md](CHANGELOG.md) for details.

## Screenshots

![Main UI](screenshots/main_ui.png)

![Preset menu](screenshots/main_preset_menu.png)

## Examples

The `samples/` folder contains example compositions generated with this fork, including both MIDI and WAV files. See [`samples/README.md`](samples/README.md) for details on which models and soundfonts were used.

## Features

- 🎵 Generate MIDI music from natural language descriptions
- 🔄 Loop mode for seamless repeating tracks
- 🎹 Supports all General MIDI instruments (0-127)
- 🎼 Multi-track compositions with correct drum channel routing
- 🔊 MIDI to WAV conversion with FluidSynth
- 🤖 Works with multiple LLM providers (Gemini, OpenAI, Anthropic, Ollama)
- ⚡ Lite mode — optimized prompt for small local models
- 🔍 Debug mode — inspect raw LLM responses for troubleshooting

## Setup

> **Note:** These instructions are written for Linux (tested on Linux Mint / Ubuntu). The application may work on other platforms, but the commands below (especially `apt install`, `source venv/bin/activate`) are Linux-specific.

### Requirements

- Python 3.10+
- [FluidSynth](https://www.fluidsynth.org/) with a General MIDI soundfont (required for MIDI → WAV conversion)

### Installation

```bash
git clone https://github.com/Zeamar/midi-music-generator.git
cd midi-music-generator
python3 -m venv venv
source venv/bin/activate
pip3 install flask litellm midiutil
```

#### FluidSynth and soundfonts

FluidSynth is needed for converting generated MIDI files to playable WAV audio. Without it, you can still generate and download MIDI files.

On Debian/Ubuntu/Mint:
```bash
sudo apt install fluidsynth fluid-soundfont-gm
```

The app automatically detects soundfont files — it first checks the project directory for known soundfont filenames, then checks common system paths (`/usr/share/sounds/sf2/`, `/usr/share/sounds/sf3/`, etc.). If you have FluidSynth installed with its default soundfonts, it should work out of the box.

#### Choosing a specific soundfont (`soundfonts.txt`)

If you have multiple soundfonts and want to control which one is used, create a `soundfonts.txt` file in the project root. Each line is a soundfont path (relative to the project directory). Lines starting with `#` are comments. The first uncommented file that exists is used:

```
# My soundfonts — uncomment the one you want to use
# GeneralUser_GS.sf2
soundfonts/FluidR3_GM.sf2
# soundfonts/Arachno.sf2
# /usr/share/sounds/sf2/TimGM6mb.sf2
```

Subdirectories work too, so you can keep a `soundfonts/` folder to stay organized. If none of the listed files are found (or `soundfonts.txt` doesn't exist), the app falls back to its built-in search order.

If you want to use a specific soundfont (e.g. [GeneralUser GS](https://schristiancollins.com/generaluser.php) for higher quality), place the `.sf2` file in the project root (or a subdirectory referenced from `soundfonts.txt`). If not using `soundfonts.txt`, check that the filename matches what the code expects in the `find_soundfont()` function in `app.py`, or rename the file accordingly.

### Running

```bash
cd midi-music-generator
source venv/bin/activate
python3 app.py
```

Open your browser to `http://localhost:5001`

### Docker

The original project includes a Docker setup. If you prefer Docker, see the [original repository](https://github.com/addy999/midi-music-generator) for instructions. Note that the Docker image may not include the changes in this fork.

## Usage

1. Enter your API key in the settings
2. Select a preset from the dropdown menus, or type your own description
3. Click "Generate" to create your MIDI file
4. Listen to the result or download the generated MIDI/WAV file

### LLM Provider Options

The settings menu offers the following provider options:

- **Gemini** — Uses litellm's native Gemini routing.
- **Gemini (Direct API)** — Connects directly to Google's REST endpoint. Use this if the standard Gemini option doesn't work with your API key.
- **OpenAI** — For OpenAI API keys (GPT-4, etc.).
- **Anthropic** — For Anthropic API keys (Claude models).
- **Ollama (Local)** — For local models via [Ollama](https://ollama.com/). No API key required. Expects Ollama running at `http://localhost:11434`. Results depend on the model's ability to follow structured output instructions — larger models tend to work better. **Tip:** Enable "Lite" mode (checkbox in the options row) for a shorter prompt that works better with small models. It is automatically enabled when Ollama is selected as the provider.
- **Custom** — Lets you specify any OpenAI-compatible API endpoint and model name.

### Debug Mode

Enable "Debug mode" in Settings to see the raw LLM response after each generation. This is useful when testing different models — if generation fails, the debug panel shows exactly what the model returned, helping you understand whether the issue is malformed JSON, a wrong structure, or something else entirely. Debug output appears in a collapsible panel below the piano roll and is also printed to the terminal.

> **Tip:** Not sure which Gemini model to use? The included `list_gemini_models.py` utility lists all models available with your API key. See [README_List_Gemini_Models.md](README_List_Gemini_Models.md) for details.

## Preset Editor (Optional)

A separate browser-based tool for adding, editing, and organizing presets. Not required for normal use — the app comes with 35 presets and you can always type a custom prompt.

See [README_Preset_editor.md](README_Preset_editor.md) for setup and usage instructions.

## License

MIT
