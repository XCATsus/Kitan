import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import random
import asyncio
import math
from math import floor
from dotenv import load_dotenv

# Bot configuration
XP_MULTIPLIER = 0.5  # XP per character in message
MIN_XP_PER_MESSAGE = 5  # Minimum XP per message
MAX_XP_PER_MESSAGE = 1000  # Maximum XP per message
XP_COOLDOWN = 3     # Cooldown in seconds between XP awards
BOT_COLOR = 0xfb02bd  # Embed color (hex color code)
MAX_LEVEL = 100     # Max level cap

# Level roles configuration - format: level: role_id
LEVEL_ROLES = {}

# Role names for display purposes - format: role_id: "role_name"
ROLE_NAMES = {}

# Starboard configuration
STARBOARD = {
    "enabled": False,
    "channel_id": 0,
    "emoji": "⭐",
    "threshold": 3  # Number of reactions needed to appear on starboard
}

# Channels to ignore for XP gain - list of channel IDs
IGNORED_CHANNELS = [
    0
]

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True

bot = commands.Bot(command_prefix='!', intents=intents)

XP_FILE = 'user_xp.json'
STARBOARD_FILE = 'starboard.json'
CONFIG_FILE = 'bot_config.json'

def load_xp_data():
    if os.path.exists(XP_FILE):
        with open(XP_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_xp_data(data):
    with open(XP_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def load_starboard_data():
    if os.path.exists(STARBOARD_FILE):
        with open(STARBOARD_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_starboard_data(data):
    with open(STARBOARD_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def load_config():
    global STARBOARD, LEVEL_ROLES, ROLE_NAMES, IGNORED_CHANNELS
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            
            if "starboard" in config:
                STARBOARD = config["starboard"]
            
            if "level_roles" in config:
                LEVEL_ROLES = {int(k): int(v) for k, v in config["level_roles"].items()}
            
            if "role_names" in config:
                ROLE_NAMES = {int(k): v for k, v in config["role_names"].items()}
            
            if "ignored_channels" in config:
                IGNORED_CHANNELS = [int(channel_id) for channel_id in config["ignored_channels"]]
                
            return config
    
    config = {
        "starboard": STARBOARD,
        "level_roles": {str(k): str(v) for k, v in LEVEL_ROLES.items()},
        "role_names": {str(k): v for k, v in ROLE_NAMES.items()},
        "ignored_channels": [str(channel_id) for channel_id in IGNORED_CHANNELS]
    }
    
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)
        
    return config

def save_config():
    config = {
        "starboard": STARBOARD,
        "level_roles": {str(k): str(v) for k, v in LEVEL_ROLES.items()},
        "role_names": {str(k): v for k, v in ROLE_NAMES.items()},
        "ignored_channels": [str(channel_id) for channel_id in IGNORED_CHANNELS]
    }
    
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

def advanced_xp_for_level(level):
    """Calculate XP needed for a specific level using Disgaea-style formula"""
    if level <= 1:
        return 0
    # Formula: XP = 0.04 * level^3 + 0.8 * level^2 + 2 * level
    return 11 * (50 + 0.04 * (level - 1)**3 + 0.8 * (level - 1)**2 + 2 * (level - 1) + 0.5)

def calculate_level(xp):
    """Calculate level based on total XP using advanced progression"""
    if xp <= 0:
        return 1
    
    low, high = 1, MAX_LEVEL
    while low <= high:
        mid = (low + high) // 2
        if advanced_xp_for_level(mid) <= xp < advanced_xp_for_level(mid + 1):
            return mid
        elif advanced_xp_for_level(mid) > xp:
            high = mid - 1
        else:
            low = mid + 1
    
    return min(low, MAX_LEVEL)

def calculate_message_xp(message):
    length = len(message.content)
    xp = int(length * XP_MULTIPLIER)
    xp = max(MIN_XP_PER_MESSAGE, min(xp, MAX_XP_PER_MESSAGE))
    xp += random.randint(0, 3)
    return xp

def is_admin(interaction: discord.Interaction):
    return interaction.user.guild_permissions.administrator

user_cooldowns = {}

@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')
    print(f'Bot is active in {len(bot.guilds)} guilds.')
    
    load_config()
    
    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    await bot.process_commands(message)
    if message.channel.id not in IGNORED_CHANNELS:
        await process_xp(message)
    
async def process_xp(message):
    user_id = str(message.author.id)
    current_time = asyncio.get_event_loop().time()
    
    if user_id in user_cooldowns and current_time - user_cooldowns[user_id] < XP_COOLDOWN:
        return
    
    user_cooldowns[user_id] = current_time
    xp_data = load_xp_data()
    
    if user_id not in xp_data:
        xp_data[user_id] = {
            "xp": 0,
            "level": 1,
            "username": message.author.name
        }
    
    xp_gained = calculate_message_xp(message)
    xp_data[user_id]["xp"] += xp_gained
    xp_data[user_id]["username"] = message.author.name
    
    current_level = xp_data[user_id]["level"]
    new_level = calculate_level(xp_data[user_id]["xp"])
    
    if new_level > current_level:
        xp_data[user_id]["level"] = new_level
        save_xp_data(xp_data)
        
        embed = discord.Embed(
            title="Level Up!",
            description=f"{message.author.mention} has reached level {new_level}!",
            color=BOT_COLOR
        )
        embed.set_thumbnail(url=message.author.display_avatar.url)
        await message.channel.send(embed=embed)
        
        await update_level_roles(message.guild, message.author, new_level)
    else:
        save_xp_data(xp_data)

async def update_level_roles(guild, member, new_level):
    """Update member's roles based on their level"""
    if not guild or not member:
        return
    
    sorted_levels = sorted(LEVEL_ROLES.keys())
    
    highest_role_level = None
    for level in sorted_levels:
        if new_level >= level:
            highest_role_level = level
        else:
            break
    
    if highest_role_level is None:
        return
    
    role_id = LEVEL_ROLES[highest_role_level]
    role = guild.get_role(role_id)
    
    if not role:
        print(f"Error: Role with ID {role_id} not found")
        return
    
    for level in LEVEL_ROLES:
        if level != highest_role_level:
            other_role_id = LEVEL_ROLES[level]
            other_role = guild.get_role(other_role_id)
            if other_role and other_role in member.roles:
                try:
                    await member.remove_roles(other_role)
                except Exception as e:
                    print(f"Failed to remove role {other_role.name}: {e}")
    
    if role not in member.roles:
        try:
            await member.add_roles(role)
            print(f"Added role {role.name} to {member.name}")
        except Exception as e:
            print(f"Failed to add role {role.name}: {e}")

@bot.event
async def on_raw_reaction_add(payload):
    """Handle starboard reactions"""
    if not STARBOARD["enabled"]:
        return
    member = await bot.get_guild(payload.guild_id).fetch_member(payload.user_id)
    if member.bot:
        return
    if str(payload.emoji) != STARBOARD["emoji"]:
        return
    channel = bot.get_channel(payload.channel_id)
    message = await channel.fetch_message(payload.message_id)
    if message.author.bot:
        return
    star_count = 0
    for reaction in message.reactions:
        if str(reaction.emoji) == STARBOARD["emoji"]:
            star_count = reaction.count
            break
    if star_count >= STARBOARD["threshold"]:
        await add_to_starboard(message, star_count)

async def add_to_starboard(message, star_count):
    """Add a message to the starboard"""
    starboard_data = load_starboard_data()
    
    message_id = str(message.id)
    if message_id in starboard_data:
        starboard_msg_id = starboard_data[message_id]["starboard_msg_id"]
        starboard_channel = bot.get_channel(STARBOARD["channel_id"])
        if not starboard_channel:
            return
        
        try:
            starboard_msg = await starboard_channel.fetch_message(int(starboard_msg_id))
            
            embed = starboard_msg.embeds[0]
            embed.set_footer(text=f"{STARBOARD['emoji']} {star_count}")
            
            await starboard_msg.edit(embed=embed)
            starboard_data[message_id]["stars"] = star_count
            save_starboard_data(starboard_data)
        except Exception as e:
            print(f"Error updating starboard message: {e}")
        
        return
    
    starboard_channel = bot.get_channel(STARBOARD["channel_id"])
    if not starboard_channel:
        print(f"Starboard channel with ID {STARBOARD['channel_id']} not found")
        return
    
    embed = discord.Embed(
        description=message.content,
        color=BOT_COLOR,
        timestamp=message.created_at
    )
    
    embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
    embed.set_footer(text=f"{STARBOARD['emoji']} {star_count}")
    embed.add_field(name="Source", value=f"[Jump to message]({message.jump_url})")
    
    if message.attachments and message.attachments[0].url.lower().endswith(('png', 'jpeg', 'jpg', 'gif', 'webp')):
        embed.set_image(url=message.attachments[0].url)
    
    try:
        starboard_msg = await starboard_channel.send(embed=embed)
        starboard_data[message_id] = {
            "starboard_msg_id": str(starboard_msg.id),
            "stars": star_count,
            "author": str(message.author.id),
            "channel": str(message.channel.id)
        }
        save_starboard_data(starboard_data)
    except Exception as e:
        print(f"Error adding message to starboard: {e}")

@bot.tree.command(name="rank", description="Check your or another user's XP and rank")
@app_commands.describe(member="The member whose rank you want to check")
async def rank(interaction: discord.Interaction, member: discord.Member = None):
    if member is None:
        member = interaction.user
    
    xp_data = load_xp_data()
    user_id = str(member.id)
    
    if user_id not in xp_data:
        embed = discord.Embed(
            description=f"{member.display_name} hasn't earned any XP yet!",
            color=BOT_COLOR
        )
        await interaction.response.send_message(embed=embed)
        return
    
    user_xp = xp_data[user_id]["xp"]
    user_level = xp_data[user_id]["level"]
    next_level_xp = advanced_xp_for_level(user_level + 1)
    current_level_xp = advanced_xp_for_level(user_level)
    
    if user_level >= MAX_LEVEL:
        progress_percent = 1
    else:
        progress = user_xp - current_level_xp
        needed = next_level_xp - current_level_xp
        progress_percent = progress / needed if needed > 0 else 1
    
    progress_bar = "■" * int(10 * progress_percent) + "□" * (10 - int(10 * progress_percent))
    
    xp_needed = next_level_xp - user_xp if user_level < MAX_LEVEL else 0
    
    embed = discord.Embed(
        title=f"{member.display_name}'s Rank",
        color=BOT_COLOR
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Level", value=str(user_level), inline=True)
    embed.add_field(name="Total XP", value=str(user_xp), inline=True)
    
    if user_level < MAX_LEVEL:
        embed.add_field(name="Next Level", value=f"{floor(user_xp)}/{floor(next_level_xp)}", inline=True)
        embed.add_field(name="Progress", value=f"{progress_bar} {int(progress_percent * 100)}%", inline=False)
        embed.add_field(name="XP Needed", value=f"{floor(xp_needed)} XP to level {user_level + 1}", inline=False)
    else:
        embed.add_field(name="Status", value="Maximum Level Reached!", inline=False)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="leaderboard", description="Show the XP leaderboard")
@app_commands.describe(limit="Number of users to show (default: 10)")
async def leaderboard(interaction: discord.Interaction, limit: int = 10):
    xp_data = load_xp_data()
    
    if not xp_data:
        embed = discord.Embed(
            description="No users have earned XP yet!",
            color=BOT_COLOR
        )
        await interaction.response.send_message(embed=embed)
        return
    
    sorted_users = sorted(xp_data.items(), key=lambda x: x[1]["xp"], reverse=True)
    
    embed = discord.Embed(
        title="📊 XP Leaderboard",
        color=BOT_COLOR
    )
    
    leaderboard_text = ""
    for index, (user_id, data) in enumerate(sorted_users[:limit], 1):
        username = data["username"]
        level = data["level"]
        xp = data["xp"]
        
        # Add emoji based on rank
        if index == 1:
            rank_emoji = "🥇"  # Gold medal for 1st place
        elif index == 2:
            rank_emoji = "🥈"  # Silver medal for 2nd place
        elif index == 3:
            rank_emoji = "🥉"  # Bronze medal for 3rd place
        else:
            rank_emoji = "⭐"  # General medal for others
            
        leaderboard_text += f"{rank_emoji} **{index}.** **{username}** - Level {level} ({xp} XP)\n"
    
    embed.description = leaderboard_text
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="help_xp", description="Show help for XP system")
async def help_xp(interaction: discord.Interaction):
    embed = discord.Embed(
        title="XP System Help",
        color=BOT_COLOR
    )
    
    embed.add_field(
        name="Commands",
        value=(
            "`/rank [user]` - Check your or another user's rank\n"
            "`/leaderboard [limit]` - Show the XP leaderboard\n"
            "`/help_xp` - Show this help message\n"
            "`/givexp` - (Admin only) Give XP to a user\n"
            "`/starboard_config` - (Admin only) Configure the starboard\n"
            "`/ignored_channels` - (Admin only) View/edit ignored channels"
        ),
        inline=False
    )
    
    embed.add_field(
        name="XP System",
        value=(
            f"• {XP_MULTIPLIER:.1f} XP per character in your message\n"
            f"• Minimum {MIN_XP_PER_MESSAGE} XP per message\n"
            f"• Maximum {MAX_XP_PER_MESSAGE} XP per message\n"
            f"• Cooldown: {XP_COOLDOWN} seconds between XP awards\n"
            f"• Advanced level system: Higher levels require exponentially more XP"
        ),
        inline=False
    )
    
    if LEVEL_ROLES:
        roles_text = ""
        for level, role_id in LEVEL_ROLES.items():
            role_name = ROLE_NAMES.get(role_id, f"Role ID: {role_id}")
            roles_text += f"• Level {level}: {role_name}\n"
        
        embed.add_field(name="Level Roles", value=roles_text, inline=False)
    
    if STARBOARD["enabled"]:
        embed.add_field(
            name="Starboard",
            value=(
                f"• React with {STARBOARD['emoji']} to add messages to the starboard\n"
                f"• Threshold: {STARBOARD['threshold']} {STARBOARD['emoji']} reactions\n"
                f"• Channel ID: {STARBOARD['channel_id']}"
            ),
            inline=False
        )

    if IGNORED_CHANNELS:
        ignored_text = "Channels where XP is not earned:\n"
        for i, channel_id in enumerate(IGNORED_CHANNELS[:5], 1):
            ignored_text += f"• Channel ID: {channel_id}\n"
        
        if len(IGNORED_CHANNELS) > 5:
            ignored_text += f"And {len(IGNORED_CHANNELS) - 5} more..."
            
        embed.add_field(name="Ignored Channels", value=ignored_text, inline=False)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="givexp", description="Give XP to a user (Admin only)")
@app_commands.describe(
    member="The member to give XP to",
    amount="Amount of XP to give"
)
async def givexp(interaction: discord.Interaction, member: discord.Member, amount: int):
    if not is_admin(interaction):
        embed = discord.Embed(
            description="❌ You don't have permission to use this command!",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    if amount <= 0:
        embed = discord.Embed(
            description="❌ XP amount must be positive!",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    xp_data = load_xp_data()
    user_id = str(member.id)

    if user_id not in xp_data:
        xp_data[user_id] = {
            "xp": 0,
            "level": 1,
            "username": member.name
        }
    
    old_xp = xp_data[user_id]["xp"]
    old_level = xp_data[user_id]["level"]
    
    xp_data[user_id]["xp"] += amount
    xp_data[user_id]["username"] = member.name
    
    new_level = calculate_level(xp_data[user_id]["xp"])
    level_change = new_level - old_level
    xp_data[user_id]["level"] = new_level
    
    save_xp_data(xp_data)
    
    embed = discord.Embed(
        title="XP Added",
        description=f"Added {amount} XP to {member.mention}",
        color=BOT_COLOR
    )
    embed.add_field(name="Previous XP", value=str(old_xp), inline=True)
    embed.add_field(name="New XP", value=str(xp_data[user_id]["xp"]), inline=True)
    
    if level_change > 0:
        if level_change == 1:
            embed.add_field(
                name="Level Up!",
                value=f"{member.display_name} is now level {new_level}!",
                inline=False
            )
        else:
            embed.add_field(
                name="Multiple Level Up!",
                value=f"{member.display_name} gained {level_change} levels and is now level {new_level}!",
                inline=False
            )
            
        await update_level_roles(interaction.guild, member, new_level)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="starboard_config", description="Configure the starboard (Admin only)")
@app_commands.describe(
    enabled="Enable or disable the starboard",
    emoji="The emoji to use for the starboard",
    threshold="Number of reactions needed to appear on starboard",
    channel_id="ID of the starboard channel"
)
async def starboard_config(
    interaction: discord.Interaction,
    enabled: bool = None,
    emoji: str = None,
    threshold: int = None,
    channel_id: str = None
):
    if not is_admin(interaction):
        embed = discord.Embed(
            description="❌ You don't have permission to use this command!",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    if enabled is not None:
        STARBOARD["enabled"] = enabled
    
    if emoji is not None:
        STARBOARD["emoji"] = emoji
    
    if threshold is not None:
        if threshold < 1:
            embed = discord.Embed(
                description="❌ Threshold must be at least 1!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        STARBOARD["threshold"] = threshold
    
    if channel_id is not None:
        try:
            channel_id_int = int(channel_id)
            STARBOARD["channel_id"] = channel_id_int
        except ValueError:
            embed = discord.Embed(
                description="❌ Invalid channel ID! Must be a number.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
    
    save_config()
    
    embed = discord.Embed(
        title="Starboard Configuration",
        description="Starboard settings have been updated!",
        color=BOT_COLOR
    )
    
    embed.add_field(name="Enabled", value=str(STARBOARD["enabled"]), inline=True)
    embed.add_field(name="Emoji", value=STARBOARD["emoji"], inline=True)
    embed.add_field(name="Threshold", value=str(STARBOARD["threshold"]), inline=True)
    embed.add_field(name="Channel ID", value=str(STARBOARD["channel_id"]), inline=True)
    
    channel = interaction.guild.get_channel(STARBOARD["channel_id"])
    if channel:
        embed.add_field(name="Channel Name", value=f"#{channel.name}", inline=True)
    else:
        embed.add_field(name="Warning", value="Channel with this ID not found in server", inline=False)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="ignored_channels", description="View or edit channels ignored for XP (Admin only)")
@app_commands.describe(
    action="Action to perform (view, add, remove)",
    channel_id="Channel ID to add or remove"
)
async def ignored_channels(
    interaction: discord.Interaction,
    action: str,
    channel_id: str = None
):
    if not is_admin(interaction):
        embed = discord.Embed(
            description="❌ You don't have permission to use this command!",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    global IGNORED_CHANNELS
    
    if action.lower() == "view":
        embed = discord.Embed(
            title="Ignored Channels",
            description="Channels where XP is not earned:",
            color=BOT_COLOR
        )
        
        if not IGNORED_CHANNELS:
            embed.description = "No channels are being ignored."
        else:
            channels_text = ""
            for i, channel_id in enumerate(IGNORED_CHANNELS, 1):
                channel = interaction.guild.get_channel(channel_id)
                if channel:
                    channels_text += f"{i}. {channel.mention} (ID: {channel_id})\n"
                else:
                    channels_text += f"{i}. Channel ID: {channel_id} (not found in server)\n"
            
            embed.description = channels_text
    
    elif action.lower() == "add":
        if not channel_id:
            embed = discord.Embed(
                description="❌ Please provide a channel ID to add.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            channel_id_int = int(channel_id)
            
            channel = interaction.guild.get_channel(channel_id_int)
            if not channel:
                embed = discord.Embed(
                    description=f"⚠️ Warning: Channel with ID {channel_id_int} not found in this server. Added anyway.",
                    color=discord.Color.gold()
                )
            else:
                if channel_id_int in IGNORED_CHANNELS:
                    embed = discord.Embed(
                        description=f"❌ Channel {channel.mention} is already in the ignored list.",
                        color=discord.Color.red()
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return
                
                embed = discord.Embed(
                    description=f"✅ Added {channel.mention} to ignored channels list.",
                    color=BOT_COLOR
                )
            
            IGNORED_CHANNELS.append(channel_id_int)
            save_config()
            
        except ValueError:
            embed = discord.Embed(
                description="❌ Invalid channel ID! Must be a number.",
                color=discord.Color.red()
            )
    
    elif action.lower() == "remove":
        if not channel_id:
            embed = discord.Embed(
                description="❌ Please provide a channel ID to remove.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            channel_id_int = int(channel_id)
            
            if channel_id_int not in IGNORED_CHANNELS:
                embed = discord.Embed(
                    description=f"❌ Channel ID {channel_id_int} is not in the ignored list.",
                    color=discord.Color.red()
                )
            else:
                IGNORED_CHANNELS.remove(channel_id_int)
                save_config()
                channel = interaction.guild.get_channel(channel_id_int)
                if channel:
                    embed = discord.Embed(
                        description=f"✅ Removed {channel.mention} from ignored channels list.",
                        color=BOT_COLOR
                    )
                else:
                    embed = discord.Embed(
                        description=f"✅ Removed channel ID {channel_id_int} from ignored channels list.",
                        color=BOT_COLOR
                    )
        except ValueError:
            embed = discord.Embed(
                description="❌ Invalid channel ID! Must be a number.",
                color=discord.Color.red()
            )
    
    else:
        embed = discord.Embed(
            description="❌ Invalid action! Use 'view', 'add', or 'remove'.",
            color=discord.Color.red()
        )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="role_config", description="Configure level roles (Admin only)")
@app_commands.describe(
    action="Action to perform (view, add, remove, update)",
    level="Level required for the role",
    role_id="ID of the role",
    role_name="Display name for the role"
)
async def role_config(
    interaction: discord.Interaction,
    action: str,
    level: int = None,
    role_id: str = None,
    role_name: str = None
):
    if not is_admin(interaction):
        embed = discord.Embed(
            description="❌ You don't have permission to use this command!",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    global LEVEL_ROLES, ROLE_NAMES

    if action.lower() == "view":
        embed = discord.Embed(
            title="Level Roles Configuration",
            description="Current level roles:",
            color=BOT_COLOR
        )
        
        if not LEVEL_ROLES:
            embed.description = "No level roles configured."
        else:
            sorted_levels = sorted(LEVEL_ROLES.keys())
            roles_text = ""
            
            for level in sorted_levels:
                role_id = LEVEL_ROLES[level]
                role_name = ROLE_NAMES.get(role_id, "Unknown")
                role = interaction.guild.get_role(role_id)
                if role:
                    roles_text += f"Level {level}: {role.mention} (ID: {role_id}, Name: {role_name})\n"
                else:
                    roles_text += f"Level {level}: Role ID {role_id} (not found in server, Name: {role_name})\n"
            
            embed.description = roles_text
    
    elif action.lower() == "add":
        if level is None or role_id is None:
            embed = discord.Embed(
                description="❌ Please provide both level and role ID.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            level_int = int(level)
            role_id_int = int(role_id)
            if level_int in LEVEL_ROLES:
                embed = discord.Embed(
                    description=f"❌ Level {level_int} already has a role assigned. Use 'update' to change it.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            role = interaction.guild.get_role(role_id_int)
            if not role:
                embed = discord.Embed(
                    description=f"⚠️ Warning: Role with ID {role_id_int} not found in this server. Added anyway.",
                    color=discord.Color.gold()
                )
            else:
                embed = discord.Embed(
                    description=f"✅ Added role {role.mention} for level {level_int}.",
                    color=BOT_COLOR
                )
            
            LEVEL_ROLES[level_int] = role_id_int
            
            if role_name:
                ROLE_NAMES[role_id_int] = role_name
            elif role:
                ROLE_NAMES[role_id_int] = role.name
            else:
                ROLE_NAMES[role_id_int] = f"Level {level_int} Role"
            
            save_config()
            
        except ValueError:
            embed = discord.Embed(
                description="❌ Invalid level or role ID! Both must be numbers.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
    
    elif action.lower() == "remove":
        if level is None:
            embed = discord.Embed(
                description="❌ Please provide the level to remove.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            level_int = int(level)
            
            if level_int not in LEVEL_ROLES:
                embed = discord.Embed(
                    description=f"❌ No role found for level {level_int}.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            role_id = LEVEL_ROLES[level_int]
            role = interaction.guild.get_role(role_id)
            
            del LEVEL_ROLES[level_int]
            
            role_still_used = False
            for _, other_role_id in LEVEL_ROLES.items():
                if other_role_id == role_id:
                    role_still_used = True
                    break

            if not role_still_used and role_id in ROLE_NAMES:
                del ROLE_NAMES[role_id]
            
            save_config()
            
            if role:
                embed = discord.Embed(
                    description=f"✅ Removed role {role.name} from level {level_int}.",
                    color=BOT_COLOR
                )
            else:
                embed = discord.Embed(
                    description=f"✅ Removed role ID {role_id} from level {level_int}.",
                    color=BOT_COLOR
                )
            
        except ValueError:
            embed = discord.Embed(
                description="❌ Invalid level! Must be a number.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
    
    elif action.lower() == "update":
        if level is None:
            embed = discord.Embed(
                description="❌ Please provide the level to update.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            level_int = int(level)
            
            if level_int not in LEVEL_ROLES:
                embed = discord.Embed(
                    description=f"❌ No role found for level {level_int}. Use 'add' to create it.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            old_role_id = LEVEL_ROLES[level_int]
            
            if role_id:
                role_id_int = int(role_id)
                LEVEL_ROLES[level_int] = role_id_int
                
                role = interaction.guild.get_role(role_id_int)
                
                if role and not role_name:
                    ROLE_NAMES[role_id_int] = role.name
            else:
                role_id_int = old_role_id
            
            if role_name:
                ROLE_NAMES[role_id_int] = role_name
            
            save_config()
            
            embed = discord.Embed(
                description=f"✅ Updated role configuration for level {level_int}.",
                color=BOT_COLOR
            )
            
        except ValueError:
            embed = discord.Embed(
                description="❌ Invalid level or role ID! Both must be numbers.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
    
    else:
        embed = discord.Embed(
            description="❌ Invalid action! Use 'view', 'add', 'remove', or 'update'.",
            color=discord.Color.red()
        )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="setup_wizard", description="Run setup wizard to configure the bot (Admin only)")
async def setup_wizard(interaction: discord.Interaction):
    if not is_admin(interaction):
        embed = discord.Embed(
            description="❌ You don't have permission to use this command!",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    embed = discord.Embed(
        title="Setup Wizard",
        description="Welcome to the XP Bot Setup Wizard! This wizard will help you configure the bot for your server.",
        color=BOT_COLOR
    )
    
    embed.add_field(
        name="Available Commands",
        value=(
            "Use these commands to set up different components:\n"
            "• `/starboard_config` - Configure the starboard\n"
            "• `/role_config` - Configure level roles\n"
            "• `/ignored_channels` - Configure channels to ignore\n"
            "• `/help_xp` - View current configuration and help"
        ),
        inline=False
    )
    
    embed.add_field(
        name="Quick Start Guide",
        value=(
            "1. Use `/role_config view` to see current role configuration\n"
            "2. Add level roles with `/role_config add [level] [role_id] [role_name]`\n"
            "3. Configure starboard with `/starboard_config`\n"
            "4. Set ignored channels with `/ignored_channels add [channel_id]`"
        ),
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

if __name__ == "__main__":
    load_config()
    load_dotenv()

    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN not set in environment or .env file")

    bot.run(token)
