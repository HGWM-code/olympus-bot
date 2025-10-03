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
        has_permission = any(role.name == "[OLY] Elo-Perms" for role in interaction.user.roles)

        if not has_permission:
            await interaction.response.send_message(
                "You need the `[OLY] Elo-Perms` role to use this command.",
                ephemeral=True
            )
            return 
        
        log_channel_id = load_config()["server"][str(interaction.guild.id)]["setup"]["log_channel"]
        if log_channel_id is None:
            await interaction.response.send_message("Log channel is not set up.", ephemeral=True)
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

            try:
                log_channel = interaction.guild.get_channel(log_channel_id)
                await log_channel.send(
                f"**Unregister Log**\n"
                f"User: {interaction.user} ({interaction.user.id})\n"
                f"Guild: {guild.name} ({guild.id})\n"
                f"Team removed: {team.name} ({team.id})"
            )
            except discord.Forbidden:
                pass
            except discord.HTTPException:
                pass
            
            await update_leaderboard(interaction)

async def setup(bot: commands.Bot):
    await bot.add_cog(unregister(bot))
