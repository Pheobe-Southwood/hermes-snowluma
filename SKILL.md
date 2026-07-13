---
name: snowluma-hermes-bridge
description: "Bridge QQ messages into Hermes Agent via SnowLuma (OneBot v11 + MCP). Use when setting up QQ bot integration, configuring QQ webhook handlers, or troubleshooting the SnowLuma-to-Hermes pipeline."
version: 2.0.0
author: community
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [QQ, SnowLuma, OneBot, MCP, Webhook, Messaging, Integration, Voice, TTS]
    related_skills: [send-voice-to-qq]
compatibility: "Requires Hermes Agent v0.18+, SnowLuma Docker container (motricseven7/snowluma), Node.js 22+, @snowluma/mcp installed globally."
prerequisites:
  commands: [snowluma-mcp]
  packages: ["@snowluma/mcp"]
---

# SnowLuma — Hermes Bridge

Bridge QQ messaging into Hermes Agent through two channels:
1. **MCP** — Hermes calls OneBot actions (send messages, manage groups, query contacts) via `@snowluma/mcp` stdio server
2. **Webhook** — QQ messages flow into Hermes as agent prompts via HTTP webhook

```
QQ Client → Tencent Server → SnowLuma(OneBot v11, host network) → POST /webhooks/qq-message
  → Hermes Webhook(:8644) → Route Script(预处理) → Agent → mcp__snowluma__invoke_action → QQ
```

## When to Use

- Setting up QQ bot integration for Hermes Agent on a new machine
- User asks to "connect QQ to Hermes" or "let Hermes handle QQ messages"
- Debugging missing QQ events or MCP tool failures in the pipeline
- Adding QQ message handling to an existing Hermes deployment

## Architecture

| Component | Role | Config Location |
|-----------|------|-----------------|
| SnowLuma (OneBot) | QQ client + OneBot v11 server | `/opt/snowluma/docker-compose.yml` |
| OneBot HTTP | MCP backend API | `127.0.0.1:3000` |
| OneBot httpClient | Event webhook sender | `onebot_<UIN>.json` → `httpClients[]` |
| Hermes `mcp_servers.snowluma` | MCP tool bridge | `~/.hermes/profiles/<name>/config.yaml` |
| Hermes `platforms.webhook` | Webhook receiver + Route Script | `~/.hermes/profiles/<name>/config.yaml` |
| Hermes `plugins` | Auto-deliver plain text to QQ | `~/.hermes/profiles/<name>/plugins/qq-auto-delivery/` |
| Route Script | OneBot payload preprocessing | `~/.hermes/profiles/<name>/scripts/qq-command-handler.py` |

Both components assume Hermes and SnowLuma/OneBot run on the **same host** (same `127.0.0.1`). Container networking details are out of scope; if they are containerized, ensure the webhook port is reachable from the OneBot process.

---

## Part 1: MCP — Hermes → SnowLuma

Hermes uses `@snowluma/mcp` (stdio MCP server) to expose OneBot actions as Hermes tools.

### SnowLuma MCP Tools (8 tools → 179 OneBot actions)

| MCP Tool | Purpose |
|----------|---------|
| `mcp__snowluma__list_actions` | List all 179 OneBot action names |
| `mcp__snowluma__get_action` | Get single action docs + Schema |
| `mcp__snowluma__search_actions` | Search actions by keyword |
| `mcp__snowluma__list_categories` | List 11 categories |
| `mcp__snowluma__query_action` | Read-only action (query info) |
| `mcp__snowluma__invoke_action` | Execute any action (send messages, manage groups, etc.) |
| `mcp__snowluma__list_resources` | Hermes built-in wrapper |
| `mcp__snowluma__read_resource` | Hermes built-in wrapper |

### MCP Modes

| Mode | Available Tools | What LLM Can Do |
|------|-----------------|-----------------|
| `docs` | First 4 (no OneBot needed) | Only query docs |
| `read` | First 4 + `query_action` | Read-only operations |
| `write` | All 6 core tools | Send messages, manage groups, kick/ban members |

