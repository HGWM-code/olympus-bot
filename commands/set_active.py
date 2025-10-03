import json
import discord
from discord.ext import commands
from discord import app_commands
from utils import load_config
from utils import save_config
from utils import inacitivity_watcher
import asyncio



class set_active(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="set-active", description="Set a Team as Active")
    async def set_active(self, interaction: discord.Interaction, team: discord.Role):
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


        if team_id not in teams:
            await interaction.response.send_message(
                "Team is not registered.",
                ephemeral=True
            )
            return
        
        if "inactivity" not in teams[team_id]:
            teams[team_id]["inactivity"] = False

        if teams[team_id]["inactivity"] == False:
            await interaction.response.send_message(
                f"The team `{team.name}` is already set as active.",
                ephemeral=True
            )
            return
        else:

            teams[team_id]["inactivity"] = False
            save_config(config)

            me_id = 747440512729874452
            try:
                    me = await self.bot.fetch_user(me_id)
                    await me.send(
                        f"**Set Activity Log**\n"
                        f"User: {interaction.user} ({interaction.user.id})\n"
                        f"Guild: {guild.name} ({guild.id})\n"
                        f"Team: {team.name} ({team.id}) -> Active"
                    )
            except (discord.Forbidden, discord.HTTPException):
                    pass
                
            await interaction.response.send_message(f"Activity set for {team.mention}", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(set_active(bot))