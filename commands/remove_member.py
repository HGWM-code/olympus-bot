import json
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from utils import load_config, save_config


class remove_member(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="remove_member", description="Remove a member from a team")
    async def remove_member(
        self,
        interaction: discord.Interaction,
        team: discord.Role,
        user: discord.Member
    ):
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        guild_id = str(guild.id)
        config = load_config()

        team_id = str(team.id)
        team_data = config["server"][guild_id]["teams"].get(team_id)
        if not team_data:
            await interaction.followup.send("Team not found.", ephemeral=True)
            return
        
        log_channel_id = config["server"][guild_id]["setup"]["transactions_channel"]
        if log_channel_id is None:
            await interaction.followup.send("Transaction channel is not set up.", ephemeral=True)
            return

        has_permission = any(role.name == "[OLY] Captain" for role in interaction.user.roles)
        has_team_permission = any(role.name == "[OLY] Team Perms" for role in interaction.user.roles)

        captain_id = team_data.get("captain")  
        if not (has_team_permission or has_permission or interaction.user.id == captain_id):
            await interaction.followup.send("You are not authorized to remove members from this team.", ephemeral=True)
            return

        members = team_data.get("member", {})
        starters = members.get("starters", {})
        subs = members.get("subs", {})
        team_members = members.get("member", {})

        removed = False
        # Check if user is in starters, subs, or member ranks
        if str(user.id) in starters:
            del starters[str(user.id)]
            removed = True
        elif str(user.id) in subs:
            del subs[str(user.id)]
            removed = True
        elif str(user.id) in team_members:
            del team_members[str(user.id)]
            removed = True

        if not removed:
            await interaction.followup.send("User is not a member of this team.", ephemeral=True)
            return

        try:
            member = await interaction.guild.fetch_member(user.id)
            await member.remove_roles(team)
        except discord.HTTPException as e:
            await interaction.followup.send("Failed to remove role.", ephemeral=True)
            print(f"Role removal error: {e}")
            return

        tz = ZoneInfo("Europe/Berlin")

        # Check if the user has the [OLY] Vice Captain role in any other team
        vice_captain_role = discord.utils.get(guild.roles, name="[OLY] Vice Captain")
        if vice_captain_role:
            # Check if the user is still a vice-captain in any other team
            is_vice_captain_in_other_teams = False
            for team_id, team_data in config["server"][guild_id]["teams"].items():
                for rank_key in ("starters", "subs", "member"):  # Include "member" as well
                    for member_id, member_obj in team_data["member"].get(rank_key, {}).items():
                        if member_id == str(user.id) and "permissions" in member_obj and "vize-captain" in member_obj["permissions"]:
                            is_vice_captain_in_other_teams = True
                            break
                if is_vice_captain_in_other_teams:
                    break
            
            # Remove vice-captain role only if the user is no longer a vice-captain in any team
            if not is_vice_captain_in_other_teams:
                await member.remove_roles(vice_captain_role)

        save_config(config)

        channel = guild.get_channel(log_channel_id)
        if channel:
            embed = discord.Embed(
                title=f"{team.name} Transaction",
                description=f"{team.mention} have **released** {user.mention}.",
                color=discord.Color.red(),
                timestamp=datetime.now(tz)
            )

            embed.set_author(
                name=guild.name,
                icon_url=guild.icon.url if guild.icon else discord.Embed.Empty
            )
            embed.add_field(name="Removed by", value=interaction.user.mention, inline=True)
            embed.set_thumbnail(url=user.display_avatar.url)

            await channel.send(embed=embed)

        await interaction.followup.send(
            f"{user.mention} has been removed from {team.mention}",
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(remove_member(bot))