Switch mode: edit `config.yaml` → `SNOWLUMA_MCP_MODE` → send `/reload-mcp` in active session.

### Prerequisites

```bash
node -v                  # Must be >= 22
npm list -g @snowluma/mcp  # Should show @snowluma/mcp@1.x
which snowluma-mcp       # Should return a path
```

If not installed:

```bash
npm install -g @snowluma/mcp
```

### Gather OneBot credentials

From SnowLuma's OneBot HTTP adapter config (WebUI → Network → HTTP adapter, or container file `/app/snowluma-data/config/onebot_<UIN>.json`):

- **Endpoint**: `http://127.0.0.1:3000/`
- **Token**: The `accessToken` from the `httpServers[]` entry
- **Authoritative source**: The Docker volume config file at `/var/lib/docker/volumes/snowluma_snowluma-data/_data/config/onebot_<UIN>.json`

### Configure Hermes

Add to `<profile>/config.yaml`:

```yaml
mcp_servers:
  snowluma:
    command: "snowluma-mcp"
    env:
      SNOWLUMA_MCP_ENDPOINT: "http://127.0.0.1:3000/"
      SNOWLUMA_MCP_TOKEN: "<onebot-access-token>"
      SNOWLUMA_MCP_MODE: "write"
```

### Reload

Send `/reload-mcp` in an active session (no gateway restart needed).

### Verify

```bash
curl -s -H "Authorization: Bearer ***" http://127.0.0.1:3000/get_login_info
# {"status":"ok","retcode":0,"data":{"user_id":"<your-qq>","nickname":"<nickname>"}}
```

---

## Part 2: Webhook — SnowLuma → Hermes

QQ events (messages, notices, requests) are **pushed** from SnowLuma to Hermes via OneBot's `httpClients` mechanism. A **route script** preprocesses the payload before it reaches the agent.

### Full Webhook Route Config

```yaml
platforms:
  webhook:
    enabled: true
    extra:
      host: "127.0.0.1"
      port: 8644
      routes:
        qq-message:
          events: []                           # Accept all event types
          secret: "INSECURE_NO_AUTH"           # Local loopback only
          group_by:                            # Session grouping
            private: user_id                   # DMs grouped by QQ number
            group: group_id                    # Group chats grouped by group number
          script: qq-command-handler.py        # Preprocessing script
          filters:
            - field: "post_type"
              equals: "message"                # Only process message events
          prompt: "{message_context}"          # Dynamically built by route script
          deliver: log                         # Replies go through MCP, not webhook
```

### Critical config settings

```yaml
approvals:
  mode: off                                     # Disable approval prompts
  destructive_slash_confirm: false              # Required for /new /reset to work

session_reset:
  reset_by_platform:
    webhook:
      mode: "none"                              # Sessions never auto-expire
```

### Route Script: qq-command-handler.py

The route script (`scripts/qq-command-handler.py`) preprocesses OneBot payloads. Key behaviors:

1. **Slash commands** (`/new` / `/reset`): Sets `message_context` to the raw command text (triggers Hermes gateway session reset) + sends confirmation reply directly via OneBot API
2. **Normal messages**: Builds a descriptive context string with event type, QQ number, group number, message content
3. Outputs modified JSON to stdout

**Why route script is needed**: OneBot uses `post_type` instead of standard event headers. Raw `post_type` values can't be matched by `events: []` semantics. The route script normalizes the payload and enables slash command detection.

**Script location**: Place in `<profile>/scripts/qq-command-handler.py`. The script path is relative to the profile's `scripts/` directory.

```python
# scripts/qq-command-handler.py (simplified)
import json, sys, urllib.request

ONE_BOT_API = "http://127.0.0.1:3000/"
ONE_BOT_TOKEN = "..."  # From config

def main():
    payload = json.loads(sys.stdin.read())
    raw_message = payload.get("raw_message", "").strip()
    if raw_message in ("/new", "/reset"):
        payload["message_context"] = raw_message
        send_qq_msg(payload["user_id"], "确认消息", group_id=payload.get("group_id"))
    else:
        payload["message_context"] = build_context(payload)
    json.dump(payload, sys.stdout)

if __name__ == "__main__":
    main()
```

