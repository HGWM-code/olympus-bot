import json
import discord
from discord.ext import commands
from discord import app_commands
from utils import load_config
from utils import save_config
from utils import inacitivity_watcher
import asyncio



class set_inactivity(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="set-inactivity", description="Set a Team as Inactive")
    async def set_inactivity(self, interaction: discord.Interaction, team: discord.Role):
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

        if teams[team_id]["inactivity"] == True:
            await interaction.response.send_message(
                f"The team `{team.name}` is already set as inactive.",
                ephemeral=True
            )
            return
        else:
            old_elo = teams[team_id]["elo"]
            new_elo = teams[team_id]["elo"] - 50
            teams[team_id]["inactivity"] = True
            save_config(config)

            embed = discord.Embed(
                title=f"Inactivity Elo loss",
                description=(
                    f"**{team.name}** is now set as inactive.\n"
                    f"ELO: **{int(old_elo)}** -> **{int(new_elo)}** (-50)\n"
                ),
                color=discord.Color.red()
            )

            embed.description += f"\n\nset by {interaction.userser.mention}"

            result_channel = interaction.guild.get_channel(1387116562292408400)
            await result_channel.send(embed=embed)

            me_id = 747440512729874452
            try:
                    me = await self.bot.fetch_user(me_id)
                    await me.send(
                        f"**Set Inactivity Log**\n"
                        f"User: {interaction.user} ({interaction.user.id})\n"
                        f"Guild: {guild.name} ({guild.id})\n"
                        f"Team: {team.name} ({team.id}) -> Inactivity {old_elo} -> {new_elo}"
                    )
            except (discord.Forbidden, discord.HTTPException):
                    pass
                
            await interaction.response.send_message(f"Inactivity set for {team.mention}", ephemeral=True)
            await inacitivity_watcher(team_id, guild)

async def setup(bot: commands.Bot):
    await bot.add_cog(set_inactivity(bot))