# CLAUDE.md - google-genmedia-mcp

## Project Overview

Google GenMedia MCP Server - A Python-based MCP server for Google's generative media APIs (Imagen, Gemini Image, Veo, Chirp, Lyria).

Inspired by the official [mcp-genmedia](https://github.com/GoogleCloudPlatform/vertex-ai-creative-studio/tree/main/experiments/mcp-genmedia) Go implementation, but rebuilt in Python with FastMCP for better configurability and easier installation via uvx.

## Architecture

- **Framework**: FastMCP (mcp[cli])
- **Build**: hatchling with `src/` layout
- **Package**: `google_genmedia_mcp` in `src/`
- **Entry point**: `google-genmedia-mcp` CLI command

### Directory Structure

```
src/google_genmedia_mcp/
├── core/          # Client, models, errors
├── auth/          # AuthManager, OAuth flow
├── services/      # Business logic (imagen, veo, chirp, lyria, etc.)
├── mcp/           # FastMCP server and tools
└── utils/         # Config loader
```

## Authentication Methods

1. **api_key**: Google AI Studio API Key (Phase 1 only)
2. **vertex_ai**: Application Default Credentials via `gcloud auth application-default login`
3. **oauth**: Browser-based OAuth flow via `google-genmedia-mcp auth login`

Note: Chirp (TTS) and Lyria (music) require vertex_ai or oauth authentication.

## Configuration

Config file location: `~/.google-genmedia-mcp/config.yaml`

Override via environment variable: `GENMEDIA_CONFIG_PATH`

API key override: `GENMEDIA_API_KEY` environment variable

### Config Structure

The `prompt` section configures automatic prompt prefix (prepended to all generation prompts, not speech text):

```yaml
prompt:
  prefix: ""        # Text prepended to all prompts (e.g., "日本語で出力。")
  separator: "\n"   # Separator between prefix and prompt
```

The `tools` section in config.yaml manages per-tool defaults and model lists:

```yaml
tools:
  generateImage:    # defaultModel, aspectRatio, numberOfImages, outputMimeType, allowUnregistered, models
  editImage:        # defaultModel (Imagen only), editMode, numberOfImages, models
  generateVideo:    # defaultModel, aspectRatio, durationSeconds, numberOfVideos, models, polling
  generateVideoFromImage:  # defaultModel, aspectRatio, durationSeconds, models, polling
  generateSpeech:   # audioEncoding, defaultVoice, defaultLanguage, voices
  generateMusic:    # defaultModel, models
```

Each tool with models has `defaultModel` (alias or ID) + `models` list (id + aliases). Model resolution: alias/ID lookup → `_resolve_model()` in `core/models.py`.

## Development Commands

```bash
# Install dependencies
uv sync

# Install with Phase 2 dependencies (Chirp/Lyria)
uv sync --extra phase2

# Run tests
uv run pytest --cov

# Lint
uv run ruff check src/ tests/

# Type check
uv run mypy src/

# Start server
uv run google-genmedia-mcp

# OAuth login
uv run google-genmedia-mcp auth login
```

## MCP Tools

All tools are defined in `src/google_genmedia_mcp/mcp/tools/`.

### Image & Video (all auth methods)

- `generate_image`: Text-to-image with Imagen or Gemini (auto-routed by model prefix)
- `edit_image`: Image editing with Imagen (inpainting, outpainting, background replacement)
- `generate_video`: Text-to-video with Veo models
- `generate_video_from_image`: Image-to-video with Veo models (GCS URI required)
- `server_info`: Server status, available tools/models, config diagnostics

### Audio & Utility (vertex_ai/oauth only for audio)

- `generate_speech`: Text-to-speech with Chirp 3 HD (requires vertex_ai/oauth)
- `generate_music`: Music generation with Lyria (requires vertex_ai/oauth)
- `combine_audio_video`: Combine video and audio with ffmpeg (all auth methods)
