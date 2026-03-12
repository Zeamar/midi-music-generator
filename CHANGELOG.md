# Changelog (Fork changes from upstream)

## New Features

- **Gemini (Direct API) provider option**: Added a dedicated "Gemini (Direct API)" provider choice that connects directly to Google's REST endpoint (`generativelanguage.googleapis.com`). This works as an alternative if litellm's native Gemini routing fails with some API keys.
- **Ollama (Local) provider option**: Added a dedicated "Ollama (Local)" provider choice that auto-configures the base URL (`http://localhost:11434/v1`) and removes the API key requirement. Makes it easy to use local models without manually entering the endpoint each time.
- **Preset menu system**: Replaced 12 hardcoded preset buttons with a hierarchical category/preset dropdown menu. Presets are loaded from an external `presets.json` file, making them easy to customize and extend without code changes.
- **Song length selector**: Added a length dropdown (Short/Medium/Long/Very Long) so users can request different composition lengths from the LLM. The original version had a fixed 8-16 bar instruction.
- **Playback volume control**: Added a real-time volume control (20%-100%) using the Web Audio API GainNode. Useful on systems where full gain causes clipping/distortion in multi-track pieces.
- **`if __name__ == '__main__'` entry point**: Added so that `python app.py` starts the server directly. The original only worked via `flask run` (as used in the Docker setup).

## Bug Fixes

- **Fixed `jazz.json` FileNotFoundError on startup**: The original `app.py` attempted to read `jazz.json` at import time, but this file is not included in the repository. Commented out the unused reference. (The example data was already commented out in the prompt construction, so this line had no functional purpose.)
- **Fixed race condition in WAV conversion**: Replaced hardcoded `/tmp/test.mid` and `/tmp/test.wav` paths with unique temporary files via Python's `tempfile` module. Parallel variation generation no longer risks file collisions when multiple WAV conversions run simultaneously.
- **Corrected API key privacy notice**: Updated the settings dialog text to accurately describe that the API key is sent to the server for proxying to the LLM provider, rather than claiming it goes "directly to the provider".
- **Fixed generation lockup after all variations fail**: When all requested variations failed (e.g. 1/1 failed), the UI state was not properly reset, causing subsequent generation attempts to appear to hang (the API call was made but results were never displayed). The fix explicitly resets UI state when no variations succeed, so the next generation works without requiring a page refresh.
- **Fixed WAV status UI race condition with multiple variations**: The `generateWav` function previously updated playback buttons unconditionally, meaning a background WAV conversion for variation #2 could hide the Play/Download buttons that were already visible for variation #1. UI updates are now scoped to the currently active variation only.
- **Fixed base URL leaking between providers**: When switching away from the Custom provider, the base URL field was hidden but its value was still saved to localStorage. This caused subsequent requests with other providers (e.g. Gemini) to be routed to the wrong endpoint, typically resulting in "405 method not allowed" or "model not found" errors. The fix clears the base URL when saving settings for any non-Custom provider.

## Other Changes

- Default model changed from `gemini-2.5-pro` to `gemini-2.5-flash` (works with free-tier API keys).
- FluidSynth default gain lowered from 1.0 to 0.6 to reduce clipping on multi-track pieces.
- Separate WAV rendering for downloads (fixed 0.6 gain) vs. preview playback (user-adjustable via client-side GainNode).
- UI & text: Adjusted header layout and updated interface text to reflect new controls.

## Notes

- The original project is designed for Docker deployment (`flask run`). This fork adds `if __name__ == '__main__'` for convenience when running without Docker, but Docker remains fully supported.
