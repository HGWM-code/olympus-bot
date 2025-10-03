import os
import json
import discord
from dotenv import load_dotenv
from discord.ext import commands
from discord.ui import Button, View
import asyncio
from utils import load_config
from utils import save_config
from utils import inacitivity_watcher

load_dotenv()
TOKEN = os.getenv('BOT__TOKEN')

intents = discord.Intents.default()
intents.guilds = True
intents.guild_messages = True
intents.members = True
intents.dm_messages = True  
intents.message_content = True

bot = commands.Bot(command_prefix='$', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} has successfully connected to Discord.')

    try:
        synced = await bot.tree.sync()
        print(f"Successfully synced {len(synced)} commands.")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

    config = load_config()

    for guild in bot.guilds:
        guild_id = str(guild.id)  
        if guild_id not in config.get("server", {}):
            config["server"][guild_id] = {"teams": {}, "leaderboard":{}, "join_cooldowns": {}} 

        if "teams" not in config["server"][guild_id]:
            config["server"][guild_id]["teams"] = {}

        if "leaderboard" not in config["server"][guild_id]:
            config["server"][guild_id]["leaderboard"] = {}

        if "join_cooldowns" not in config["server"][guild_id]:
            config["server"][guild_id]["join_cooldowns"] = {}
        
        teams_config = config["server"][guild_id]["teams"]
        for team_id in teams_config:
            if "inactivity" not in teams_config[team_id]:
                teams_config[team_id]["inactivity"] = False
                save_config(config)
            elif teams_config[team_id]["inactivity"] == True:
                await inacitivity_watcher(team_id, guild)
            else:
                teams_config[team_id]["inactivity"] = False
                save_config(config)
        
        if "setup" not in config["server"][guild_id]:
            config["server"][guild_id]["setup"] = {
                "leaderboard_channel": None,
                "elo_update_channel": None,
                "elo_matches_category": None,
                "transactions_channel": None,
                "log_channel": None
            }
        save_config(config)

@bot.event
async def on_member_remove(member):
    config = load_config()
    guild_id = str(member.guild.id)
    teams = config["server"].get(guild_id, {}).get("teams", {})

    changed = False
    for team_id, team_data in teams.items():
        members_dict = team_data.get("member", {})
        for key in ["starters", "subs", "member"]:
            if key in members_dict and str(member.id) in members_dict[key]:
                del members_dict[key][str(member.id)]
                changed = True
        # Remove as captain if needed
        if str(team_data.get("captain")) == str(member.id):
            team_data["captain"] = None
            changed = True

    if changed:
        save_config(config)

async def load_cogs():
    await bot.load_extension('commands.register')
    await bot.load_extension('commands.unregister')
    await bot.load_extension('commands.update_elo')
    await bot.load_extension('commands.debug_update_elo')
    await bot.load_extension('commands.set_elo')
    await bot.load_extension('commands.set_record')
    await bot.load_extension('commands.challange')
    await bot.load_extension('commands.set_captain')
    await bot.load_extension('commands.reload_leaderboard')
    await bot.load_extension('commands.add_member')
    await bot.load_extension('commands.remove_member')
    await bot.load_extension('commands.leave_team')
    await bot.load_extension('commands.list_member')
    await bot.load_extension('commands.add_team_permission')
    await bot.load_extension('commands.remove_team_permission')
    await bot.load_extension('commands.set_inactivity')
    await bot.load_extension('commands.set_active')
    await bot.load_extension('commands.setup')

async def main():
    try:
        await load_cogs()
    except Exception as e:
        print(f"Error loading cogs: {e}")

    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())