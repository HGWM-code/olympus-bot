import json
import discord
from discord.ext import commands
from discord import app_commands
from utils import load_config
from utils import save_config
from utils import update_leaderboard


class challange(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def check_permission(self, interaction, team, interactionUserRoles, teams):

        has_permission = any(role.name == "[OLY] Captain" for role in interaction.user.roles)
        if not has_permission:
            await interaction.response.send_message(
                "You need the `[OLY] Captain` role to use this command.",
                ephemeral=True
            )
            return  False
        
        for team in teams:
            if int(team) in [role.id for role in interactionUserRoles]:
                await interaction.response.send_message(
                "You are not part of a Team.",
                ephemeral=True
            )
            return  False

        if str(team.id) not in teams:
            await interaction.response.send_message(
                "The Team you are trying to challange is not registered", 
                ephemeral=True
            )
            return False
        
        return True


    @app_commands.command(name="challange", description="Callange a team for an Elo Match")
    async def challange(self, interaction: discord.Interaction, team: discord.Role):

        guild = interaction.user.guild
        guild_id = guild.id
        config = load_config()
        interactionUserRoles = interaction.user.roles()
        teams = config["server"][str(guild_id)]["teams"]

        check_perms = challange.check_permission(interaction, team, interactionUserRoles, teams)

        if check_perms == True:

            for team in teams:
                if int(team) in [role.id for role in interactionUserRoles]:
                    team1 = team

            category = discord.utils.get(guild.categories, id=1398701108515573851)

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            }

            for member in guild.members:
                has_captain_role = any(role.name == "[OLY] Captain" for role in member.roles)
                has_team_role = any(role.id == team.id for role in member.roles)
                if has_captain_role and has_team_role:
                    overwrites[member] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

            if category:
                for role in category.overwrites:
                    if isinstance(role, discord.Role) and category.overwrites[role].view_channel:
                        overwrites[role] = discord.PermissionOverwrite(view_channel=True)

            await guild.create_text_channel(
                name=f"{team1}-vs-{team}",
                category=category,
                overwrites=overwrites
            )
            
async def setup(bot: commands.Bot):
    await bot.add_cog(challange(bot))
