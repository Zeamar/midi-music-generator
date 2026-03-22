# Changelog (Fork changes from upstream)

All changes are relative to the original [addy999/midi-music-generator](https://github.com/addy999/midi-music-generator).

---

## v1.1

Changes from v1.0 → v1.1:

### New Features

- **Configurable soundfont via `soundfonts.txt`**: The app now checks for a `soundfonts.txt` file in the project directory before falling back to hard-coded filenames and system paths. Each uncommented line is treated as a soundfont path (relative to the project directory, e.g. `soundfonts/GeneralUser_GS.sf2`). Lines starting with `#` are ignored, so you can keep a list of soundfonts and quickly switch between them by commenting/uncommenting. If none of the listed files exist, the app falls back to the previous search order.
- **Lite mode for local models**: Added a "Lite" checkbox in the options row that uses a drastically shorter prompt optimized for small local LLMs (Ollama). The lite prompt replaces the full 128-instrument GM table with a curated ~30 instrument list in compact format, adds a complete concrete JSON example (not just a schema with `...`), and uses direct "return ONLY JSON" instructions. Automatically enabled when Ollama provider is selected. Reduces prompt token count by ~80%.
- **Debug mode**: Added a "Debug mode" toggle in Settings that shows the raw LLM response in a collapsible panel below the piano roll. When generating multiple variations, the debug panel displays them sorted by variation number (1, 2, 3…), and failed variations are always included — showing both the error message and the raw response, making it much easier to diagnose why a particular model fails (malformed JSON, plain text response, syntax errors, wrong structure, etc.). Debug info is also printed to the terminal when enabled. Successful generations also show the raw response when debug is on.

### Bug Fixes

- **Strip JavaScript-style comments from JSON responses**: Some models (notably Gemini 2.5 Flash) insert `//` line comments inside the generated JSON (e.g. `// Bar 1`, `// Intro`), which is not valid JSON and caused parse failures. The JSON parser now includes a comment-stripping pass that removes `//` comments while preserving URLs and other legitimate `//` content inside quoted strings. Both the full and lite prompts also now explicitly instruct the LLM not to include comments.
- **Fixed drum channel assignment**: Tracks are now assigned to separate MIDI channels (skipping channel 9 for melodic instruments). Drum/percussion tracks (channel 9/10 requested by LLM, or instruments 112-119) are correctly routed to MIDI channel 9. Previously, sequential channel assignment starting from 0 meant track 10+ would accidentally land on the drum channel.
- **Robust JSON parsing**: Replaced the fragile two-step JSON parser with a multi-strategy extraction function that tries: direct parse, ` ```json ` fences, generic code fences, brace-matching, and bracket-matching. Failed parses now return specific diagnostic messages (empty response, no JSON found, syntax error with position) instead of generic "Generation Failed".
- **JSON format enforcement for Ollama**: Added `response_format: {"type": "json_object"}` to Ollama API calls, which forces compatible models to output valid JSON instead of mixing prose with data.
- **Malformed note data handling**: Individual notes with invalid pitch/duration/time values are now skipped instead of crashing the entire MIDI generation. Duration is clamped to minimum 0.1 beats and time to minimum 0.0.
- **Ollama allowed without API key on page load**: The "API key not configured" warning is no longer shown when the provider is set to Ollama, which doesn't require an API key.

### Other Changes

- Full prompt JSON schema now includes a concrete 3-track example (piano + bass + drums with `"channel": 9`) instead of a skeleton with `...` placeholders.
- Removed dead commented-out mido channel remapping code from `separate_channels_and_render()`.
- Removed unused `jazz.json` and `mido` import references.

---

## v1.0

Initial fork release. All changes below are relative to the original upstream project.

### New Features

- **Gemini (Direct API) provider option**: Added a dedicated "Gemini (Direct API)" provider choice that connects directly to Google's REST endpoint (`generativelanguage.googleapis.com`). This works as an alternative if litellm's native Gemini routing fails with some API keys.
- **Ollama (Local) provider option**: Added a dedicated "Ollama (Local)" provider choice that auto-configures the base URL (`http://localhost:11434/v1`) and removes the API key requirement. Makes it easy to use local models without manually entering the endpoint each time.
- **Preset menu system**: Replaced 12 hardcoded preset buttons with a hierarchical category/preset dropdown menu. Presets are loaded from an external `presets.json` file, making them easy to customize and extend without code changes.
- **Song length selector**: Added a length dropdown (Short/Medium/Long/Very Long) so users can request different composition lengths from the LLM. The original version had a fixed 8-16 bar instruction.
- **Playback volume control**: Added a real-time volume control (20%-100%) using the Web Audio API GainNode. Useful on systems where full gain causes clipping/distortion in multi-track pieces.
- **`if __name__ == '__main__'` entry point**: Added so that `python app.py` starts the server directly. The original only worked via `flask run` (as used in the Docker setup).

### Bug Fixes

- **Fixed `jazz.json` FileNotFoundError on startup**: The original `app.py` attempted to read `jazz.json` at import time, but this file is not included in the repository. Commented out the unused reference.
- **Fixed race condition in WAV conversion**: Replaced hardcoded `/tmp/test.mid` and `/tmp/test.wav` paths with unique temporary files via Python's `tempfile` module. Parallel variation generation no longer risks file collisions when multiple WAV conversions run simultaneously.
- **Corrected API key privacy notice**: Updated the settings dialog text to accurately describe that the API key is sent to the server for proxying to the LLM provider, rather than claiming it goes "directly to the provider".
- **Fixed generation lockup after all variations fail**: When all requested variations failed (e.g. 1/1 failed), the UI state was not properly reset, causing subsequent generation attempts to appear to hang. The fix explicitly resets UI state when no variations succeed.
- **Fixed WAV status UI race condition with multiple variations**: The `generateWav` function previously updated playback buttons unconditionally, meaning a background WAV conversion for variation #2 could hide buttons already visible for variation #1. UI updates are now scoped to the currently active variation only.
- **Fixed base URL leaking between providers**: When switching away from the Custom provider, the base URL field was hidden but its value was still saved to localStorage. The fix clears the base URL when saving settings for any non-Custom provider.

### Other Changes

- Default model changed from `gemini-2.5-pro` to `gemini-2.5-flash` (works with free-tier API keys).
- FluidSynth default gain lowered from 1.0 to 0.6 to reduce clipping on multi-track pieces.
- Separate WAV rendering for downloads (fixed 0.6 gain) vs. preview playback (user-adjustable via client-side GainNode).
- UI & text: Adjusted header layout and updated interface text to reflect new controls.

### Notes

- The original project is designed for Docker deployment (`flask run`). This fork adds `if __name__ == '__main__'` for convenience when running without Docker, but Docker remains fully supported.
