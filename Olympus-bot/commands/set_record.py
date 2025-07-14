import json
import discord
from discord.ext import commands
from discord import app_commands
from utils import load_config
from utils import save_config
from utils import update_leaderboard


class set_record(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="set-record", description="Set the Record of a Team")
    async def set_record(self, interaction: discord.Interaction, team: discord.Role, record_wins: int, record_losses: int):
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

            teams[team_id]["record_wins"] = record_wins
            leaderboard[team_id]["record_wins"] = record_wins

            teams[team_id]["record_loses"] = record_losses
            leaderboard[team_id]["record_loses"] = record_losses

            save_config(config)
            
            await update_leaderboard(interaction)

async def setup(bot: commands.Bot):
    await bot.add_cog(set_record(bot))
