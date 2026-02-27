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

### Phase 1
- `imagen_t2i`: Text-to-image with Imagen models
- `gemini_image_generation`: Image generation/editing with Gemini
- `veo_t2v`: Text-to-video with Veo models
- `veo_i2v`: Image-to-video with Veo models
- `server_info`: Server status and available tools/models

### Phase 2
- `imagen_edit`: Image editing (inpainting, outpainting, etc.)
- `chirp_tts`: Text-to-speech with Chirp 3 HD (requires vertex_ai/oauth)
- `lyria_generate_music`: Music generation with Lyria (requires vertex_ai/oauth)
- `av_combine`: Combine video and audio with ffmpeg