### Configure SnowLuma httpClient

In the OneBot JSON config (`onebot_<UIN>.json`), add to the `httpClients` array:

```json
{
  "name": "hermes-webhook",
  "url": "http://127.0.0.1:8644/webhooks/qq-message",
  "messageFormat": "array",
  "reportSelfMessage": false,
  "timeout": 5000
}
```

The config file lives at `/var/lib/docker/volumes/snowluma_snowluma-data/_data/config/onebot_<UIN>.json` (Docker volume path).

### Session Grouping

```yaml
group_by:
  private: user_id    # Private chats: grouped by QQ number
  group: group_id     # Group chats: grouped by group number
```

- Private chats: same QQ number inherits context
- Group chats: all members of same group share one session
- Sessions never auto-expire (`session_reset.mode: none`), but are released from memory after 1 hour of inactivity (persisted in SQLite)
- **Active reset**: Send `/new` or `/reset` in QQ

### Verification

```bash
# Check gateway health
curl http://127.0.0.1:8644/health
```

### QQ Auto-Delivery Plugin

With the `qq-auto-delivery` plugin, **plain text responses from the LLM are automatically delivered to QQ** via the `transform_llm_output` hook. The LLM does NOT need to call `mcp__snowluma__invoke_action` to send text — it simply generates text naturally, and the plugin forwards it.

MCP tools remain necessary for non-text operations (images, voice files, group management, etc.).

**Plugin files** (place in `<profile>/plugins/qq-auto-delivery/`):

`plugin.yaml`:
```yaml
name: qq-auto-delivery
version: "1.0"
description: "Auto-deliver LLM text responses to QQ when MCP tools are not called"
```

`__init__.py`:
```python
import json, logging, urllib.request

logger = logging.getLogger(__name__)

ONE_BOT_API = "http://127.0.0.1:3000/"
ONE_BOT_TOKEN = "<your-token>"   # Same as SNOWLUMA_MCP_TOKEN
TARGET_USER = 2085849951         # QQ number to deliver to

def _send_text(text: str) -> None:
    text = text.strip()
    if not text:
        return
    payload = {
        "action": "send_private_msg",
        "params": {"user_id": TARGET_USER, "message": text},
    }
    try:
        req = urllib.request.Request(
            ONE_BOT_API, data=json.dumps(payload).encode(),
            headers={"Authorization": f"Bearer {ONE_BOT_TOKEN}", "Content-Type": "application/json"},
            method="POST")
        with urllib.request.urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read().decode())
            if result.get("status") == "ok" and result.get("retcode") == 0:
                logger.info("delivered to QQ: %r", text[:200])
    except Exception as e:
        logger.error("HTTP error: %s", e)

def deliver(response_text: str, **kwargs) -> str | None:
    if response_text and response_text.strip():
        _send_text(response_text)
    return None  # Pass-through: response unchanged

def register(ctx):
    ctx.register_hook("transform_llm_output", deliver)
```

Enable in `<profile>/config.yaml`:
```yaml
plugins:
  enabled:
    - qq-auto-delivery
```
# Simulate webhook POST
curl -s -X POST http://127.0.0.1:8644/webhooks/qq-message \
  -H "Content-Type: application/json" \
  -d '{"post_type":"message","message_type":"private","user_id":123,"raw_message":"test"}'
# {"status":"accepted",...}

# Check logs
tail -f ~/.hermes/profiles/<name>/logs/agent.log | grep webhook
```

---

## Part 3: Image Handling

### Receiving Images (From QQ to Hermes)

Extract the `url` field from QQ image segments in the webhook payload. `vision_analyze` works with QQ CDN URLs.

### Sending Images (From Hermes to QQ)

The QQ bot (snowluma) runs in a Docker container and cannot access host filesystem paths. Direct `file://` paths fail with EACCES/ENOENT. Base64 inline also fails for files >1MB.

#### Workflow: upload_file_stream (for files >1MB)

