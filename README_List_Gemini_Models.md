# List Gemini Models

A small utility for **Midi Music Generator v2 – Zeamar's Fork** that lists all Gemini models available with your API key.

This helps you find the correct model name to enter in the application's **Settings → Model Name** field.

## Requirements

- Python 3.8 or higher
- `requests` library

If you installed the main app's dependencies in a virtual environment, activate it first (`source venv/bin/activate`) — `requests` is likely already available through litellm's dependencies.

If `requests` is not installed:
```bash
pip3 install requests
```

## Usage

```bash
# Pass your API key as an argument
python3 list_gemini_models.py YOUR_API_KEY

# Or run without arguments to be prompted interactively
python3 list_gemini_models.py
```

## Example output

```
======================================================================
AVAILABLE GEMINI MODELS
======================================================================

Found 12 model(s) compatible with Midi Music Generator:

  gemini-2.0-flash
    Display name : Gemini 2.0 Flash
    Description  : Fast and versatile multimodal model for scaling...

  gemini-2.5-flash
    Display name : Gemini 2.5 Flash
    Description  : Adaptive thinking, cost efficiency...

======================================================================

TIP: Copy the model name (e.g. 'gemini-2.5-flash') into the
     Model Name field in the Settings window (without the 'models/' prefix).

NOTE: This list shows all models that technically support content
      generation. It does NOT reflect your API key's actual quota.
      Free-tier keys may not have access to all listed models
      (e.g. pro models). If a model fails in the app, check your
      quota tier at https://aistudio.google.com/apikey
======================================================================
```

## Getting a Gemini API key

You need a Gemini API key. You can obtain one from [Google AI Studio](https://aistudio.google.com/apikey).
Note: Google AI Studio is intended for developer use. Review Google's [Gemini API Terms of Service](https://ai.google.dev/gemini-api/terms) before signing up.

## Important: model list vs. actual access

This tool lists all Gemini models that technically support the `generateContent` method. However, the Google AI API **does not filter the list based on your API key's quota tier**. This means both free-tier and paid keys will return the same set of models.

In practice, free-tier keys may not have access to all listed models (e.g. `gemini-2.5-pro` may only work with a paid key). If a model appears in the list but fails when used in Midi Music Generator, your quota tier is likely the reason. You can check and upgrade your tier at [Google AI Studio → API Keys](https://aistudio.google.com/apikey).

## Notes

- The tool only shows models that support the `generateContent` method, which is what Midi Music Generator uses.
- Your available models may vary depending on your API plan (free tier vs. paid).
- The API key is sent directly to Google's API and is not stored anywhere.

## License

MIT
