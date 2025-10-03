import json
import discord
from discord.ext import commands
from discord import app_commands
from utils import load_config, save_config, update_leaderboard


class SetCaptain(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="set-captain", description="Set the Captain for a Team")
    async def set_captain(self, interaction: discord.Interaction, team: discord.Role, captain: discord.Member):
        has_permission = any(role.name == "[OLY] Elo-Perms" for role in interaction.user.roles)
        if not has_permission:
            await interaction.response.send_message(
                "You need the `[OLY] Elo-Perms` role to use this command.",
                ephemeral=True
            )
            return

        guild = interaction.guild
        guild_id = str(guild.id)
        team_id = str(team.id)
        captain_id = captain.id

        config = load_config()

        if guild_id not in config.get("server", {}) or team_id not in config["server"][guild_id]["teams"]:
            await interaction.response.send_message("Server or team configuration not found.", ephemeral=True)
            return
        
        log_channel_id = config["server"][guild_id]["setup"].get("log_channel")
        log_channel = guild.get_channel(log_channel_id) if log_channel_id else None
        if log_channel is None:
            await interaction.response.send_message("Log channel is not set up.", ephemeral=True)
            return

        teams = config["server"][guild_id]["teams"]
        old_captain_id = teams[team_id].get("captain")

        # Check if already captain
        if old_captain_id == captain_id:
            await interaction.response.send_message(
                "This user is already the captain of this team.",
                ephemeral=True
            )
            return

        teams[team_id]["captain"] = captain_id

        captain_role = discord.utils.get(guild.roles, name="[OLY] Captain")
        if captain_role:
            try:
                await captain.add_roles(captain_role, reason="Set new Captain")
                if old_captain_id:
                    old_captain_member = guild.get_member(old_captain_id)
                    if old_captain_member:
                        await old_captain_member.remove_roles(captain_role, reason="Removed Captain")
            except discord.Forbidden:
                await interaction.response.send_message(
                    "Bot does not have permission to manage roles.",
                    ephemeral=True
                )
                return

        save_config(config)

        await log_channel.send(
            f" **Set Captain Log**\n"
            f"User: {interaction.user} ({interaction.user.id})\n"
            f"Guild: {guild.name} ({guild.id})\n"
            f"Team set: {team.name} ({team.id}) {captain.mention}"
        )

        await interaction.response.send_message(
            f"{captain.mention} has been successfully set as the captain of **{team.name}**.",
            ephemeral=True
        )

        await update_leaderboard(interaction)


async def setup(bot: commands.Bot):
    await bot.add_cog(SetCaptain(bot))