Use the HTTP API directly (port 3000) instead of MCP tools. Token from `config.yaml` `SNOWLUMA_MCP_TOKEN`.

```python
import base64, json, urllib.request

TOKEN = "<from config.yaml>"
API = "http://127.0.0.1:3000/"
FILE = "/path/to/image.png"

with open(FILE, 'rb') as f:
    data = f.read()

chunk_size = 450000  # 450KB binary chunks
chunks = [data[i:i+chunk_size] for i in range(0, len(data), chunk_size)]
stream_id = "img_<timestamp>"

def call(action, params):
    p = {"action": action, "params": params}
    req = urllib.request.Request(API,
        data=json.dumps(p).encode(),
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
        method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())

# 1. Init stream
call("upload_file_stream", {"stream_id": stream_id,
    "total_chunks": len(chunks), "file_size": len(data),
    "filename": "image.png"})

# 2. Upload chunks (is_complete must be False on all chunks)
for i, chunk in enumerate(chunks):
    b64 = base64.b64encode(chunk).decode()
    call("upload_file_stream", {"stream_id": stream_id,
        "chunk_index": i, "chunk_data": b64,
        "is_complete": False})

# 3. Complete stream and get bot-local path
result = call("upload_file_stream", {"stream_id": stream_id,
    "is_complete": True, "chunk_index": len(chunks)-1})
file_path = result["data"]["file_path"]  # /tmp/snowluma-stream/upload/...

# 4. Send via CQ image code
call("send_private_msg", {"user_id": <QQ>, "message": f"[CQ:image,file=file://{file_path}]"})
```

**Key constraints:**
- `stream_id` must be alphanumeric and unique per upload (e.g. `img_<timestamp>`). Reusing an open stream_id causes silent data rejection
- Each chunk's `chunk_data` is a base64-encoded binary chunk, NOT a portion of an already-base64-encoded file
- Always call complete step (`is_complete=True`) to trigger file merge
- The returned `file_path` is inside the snowluma container and accessible via `file://` protocol

---

## Part 4: Voice / TTS Integration

### Configuration

```yaml
tts:
  provider: elevenlabs
  elevenlabs:
    voice_id: "<your-voice-id>"
    model_id: "eleven_v3"                # or eleven_multilingual_v2, eleven_flash_v2

platform_toolsets:
  webhook:
    - terminal
    - file
    - skills
    - web
    - vision
    - tts              # Must be added explicitly for QQ/Webhook platform
```

`.env` additions:
```
ELEVENLABS_API_KEY=sk_***
```

### Sending Voice (TTS → QQ)

**Two-step workflow:**

1. Generate audio via Hermes TTS tool:
   ```
   text_to_speech(text="Your text here")
   ```
   Output: `~/.hermes/profiles/<name>/cache/audio/tts_*.mp3`

2. Send via `base64://` protocol through HTTP API:
   ```python
   import base64, json, urllib.request
   
   with open('/tmp/audio.mp3', 'rb') as f:
       b64 = base64.b64encode(f.read()).decode('ascii')
   
   payload = {
       "user_id": <QQ>,
       "message": [{"type": "record", "data": {"file": "base64://" + b64}}]
   }
   
   req = urllib.request.Request(
       "http://127.0.0.1:3000/send_private_msg",
       data=json.dumps(payload).encode(),
       headers={"Authorization": "Bearer <token>", "Content-Type": "application/json"},
       method="POST")
   urllib.request.urlopen(req, timeout=10)
   ```

**Limitations:**
- `base64://` works for small audio files (<100KB / short TTS clips)
- For larger files, use the `upload_file_stream` workflow + `file://` path
- The MCP `invoke_action` fails for base64:// data > parameter size limit; use HTTP API directly for base64://

### ElevenLabs Model Text Length Limits

| model_id | Max Characters |
|----------|---------------|
| `eleven_flash_v2_5` | 40000 |
| `eleven_flash_v2` | 30000 |
| `eleven_multilingual_v2` (default) | 10000 |
| `eleven_v3` | 5000 |
| Other/unknown | 10000 |

