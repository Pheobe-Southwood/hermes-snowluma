#!/usr/bin/env python3
"""
Route script for Hermes Webhook — preprocesses OneBot v11 payloads.

Key behaviors:
- Detects /new and /reset commands → sets message_context for gateway interception + sends QQ confirmation
- Normal messages → builds descriptive context with event type, QQ number, group, message text
- Outputs modified JSON to stdout

Prerequisites:
- Place this file at <profile>/scripts/qq-command-handler.py
- Set config.yaml route.script: qq-command-handler.py
- Set config.yaml route.prompt: "{message_context}"
- Token / API endpoint must be configured below
"""

import json
import sys
import urllib.request

# === CONFIGURE THESE ===
ONE_BOT_API = "http://127.0.0.1:3000/"
ONE_BOT_TOKEN = "YOUR_ONE_BOT_ACCESS_TOKEN"
# =======================


def build_context(payload):
    """Build a descriptive prompt context from the OneBot payload."""
    post_type = payload.get("post_type", "")
    message_type = payload.get("message_type", "")
    sub_type = payload.get("sub_type", "")
    user_id = payload.get("user_id", "")
    group_id = payload.get("group_id", "")
    self_id = payload.get("self_id", "")
    raw = payload.get("raw_message", "")
    return (
        "QQ事件 — 请处理：\n"
        "事件类型: " + str(post_type) + "\n"
        "消息类型: " + str(message_type) + "\n"
        "子类型: " + str(sub_type) + "\n"
        "发送者QQ: " + str(user_id) + "\n"
        "群号: " + str(group_id) + "\n"
        "QQ号: " + str(self_id) + "\n"
        "消息内容: " + str(raw)
    )


def send_qq_msg(user_id, text, group_id=None):
    """Send a message via OneBot HTTP API. Returns True on success."""
    action = "send_group_msg" if group_id else "send_private_msg"
    params = {"group_id": int(group_id)} if group_id else {"user_id": int(user_id)}
    params["message"] = text
    req = urllib.request.Request(
        ONE_BOT_API,
        data=json.dumps({"action": action, "params": params}).encode(),
        headers={
            "Authorization": "Bearer " + ONE_BOT_TOKEN,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read().decode())
            return result.get("status") == "ok"
    except Exception as e:
        sys.stderr.write("send_qq_msg failed: " + str(e) + "\n")
        return False


def main():
    payload = json.loads(sys.stdin.read())
    raw_message = payload.get("raw_message", "").strip()
    msg_type = payload.get("message_type", "")
    user_id = payload.get("user_id", "")
    group_id = payload.get("group_id") or None

    if raw_message in ("/new", "/reset"):
        payload["message_context"] = raw_message
        # Send confirmation through QQ
        confirm_text = (
            "Command received. "
            "Resetting conversation now \u200b~"
        )
        if msg_type == "group" and group_id:
            send_qq_msg(user_id, confirm_text, group_id=group_id)
        else:
            send_qq_msg(user_id, confirm_text)
    else:
        payload["message_context"] = build_context(payload)

    json.dump(payload, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()
