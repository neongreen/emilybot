# emilybot

## Development

### Setup

```bash
# Install dependencies
uv sync

# Run type checking
uv run pyright

# Start the bot (requires TOKEN environment variable)
DEV_MODE=True uv run emilybot
```

### Configuration

The bot uses SOPS for secret management. The Discord bot token is encrypted in `.env.yaml`.

### Deployment

Configured for deployment with Coolify using nixpacks. The `nixpacks.toml` handles SOPS decryption and app startup.

## Notes

### Discord Setup

1. Create bot at <https://discord.dev>
2. Enable 'message content intent' in bot settings
3. Add bot to server: `https://discord.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&scope=bot`
4. After that you can find the bot in server members list and DM it

### SOPS

Created encryption key with `age-keygen`, added to server as `SOPS_AGE_KEY` environment variable.