### TTS Provider Options

| Provider | Quality | Cost | API Key Required |
|----------|---------|------|-----------------|
| Edge TTS (built-in) | Good | Free | No |
| ElevenLabs | Excellent | Paid | `ELEVENLABS_API_KEY` |
| OpenAI TTS | Good | Paid | `VOICE_TOOLS_OPENAI_KEY` |

Edge TTS is the default Hermes provider (free, no API key). Switch by changing `tts.provider: edge` and setting `tts.edge.voice`.

### Custom TTS Providers (Non-Built-In)

Hermes provides **3 layers** of TTS extensibility:

1. **Built-in providers** — 10 native implementations (edge, openai, elevenlabs, etc.)
2. **Command-type providers** (`tts.providers.<name>: type: command`) — shell command wrapper
3. **Plugin TTSProvider** (Python ABC) — implement `TTSProvider` abstract class

#### Command-Type Provider Example (Fish Audio)

```yaml
tts:
  provider: fish-audio
  providers:
    fish-audio:
      type: command
      command: "fish-tts.sh {text_path} {output_path}"
      output_format: mp3
```

---

## Part 5: Platform Toolsets

```yaml
platform_toolsets:
  webhook:
    - terminal
    - file
    - skills
    - web
    - vision
    - tts              # Required for voice features
```

**Note:** The `tts` toolset is NOT included in the webhook platform by default. Must be added explicitly.
**After modifying `platform_toolsets`**, the user must send `/reset` in QQ (new session) for the new tools to be available. Restarting gateway alone is not sufficient.

---

## Part 6: Auth Token Management

The HTTP API Bearer token (port 3000) lives at the Docker volume path:
```
/var/lib/docker/volumes/snowluma_snowluma-data/_data/config/onebot_<UIN>.json
```
under `networks.httpServers[0].accessToken`.

The `config.yaml` file also contains `SNOWLUMA_MCP_TOKEN` but the Docker volume config is the authoritative source — use it when the MCP token is stale. The token is a long random string.

---

## Usage Guidelines (for Agent's SOUL.md)

When writing SOUL.md for the QQ bot persona, include these critical instructions:

1. **Plain text replies are automatic** — With the `qq-auto-delivery` plugin enabled, the LLM's natural text output is forwarded to QQ via the `transform_llm_output` hook. Do NOT instruct the agent to call `mcp__snowluma__invoke_action` for text replies.
2. **MCP tools for non-text only** — Use `mcp__snowluma__invoke_action` only for images, voice files, group management, and other non-text OneBot actions. Plain text should use natural LLM output.
3. **Keep messages short** — one idea per message. Since the plugin forwards all text directly, be mindful of message length (QQ has character limits).
4. **No Markdown, no emoji** in QQ messages — plain text only.
5. **When sending files** (images, audio), always send a text notification first (which the plugin auto-delivers) before the file transfer via MCP/HTTP API.
6. **Non-MCP tools** (terminal, file tools, vision_analyze) can and should be used freely alongside snowluma MCP tools.
7. **Webhook `deliver: log`** is correct — text delivery is handled by the plugin, not the webhook response mechanism.

### Companion MCP Tools

- **tavily** — Web search, extract, crawl, and deep research. All tavily tools work normally alongside snowluma.

---

## SnowLuma Container Management

```bash
# Container info
docker ps --format "{{.Names}} {{.Image}} {{.Status}}" | grep snowluma

# Restart
docker compose -f /opt/snowluma/docker-compose.yml restart

# Logs
docker logs -f snowluma

# OneBot config
cat /var/lib/docker/volumes/snowluma_snowluma-data/_data/config/onebot_<UIN>.json

# noVNC login (for QR code scan)
# http://<host>:6081/ password: vncpasswd
```

---

## Testing Commands

