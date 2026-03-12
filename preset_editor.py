#!/usr/bin/env python3
"""
MIDI Music Generator - Preset Editor
Standalone editor for presets.json
"""
from flask import Flask, render_template, request, jsonify
import json
import os
import shutil
from datetime import datetime

app = Flask(__name__)

# Presets file path - must match the main app's location
PRESETS_FILE = 'presets.json'

# Common emojis available for category icons
EMOJI_LIST = [
    '🎼', '🎵', '🎶', '🎹', '🎸', '🎷', '🎺', '🎻', '🥁', '🎤',
    '🎧', '🎮', '⚔️', '🏰', '🌟', '✨', '🔥', '💎', '🌈', '🌍',
    '🌊', '🌙', '☀️', '⭐', '💫', '🎪', '🎭', '🎨', '🎬', '📻',
    '🔊', '🎛️', '😊', '😢', '😡', '😴', '🤔', '💃', '🕺', '🎉'
]

def load_presets():
    """Load presets from the JSON file. Returns empty structure if file doesn't exist."""
    if not os.path.exists(PRESETS_FILE):
        return {'categories': []}
    try:
        with open(PRESETS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading presets: {e}")
        return {'categories': []}

def save_presets(data):
    """Save presets to file. Creates a timestamped backup of the previous version."""
    try:
        # Create a backup before overwriting
        if os.path.exists(PRESETS_FILE):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = f'presets_backup_{timestamp}.json'
            shutil.copy2(PRESETS_FILE, backup_file)
            print(f"Backup created: {backup_file}")
        # Write the new data
        with open(PRESETS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True, "Saved successfully!"
    except Exception as e:
        return False, f"Save error: {str(e)}"

@app.route('/')
def index():
    """Serve the editor page."""
    return render_template('preset_editor.html')

@app.route('/api/presets', methods=['GET'])
def get_presets():
    """Return all presets as JSON."""
    data = load_presets()
    return jsonify(data)

@app.route('/api/emojis', methods=['GET'])
def get_emojis():
    """Return the list of available emojis."""
    return jsonify(EMOJI_LIST)

@app.route('/api/presets', methods=['POST'])
def save_presets_api():
    """Validate and save presets received from the editor."""
    try:
        data = request.json
        # Validate top-level structure
        if 'categories' not in data:
            return jsonify({'error': 'Invalid data structure: missing categories'}), 400
        # Validate each category and its presets
        for cat in data['categories']:
            if 'name' not in cat or 'icon' not in cat or 'presets' not in cat:
                return jsonify({'error': 'Invalid category structure'}), 400
            for preset in cat['presets']:
                if 'name' not in preset or 'prompt' not in preset:
                    return jsonify({'error': 'Invalid preset structure'}), 400
        success, message = save_presets(data)
        if success:
            return jsonify({'message': message})
        else:
            return jsonify({'error': message}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("\n" + "="*60)
    print("MIDI PRESET EDITOR")
    print("="*60)
    print(f"\nPresets file: {os.path.abspath(PRESETS_FILE)}")
    print("\nOpen in browser: http://localhost:5002")
    print("\nPress Ctrl+C to quit")
    print("="*60 + "\n")
    app.run(host='0.0.0.0', port=5002, debug=False)
