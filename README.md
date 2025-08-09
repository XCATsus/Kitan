# Kitan
A lightweight Python Discord bot with an innovative, length‑based XP system for fair progression.

## Leveling features
- **Length‑based XP:** XP scales with message length, with sensible caps to prevent abuse.
- **Cooldown and filters:** Per‑user cooldown to deter spam; ignores bots and webhooks.
- **Progression curve:** Quadratic/cubic‑style thresholds for smooth level pacing.
- **Slash commands:** View rank/XP, leaderboards, and configure leveling.

## Starboard
When a message reaches the configured reaction threshold (using your chosen emoji), Kitan posts it to the starboard channel with author, content, and the link to the original message.

## Getting started
### Prerequisites
Python 3.10+ and a Discord application/bot with a token.

> [!IMPORTANT]
> Make sure to enable **Message Content** and **Server Members** intents for your bot on the Discord Developer Portal!

### Installation
> [!TIP]
> Consider using a virtual environment (`python -m venv .venv && source .venv/bin/activate` on macOS/Linux, `.venv\Scripts\activate` on Windows) before installing dependencies.

1. Clone the repository and install dependencies by running:
```python
pip install -r requirements.txt
```
3. Start the bot using:
```bash
python main.py
```
## Configuration

### Basic
Run `/setup_wizard` and follow the prompts.

### Advanced
> [!NOTE]
> Advanced configuration requires modifying the code (`main.py`).

Available variables:
- **XP_MULTIPLIER** - XP per character in message
- **MIN_XP_PER_MESSAGE** - Minimum XP per message
- **MAX_XP_PER_MESSAGE** - Maximum XP per message
- **XP_COOLDOWN** - Cooldown in seconds between XP awards
- **BOT_COLOR** - Embed color (hex color code)
- **MAX_LEVEL** - Max level cap

Changing the level formula:
- Find the `advanced_xp_for_level` function and change the formula after `return` using Python's syntax.

## Commands overview:
- `/rank` - Check your or another user's rank.
- `/leaderboard` - Show the XP leaderboard.
- `/help_xp` - Show the help message.
- `/givexp` - (Admin only) Give XP to a user.
- `/starboard_config` - (Admin only) Configure the starboard.
- `/ignored_channels` - (Admin only) View/edit ignored channels.
- `/role_config` - (Admin only) Configure level roles.

## Permissions
- General: the bot needs the read and send messages permissions.
- For level roles: the bot needs Manage Roles and must be higher than the target roles in the server’s role hierarchy.
- For starboard posting: the bot needs permission to read and send messages (and embed links) on the starboard channel.

## Troubleshooting

### Slash commands not appearing:
 - Ensure the bot was invited with application.commands scope.
 - Give it a minute after first run; commands sync on startup.

### No XP awarded:
- Verify Message Content intent is enabled in the Developer Portal and in code.
- Check that the channel isn’t in ignored channels.
- Cooldown may be preventing frequent awards.

### Role assignment fails:
- Confirm Manage Roles permission and role order (bot’s top role above target roles).

### Starboard not posting:
- Check the configured channel ID and that the bot has permission there.
- Ensure the emoji and threshold are set correctly.
