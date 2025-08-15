import json
import discord
from discord.ext import commands
from discord import app_commands
from utils import load_config

class list_member(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="list-member", description="List all the Members of a Team")
    async def list_member(self, interaction: discord.Interaction, team: discord.Role):

        guild_id = str(interaction.guild.id)
        teams_id = str(team.id)
        
        config = load_config()
        teams = config["server"][guild_id]["teams"]
        members = config["server"][guild_id]["members"]

        starters = members.get("starters", {})
        subs = members.get("subs", {})
        member = members.get("member", {})

        if teams_id not in teams:
            await interaction.response.send_message(
                f"The team `{team.name}`is not registered.",
                ephemeral=True
            )
            return

        if len(starters) == 0 and len(subs) == 0 and len(member) == 0:
            await interaction.response.send_message(
                f"The team `{team.name}` has no members.",
                ephemeral=True
            )
            return
        
        class TeamPositions:
            def __init__(self, ws1):
                self.ws1 = ""
                self.setter = ""
                self.ws2 = ""
                self.ds1 = ""
                self.lib = ""
                self.ds2 = ""

        team_positions = TeamPositions()

        for member in starters:
            pos = member.get("position", "-")

            if pos == "wing-spiker" and TeamPositions.ws1 == "":
                team_positions.ws1 = member
            elif pos == "setter" and team_positions.setter == "":
                team_positions.setter = member
            elif pos == "libero" and team_positions.lib == "":
                team_positions.lib = member
            elif pos == "defensive-specialist" and team_positions.ds1 == "":
                team_positions.ds1 = member
            elif pos == "wing-spiker" and team_positions.ws2 == "":
                team_positions.ws2 = member
            elif pos == "defensive-specialist" and team_positions.ds2 == "":
                team_positions.ds2 = member
        
        member_list_embed = discord.Embed(
            title=f"{team.name} Member",
            color=team.colour()
        )
async def setup(bot: commands.Bot):
    await bot.add_cog(list_member(bot))
