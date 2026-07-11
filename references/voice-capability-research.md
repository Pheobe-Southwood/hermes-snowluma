# Voice Capability Research: SnowLuma QQ Bot + Hermes TTS/STT

## Context

Research findings for integrating TTS/STT with QQ bot via SnowLuma OneBot bridge.

## Hermes Side (Voice Mode)

Hermes supports Voice Mode natively on: CLI / Telegram / Discord
**QQ/OneBot is NOT supported out of the box.**

### TTS Config (text → voice)

| Provider | Quality | Cost | API Key |
|----------|---------|------|---------|
| Edge TTS (default) | Good | Free | None |
| OpenAI TTS | Good | Paid | `VOICE_TOOLS_OPENAI_KEY` |
| Mistral Voxtral TTS | Excellent | Paid | `MISTRAL_API_KEY` |
| ElevenLabs | Excellent | Paid | `ELEVENLABS_API_KEY` |

### Edge TTS Chinese Voices

```bash
pip install edge-tts
edge-tts --text "你好" --voice zh-CN-XiaoxiaoNeural --write-media hello.mp3
```

Common Chinese voices:
- `zh-CN-XiaoxiaoNeural` (female, default)
- `zh-CN-XiaoyiNeural` (female)
- `zh-CN-YunxiNeural` (male)
- `zh-CN-YunyangNeural` (male)

## SnowLuma / OneBot Side

### Verified Voice Actions

**Sending voice ✅** — `send_private_msg` / `send_group_msg` with message format:
- `[CQ:record,file=http://example.com/audio.mp3]` (URL)
- `[CQ:record,file=base64://<b64data>]` (base64 for small files)
- `[CQ:record,file=file:///tmp/snowluma-stream/upload/...]` (container-local path)

**Receiving voice related actions (exist, may error without cache):**
- `get_record` — Fails with "record not found in cache" if not cached
- `get_file` — Resolves cached image/voice IDs only
- `download_file` — Downloads files to server

### OneBot Version

- SnowLuma v1.12.0-node
- Protocol: OneBot v11

## Integration Paths

### Path A: TTS Only (Send Voice Replies)

1. Add `tts` to `platform_toolsets.webhook`
2. Generate audio via Hermes TTS tool
3. Send via `invoke_action` with `base64://` or HTTP API directly for larger files

### Path B: STT Only (Receive Voice)

1. Modify route script to detect voice messages
2. Extract voice URL from OneBot payload
3. Download + transcribe with faster-whisper
4. Inject transcription as message_context

### Path C: Bidirectional Voice (A + B)

Combine both approaches for full two-way voice.

## TTS Model Text Length Limits (ElevenLabs)

| model_id | Max Characters |
|----------|---------------|
| `eleven_flash_v2_5` | 40000 |
| `eleven_flash_v2` | 30000 |
| `eleven_multilingual_v2` | 10000 |
| `eleven_multilingual_v1` | 10000 |
| `eleven_english_sts_v2` | 10000 |
| `eleven_english_sts_v1` | 10000 |
| `eleven_v3` | 5000 |
| `eleven_ttv_v3` | 5000 |

## Custom TTS Providers (Non-Built-In)

Hermes provides **3 layers** of TTS extensibility:

1. **Built-in providers** — 10 native implementations (edge, openai, elevenlabs, minimax, xai, mistral, gemini, neutts, kittentts, piper)
2. **Command-type providers** — Shell command wrapper, no Python changes needed
3. **Plugin TTSProvider** (Python ABC) — Implement `TTSProvider` abstract class at `~/.hermes/plugins/tts/<name>/`

### Local TTS Model Feasibility (2 CPU, 3.8GB RAM, no GPU)

| Model | Viable? | Reason |
|-------|---------|--------|
| Edge TTS (cloud) | ✅ Best choice | Free, great Chinese, zero local cost |
| Piper | ⚠️ Marginal | CPU-runnable, poor Chinese quality |
| KittenTTS | ⚠️ Marginal | CPU-runnable |
| NeuTTS | ❌ Not suitable | Needs GPU |
| Fish Audio (cloud API) | ✅ Viable | API-based, no local cost |

## Key Code Paths

- TTS tool entry: `text_to_speech_tool()` in `tts_tool.py`
- Built-in providers: `BUILTIN_TTS_PROVIDERS` frozenset
- Command-type: checked after built-in, supports `{text_path}`, `{output_path}`, `{format}`, `{voice}`
- Plugin TTSProvider: `agent/tts_provider.py` ABC — official code reserves Fish Audio slot at line 34-35

### OpenAI TTS provider limitation

The OpenAI TTS provider has `DEFAULT_OPENAI_BASE_URL` hardcoded to `https://api.openai.com/v1` — does NOT support custom `base_url` via config. Workaround: command-type provider.
