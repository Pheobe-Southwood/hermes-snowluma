# hermes-snowluma

Bridge QQ messages into [Hermes Agent](https://hermes-agent.nousresearch.com) via [SnowLuma](https://github.com/SnowLuma/SnowLuma.Docker.Framework) (OneBot v11 + MCP).

## What this project does

This repository is a **Hermes skill** that connects QQ messaging with Hermes Agent through two channels:

1. **MCP** — Hermes calls OneBot actions (send/recv messages, manage groups, handle files) via `@snowluma/mcp` stdio server
2. **Webhook** — QQ events flow into Hermes as agent prompts via HTTP webhook, with **route script** preprocessing for slash command support

## Features

- **8 MCP tools** → 179 OneBot actions (`send_private_msg`, `send_group_msg`, image upload, voice messages, group management, etc.)
- **Auto-text-delivery plugin** — Plain text LLM responses are automatically forwarded to QQ via `qq-auto-delivery` plugin (no MCP needed for text)
- **Route script** — Preprocesses OneBot payloads, enables `/new` / `/reset` session management in QQ
- **Session grouping** — Private chats grouped by QQ number, group chats grouped by group number
- **Image transfer** — `upload_file_stream` workflow for sending large images (>1MB) to QQ
- **Voice/TTS integration** — ElevenLabs TTS + `base64://` protocol for audio messages
- **Platform toolsets** — Configurable toolkits for webhook platforms (terminal, file, skills, web, vision, tts)

## Quick Start

```bash
# 1. Install the MCP server
npm install -g @snowluma/mcp

# 2. Add the skill
mkdir -p ~/.hermes/skills/messaging/snowluma-hermes-bridge
cp SKILL.md ~/.hermes/skills/messaging/snowluma-hermes-bridge/

# 3. Set up the auto-text-delivery plugin (for automatic plain text replies)
mkdir -p ~/.hermes/profiles/<name>/plugins/qq-auto-delivery
cp -r plugins/qq-auto-delivery/* ~/.hermes/profiles/<name>/plugins/qq-auto-delivery/

# 4. Add to your Hermes profile config.yaml
# (See SKILL.md for full configuration reference)

# 5. Start Hermes gateway
hermes -p <profile> gateway start
```

See [SKILL.md](SKILL.md) for complete setup instructions including MCP configuration, webhook routing, route scripts, voice integration, and troubleshooting.

## Requirements

- Hermes Agent v0.18+
- SnowLuma Docker container (`motricseven7/snowluma:latest`) with OneBot HTTP enabled
- Node.js 22+ with `@snowluma/mcp` installed globally

## Repository Structure

```
hermes-snowluma/
├── SKILL.md                          # Main skill documentation
├── README.md                         # This file
├── scripts/
│   ├── qq-command-handler.py         # OneBot payload preprocessing (route script)
│   └── send-voice.py                 # Pure sender for TTS audio files
├── plugins/
│   └── qq-auto-delivery/             # Auto-deliver plain text to QQ
│       ├── plugin.yaml
│       └── __init__.py
└── references/
    ├── user-profile.md               # User profile template
    ├── container-architecture.md     # SnowLuma Docker container details
    └── voice-capability-research.md  # TTS/STT integration research
```

## License

MIT
