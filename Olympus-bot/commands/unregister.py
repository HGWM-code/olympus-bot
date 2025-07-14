import json
import discord
from discord.ext import commands
from discord import app_commands
from utils import load_config
from utils import save_config
from utils import update_leaderboard


class unregister(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="unregister", description="Unregister a Team for the Elo-Rating")
    async def unregister(self, interaction: discord.Interaction, team: discord.Role):
        has_permission = any(role.name == "elo-perms" for role in interaction.user.roles)

        if not has_permission:
            await interaction.response.send_message(
                "You need the `elo-perms` role to use this command.",
                ephemeral=True
            )
            return 

        guild = interaction.user.guild
        guild_id = guild.id
        config = load_config()
        team_id = str(team.id)

        teams = config["server"][str(guild_id)]["teams"]
        leaderboard = config["server"][str(guild_id)]["leaderboard"]

        if team_id not in teams:
            await interaction.response.send_message("Team is not registered.", ephemeral=True)

        else:

            del teams[team_id]
            del leaderboard[team_id]

            save_config(config)
            
            await update_leaderboard(interaction)

async def setup(bot: commands.Bot):
    await bot.add_cog(unregister(bot))
