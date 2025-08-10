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

        guild_id = str(interaction.guild.id)
        team_id = str(team.id)
        captain_id = captain.id

        config = load_config()

        if guild_id not in config.get("server", {}) or team_id not in config["server"][guild_id]["teams"]:
            await interaction.response.send_message("Server or team configuration not found.", ephemeral=True)
            return

        teams = config["server"][guild_id]["teams"]

        for t_id, t_data in teams.items():
            if t_data.get("captain") == captain_id:
                if t_id == team_id:
                    await interaction.response.send_message(
                        "This user is already the captain of this team.",
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        "This user is already the captain of another team.",
                        ephemeral=True
                    )
                return

        teams[team_id]["captain"] = captain.id
        save_config(config)

        me_id = 747440512729874452
        me = await self.bot.fetch_user(me_id)
        guild = interaction.user.guild
        await me.send(
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
