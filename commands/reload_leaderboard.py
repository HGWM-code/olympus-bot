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

        if not has_permission:
            await interaction.response.send_message(
                "You need the `[OLY] Elo-Perms` role to use this command.",
                ephemeral=True
            )
            return 
         
        await update_leaderboard(interaction)

async def setup(bot: commands.Bot):
    await bot.add_cog(reload_leaderboard(bot))
