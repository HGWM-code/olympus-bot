import os
import json
import discord
from dotenv import load_dotenv
from discord.ext import commands
from discord.ui import Button, View
import asyncio
from utils import load_config
from utils import save_config

load_dotenv()
TOKEN = os.getenv('BOT__TOKEN')

intents = discord.Intents.default()
intents.guilds = True 
intents.guild_messages = True
intents.messages = True

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
            config["server"][guild_id] = {"teams": {}, "leaderboard":{}} 

    save_config(config)
        

async def load_cogs():
    await bot.load_extension('commands.register')
    await bot.load_extension('commands.unregister')
    await bot.load_extension('commands.update_elo')
    await bot.load_extension('commands.set_elo')
    await bot.load_extension('commands.set_record')

async def main():
    try:
        await load_cogs()
    except Exception as e:
        print(f"Error loading cogs: {e}")

    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())