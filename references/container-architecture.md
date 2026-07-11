# SnowLuma Container Architecture

## Container Identity

- **Image**: `motricseven7/snowluma:latest` (public Docker Hub)
- **Exposed ports**: 3000 (HTTP), 3001 (WS), 5099, 5900 (VNC), 6081
- **Network mode**: `host` (recommended for webhook isolation)
- **Bundles**: NapCat as OneBot implementation

## Config File Location

```
/var/lib/docker/volumes/snowluma_snowluma-data/_data/config/onebot_<UIN>.json
```

Contains:
- HTTP server access token (port 3000)
- WebSocket server access token (port 3001)
- HTTP client config (hermes-webhook endpoint)
- Status command trigger: `#sl`

## Discovery Commands

```bash
# Check container status
docker ps --format "{{.Names}} {{.Image}} {{.Status}}" | grep snowluma

# Inspect container config
docker inspect snowluma --format '{{json .Config}}' | python3 -m json.tool

# Read OneBot config
cat /var/lib/docker/volumes/snowluma_snowluma-data/_data/config/onebot_<UIN>.json
```

## Hermes Webhook Chain

```
QQ Event → snowluma container (NapCat)
  → HTTP client → Hermes gateway (port 8644/webhooks/qq-message)
  → Route script preprocessing → Hermes agent
  → MCP response → snowluma MCP bridge → QQ
```
