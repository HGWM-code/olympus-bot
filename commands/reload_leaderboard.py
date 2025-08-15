import json
import discord
from discord.ext import commands
from discord import app_commands
from utils import load_config
from utils import save_config
from utils import update_leaderboard
import asyncio


class reload_leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="reload-leaderboard", description="Reload the leaderboard")
    async def reload_leaderboard(self, interaction: discord.Interaction):
        has_permission = any(role.name == "[OLY] Elo-Perms" for role in interaction.user.roles)
        config = load_config()
        guild_id = interaction.user.guild.id
        config_reload =  config["server"][str(guild_id)]["reload_leaderboard"]

        if not has_permission:
            await interaction.response.send_message(
                "You need the `[OLY] Elo-Perms` role to use this command.",
                ephemeral=True
            )
            return 
        
        if config_reload == False:
            config_reload = True
            save_config(config)
            
            while True:
                await update_leaderboard(interaction)
                await asyncio.sleep(3600)

async def setup(bot: commands.Bot):
    await bot.add_cog(reload_leaderboard(bot))