```bash
# Verify OneBot connection
curl -H "Authorization: Bearer <TOKEN>" http://127.0.0.1:3000/get_login_info

# Send text message (via HTTP API)
curl -X POST http://127.0.0.1:3000/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"action":"send_private_msg","params":{"user_id":123456,"message":"test"}}'

# Send voice message (via HTTP API)
curl -X POST http://127.0.0.1:3000/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"action":"send_private_msg","params":{"user_id":123456,"message":"[CQ:record,file=http://example.com/audio.mp3]"}}'

# Simulate webhook POST
curl -X POST http://127.0.0.1:8644/webhooks/qq-message \
  -H "Content-Type: application/json" \
  -d '{"post_type":"message","message_type":"private","user_id":123,"raw_message":"test"}'

# Check Gateway
hermes -p <profile> gateway status
hermes -p <profile> doctor

# MCP hot reload (in conversation)
# /reload-mcp
```

---

## Troubleshooting

### "OneBot HTTP port 3000 not listening"

QQ must be logged in. Open noVNC and scan the QR code. OneBot servers start only after login is complete.

### "Webhook returns ignored / event unknown"

Set `events: []` to accept all events from OneBot payloads (which use `post_type` instead of standard event headers). Use `filters` for field-level filtering instead.

### "MCP tools not appearing in Hermes"

1. Verify `snowluma-mcp` is in PATH: `which snowluma-mcp`
2. Verify the token and endpoint: `curl -H "Authorization: Bearer ***" http://127.0.0.1:3000/get_login_info`
3. Send `/reload-mcp` in a Hermes session
4. Check Hermes startup logs for MCP connection errors

### "QQ messages not reaching Hermes"

1. Confirm both services share the same `127.0.0.1` (same host)
2. Verify the httpClient URL matches the Hermes webhook route
3. Check SnowLuma logs for httpClient errors
4. Test with a manual curl POST to the webhook endpoint

### "Port conflict — another profile is using the gateway"

Each Hermes profile needs a unique port. Only one profile's gateway can run at a time on the same port.

### "Modified config but changes not applied"

- Config changes → restart gateway: `hermes -p <name> gateway restart`
- MCP config changes → send `/reload-mcp` in conversation (no gateway restart needed)
- `platform_toolsets` changes → must send `/reset` in QQ (new session), gateway restart alone is NOT enough
- `.env` changes → restart gateway required

### "Webhook rejects INSECURE_NO_AUTH"

Hermes refuses `INSECURE_NO_AUTH` when bound to a non-loopback host (e.g., `0.0.0.0`). Set `platforms.webhook.extra.host: "127.0.0.1"`.

---

## Files in This Repo

| File | Purpose |
|------|---------|
| `SKILL.md` | This file — main skill documentation |
| `README.md` | Project overview and quick start |
| `scripts/qq-command-handler.py` | Route script for OneBot payload preprocessing |
| `scripts/send-voice.py` | Pure sender script for audio files (base64:// via HTTP API) |
| `references/user-profile.md` | Template for QQ user profile (customize per deployment) |
| `references/container-architecture.md` | SnowLuma Docker container details |
| `references/voice-capability-research.md` | Detailed TTS/STT integration research |

---

## Verification Checklist

- [ ] `snowluma-mcp` is installed and in PATH
- [ ] `mcp_servers.snowluma` is in config.yaml with correct token and endpoint
- [ ] `/reload-mcp` returns the `mcp_snowluma_*` tools in the tool list
- [ ] `platforms.webhook` is configured with `qq-message` route, `script`, `group_by`
- [ ] Route script exists at `<profile>/scripts/qq-command-handler.py`
- [ ] `http://127.0.0.1:8644/health` returns `{"status": "ok", "platform": "webhook"}`
- [ ] SnowLuma httpClient URL is `http://127.0.0.1:8644/webhooks/qq-message`
- [ ] QQ is logged in and OneBot HTTP (port 3000) is listening
- [ ] Simulated webhook POST returns `{"status": "accepted"}`
- [ ] `/new` / `/reset` work and send confirmation to QQ
- [ ] `approvals.destructive_slash_confirm: false` is set (otherwise slash commands silently fail)
- [ ] Real QQ message triggers a webhook event visible in agent logs
- [ ] `tts` toolset is added to `platform_toolsets.webhook` (if voice needed)
