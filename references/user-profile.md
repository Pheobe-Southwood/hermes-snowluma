# User Profile Template

This file serves as a template for documenting a QQ user's profile and preferences. Customize per deployment.

## Fields

- **QQ Number**: The user's QQ number
- **Name**: Display name or handle
- **Persona**: The bot's persona when interacting with this user (e.g. catgirl, assistant, etc.)
- **Communication Preferences**:
  - All replies go through `mcp__snowluma__invoke_action(action='send_private_msg')`
  - Keep messages short, one idea per message
  - No Markdown formatting
  - No emoji
- **Preferred TTS Provider**: elevenlabs / edge / openai (and voice_id)
- **Known Working Tools**: vision_analyze, terminal, tavily_search, etc.
- **Session History Notes**: Key learnings from past interactions

## Example

```markdown
# User: ExampleUser (QQ: 123456789)

## Communication Preferences
- All replies must go through MCP send_private_msg
- Short messages, one idea per message
- No Markdown, no emoji

## TTS Preferences
- Provider: elevenlabs
- Voice ID: your-elevenlabs-voice-id-here
- Model: eleven_multilingual_v2
```
