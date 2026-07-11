#!/usr/bin/env python3
"""
Pure audio sender — base64-encodes an audio file and sends it to QQ via OneBot HTTP API.

Usage:
    python3 scripts/send-voice.py <audio-file-path> [--user QQ号]

This script does NOT perform TTS generation. Use Hermes text_to_speech tool first,
then pass the generated MP3 file path to this script.

Part of the hermes-snowluma skill.
"""

import base64
import json
import os
import sys
import urllib.request

# === CONFIGURE THESE ===
SNOWLUMA_API = "http://127.0.0.1:3000"
SNOWLUMA_TOKEN = "YOUR_ONE_BOT_ACCESS_TOKEN"
DEFAULT_USER_ID = 12345678
# =======================


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("Usage: python3 scripts/send-voice.py <audio_file_path> [--user QQ_number]")
        print("Example: python3 scripts/send-voice.py /tmp/hello.mp3")
        print("         python3 scripts/send-voice.py /tmp/hello.mp3 --user 123456789")
        sys.exit(1)

    audio_path = sys.argv[1]
    user_id = DEFAULT_USER_ID

    if "--user" in sys.argv:
        idx = sys.argv.index("--user")
        if idx + 1 < len(sys.argv):
            user_id = int(sys.argv[idx + 1])

    if not os.path.exists(audio_path):
        print(f"File not found: {audio_path}")
        sys.exit(1)

    with open(audio_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")

    payload = {
        "user_id": user_id,
        "message": [{"type": "record", "data": {"file": f"base64://{b64}"}}]
    }

    req = urllib.request.Request(
        f"{SNOWLUMA_API}/send_private_msg",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {SNOWLUMA_TOKEN}"
        },
        method="POST"
    )

    resp = urllib.request.urlopen(req, timeout=30)
    result = json.loads(resp.read().decode())

    if result.get("status") == "ok":
        print(f"Voice sent successfully (message_id: {result['data']['message_id']})")
    else:
        print(f"Failed to send: {result}")
        sys.exit(1)


if __name__ == "__main__":
    main()
