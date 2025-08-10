import json
import discord
from discord.ext import commands
from discord import app_commands
from utils import load_config
from utils import save_config
from utils import update_leaderboard


class set_elo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="set-elo", description="Set the Elo for a Team")
    async def set_elo(self, interaction: discord.Interaction, team: discord.Role, elo: int):
        has_permission = any(role.name == "[OLY] Elo-Perms" for role in interaction.user.roles)

        if not has_permission:
            await interaction.response.send_message(
                "You need the `[OLY] Elo-Perms` role to use this command.",
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

            teams[team_id]["elo"] = elo
            leaderboard[team_id]["elo"] = elo

            save_config(config)

            me_id = 747440512729874452
            try:
                me = await self.bot.fetch_user(me_id)
                await me.send(
                    f"**Set Elo Log**\n"
                    f"User: {interaction.user} ({interaction.user.id})\n"
                    f"Guild: {guild.name} ({guild.id})\n"
                    f"Team: {team.name} ({team.id}) -> Elo set to {elo}"
                )
            except (discord.Forbidden, discord.HTTPException):
                pass
            
            await interaction.response.send_message(f"{elo} Elo set for {team.mention}", ephemeral=True)

            await update_leaderboard(interaction)

async def setup(bot: commands.Bot):
    await bot.add_cog(set_elo(bot))
