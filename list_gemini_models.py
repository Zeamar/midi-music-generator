#!/usr/bin/env python3
"""
List all available Gemini models via the Google AI API.

A utility tool for Midi Music Generator v2 – Zeamar's Fork.
Helps users find the correct model name to enter in the Settings window.

Note: The API returns all models that technically support content generation,
regardless of whether your API key's quota tier grants access to them.

Usage:
    python3 list_gemini_models.py YOUR_API_KEY
    python3 list_gemini_models.py
        (prompts for API key interactively)
"""
import requests
import sys


def list_gemini_models(api_key):
    """List all Gemini models that support content generation."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        print("\n" + "=" * 70)
        print("AVAILABLE GEMINI MODELS")
        print("=" * 70 + "\n")

        models = data.get("models", [])

        # Filter models that support the generateContent method
        generate_models = [
            m for m in models
            if "generateContent" in m.get("supportedGenerationMethods", [])
        ]

        if not generate_models:
            print("No models found that support the generateContent method.")
            return

        print(f"Found {len(generate_models)} model(s) compatible with Midi Music Generator:\n")

        for model in sorted(generate_models, key=lambda x: x.get("name", "")):
            name = model.get("name", "").replace("models/", "")
            display_name = model.get("displayName", "N/A")
            description = model.get("description", "No description available")

            # Truncate long descriptions
            if len(description) > 100:
                description = description[:97] + "..."

            print(f"  {name}")
            print(f"    Display name : {display_name}")
            print(f"    Description  : {description}")

            # Show rate-limit info if available
            if "rateLimits" in model:
                print(f"    Rate limits  : {model['rateLimits']}")

            print()

        print("=" * 70)
        print("\nTIP: Copy the model name (e.g. 'gemini-2.5-flash') into the")
        print("     Model Name field in the Settings window (without the 'models/' prefix).")
        print()
        print("NOTE: This list shows all models that technically support content")
        print("      generation. It does NOT reflect your API key's actual quota.")
        print("      Free-tier keys may not have access to all listed models")
        print("      (e.g. pro models). If a model fails in the app, check your")
        print("      quota tier at https://aistudio.google.com/apikey")
        print("=" * 70 + "\n")

    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 400:
            print(f"\nError: Invalid API key or bad request ({e})")
        else:
            print(f"\nError: API request failed: {e}")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"\nError: Could not reach the API: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python3 list_gemini_models.py YOUR_API_KEY\n")

        api_key = input("Enter your Gemini API key: ").strip()
        if not api_key:
            print("Error: An API key is required.")
            sys.exit(1)
    else:
        api_key = sys.argv[1]

    list_gemini_models(api_key)
