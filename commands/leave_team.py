import json
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from utils import load_config, save_config

class leave_team(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="leave-team", description="Leave from a team")
    async def leave_team(
        self,
        interaction: discord.Interaction,
        team: discord.Role
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
        
        log_channel_id = config["server"][str(interaction.guild.id)]["setup"]["transactions_channel"]
        channel = guild.get_channel(int(log_channel_id))
        if log_channel_id is None:
            await interaction.followup.send("Transaction channel is not set up.", ephemeral=True)
            return

        members = team_data.get("member", {})
        removed = False
        user_id_str = str(interaction.user.id)

        # Check and remove the user from each bucket if present
        for bucket in ("starters", "subs", "member"):
            if user_id_str in members.get(bucket, {}):
                del members[bucket][user_id_str]
                removed = True
                break

        if not removed:
            await interaction.followup.send("You are not a member of this team.", ephemeral=True)
            return

        save_config(config)

        # remove role
        try:
            await interaction.user.remove_roles(team)
        except discord.HTTPException as e:
            await interaction.followup.send("Failed to remove role.", ephemeral=True)
            print(f"Role removal error: {e}")
            return

        # Check if the user has the [OLY] Vice Captain role in any other team
        vice_captain_role = discord.utils.get(guild.roles, name="[OLY] Vice Captain")
        if vice_captain_role:
            # Check if the user is still a vice-captain in any other team
            is_vice_captain_in_other_teams = False
            for team_id, team_data in config["server"][guild_id]["teams"].items():
                for rank_key in ("starters", "subs", "member"):  # Include "member" as well
                    for member_id, member_obj in team_data["member"].get(rank_key, {}).items():
                        if member_id == str(interaction.user.id) and "permissions" in member_obj and "vize-captain" in member_obj["permissions"]:
                            is_vice_captain_in_other_teams = True
                            break
                if is_vice_captain_in_other_teams:
                    break
            
            # Remove vice-captain role only if the user is no longer a vice-captain in any team
            if not is_vice_captain_in_other_teams:
                await interaction.user.remove_roles(vice_captain_role)

        tz = ZoneInfo("Europe/Berlin")
        save_config(config)

        if channel:
            embed = discord.Embed(
                title=f"{team.name} Transaction",
                description=f"{interaction.user.mention} has **left** {team.mention}.",
                color=discord.Color.red(),
                timestamp=datetime.now(tz)
            )

            embed.set_author(
                name=guild.name,
                icon_url=guild.icon.url if guild.icon else discord.Embed.Empty
            )
            embed.set_thumbnail(url=interaction.user.display_avatar.url)

            await channel.send(embed=embed)

        await interaction.followup.send(
            f"You left from {team.mention}",
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(leave_team(bot))
