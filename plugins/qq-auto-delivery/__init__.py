"""
QQ Auto-Delivery Plugin

Automatically forwards ALL LLM text responses to the configured QQ user
via the OneBot HTTP API. No MCP tool calling needed for text.

Replaces the SOUL.md / skill instructions that told the LLM "you MUST
call mcp__snowluma__invoke_action to reply". With this plugin, the LLM
simply generates text content, and it's delivered to QQ automatically.

MCP tools are still used for non-text content (images, voice files, etc.)
"""

import json
import logging
import urllib.request

logger = logging.getLogger(__name__)

# OneBot API — matches qq-command-handler.py
ONE_BOT_API = "http://127.0.0.1:3000/"
ONE_BOT_TOKEN = "JT1k6oPp-imQAcAt8RfKsrnC7xnRmSvkYRkuaj52-0c"
TARGET_USER = 2085849951


def _send_text(text: str) -> None:
    """Send text to QQ user. Errors are logged, never crash the agent."""
    text = text.strip()
    if not text:
        return

    payload = {
        "action": "send_private_msg",
        "params": {"user_id": TARGET_USER, "message": text},
    }
    try:
        req = urllib.request.Request(
            ONE_BOT_API,
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {ONE_BOT_TOKEN}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read().decode())
            if result.get("status") == "ok" and result.get("retcode") == 0:
                logger.info("delivered to QQ: %r", text[:200])
            else:
                logger.warning(
                    "OneBot error: status=%s retcode=%s wording=%s",
                    result.get("status"),
                    result.get("retcode"),
                    result.get("wording", ""),
                )
    except Exception as e:
        logger.error("HTTP error: %s", e)


def deliver(response_text: str, **kwargs) -> str | None:
    """Forward every LLM text response to QQ.

    Fires once per turn via the transform_llm_output hook.
    Returns None so the response text passes through unchanged
    (it still goes to the webhook's ``deliver: log`` target,
    which is harmless).
    """
    if response_text and response_text.strip():
        _send_text(response_text)
    return None


def register(ctx):
    ctx.register_hook("transform_llm_output", deliver)
