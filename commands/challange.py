import json
import discord
from discord.ext import commands
from discord import app_commands
from utils import load_config, save_config, update_leaderboard

class MyCancelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.danger)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.channel.delete()
        except discord.NotFound:
            await interaction.response.send_message("This channel has already been deleted.", ephemeral=True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Canceled.", ephemeral=True)
        self.stop()


class MyCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="Delete Channel?",
            description="Are you sure you want to delete the channel?",
            color=discord.Color.red()
        )
        view = MyCancelView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class Challenge(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def check_permission(self, interaction, user_roles, challenging_team_id, teams):
        """Check if the user has Captain or Vice Captain permissions in the challenging team."""
        has_permission = any(role.name == "[OLY] Captain" for role in user_roles) or any(role.name == "[OLY] Vice Captain" for role in user_roles)
        if not has_permission:
            await interaction.response.send_message(
                "You need the `[OLY] Captain` or `[OLY] Vice Captain` role to use this command.",
                ephemeral=True
            )
            return False

        # Ensure the user is part of the challenging team
        if str(challenging_team_id) not in teams:
            await interaction.response.send_message(
                "You are not part of the challenging team.",
                ephemeral=True
            )
            return False

        # Ensure the user is actually in the challenging team
        user_team = None
        for team_id in teams:
            if int(team_id) in [role.id for role in user_roles]:
                user_team = team_id
                break

        if user_team != str(challenging_team_id):
            await interaction.response.send_message(
                "You can only challenge on behalf of your own team.",
                ephemeral=True
            )
            return False

        return True

    @app_commands.command(name="challenge", description="Challenge a team to an Elo match")
    async def challenge(self, interaction: discord.Interaction, challenging_team: discord.Role, challenged_team: discord.Role):
        guild = interaction.guild
        guild_id = guild.id
        config = load_config()

        interaction_user_roles = interaction.user.roles
        teams = config["server"][str(guild_id)]["teams"]

        # Check if the user has permissions in the challenging team
        check_perms = await self.check_permission(interaction, interaction_user_roles, challenging_team.id, teams)
        if not check_perms:
            return

        # Get the roles of both the challenging team and the challenged team
        team1 = discord.utils.get(guild.roles, id=challenging_team.id)
        team2 = discord.utils.get(guild.roles, id=challenged_team.id)

        # Check if both teams exist in the configuration
        missing_teams = []
        if str(challenging_team.id) not in teams:
            missing_teams.append(f"**{challenging_team.name}** (challenging team)")
        if str(challenged_team.id) not in teams:
            missing_teams.append(f"**{challenged_team.name}** (challenged team)")

        if missing_teams:
            await interaction.response.send_message(
                f"One or both of the teams are not registered. The following teams are missing:\n" + "\n".join(missing_teams),
                ephemeral=True
            )
            return

        # Now both teams are confirmed to be valid
        category = discord.utils.get(guild.categories, id=1398701108515573851)  # Specify your category ID

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }

        # Identify captains and vice captains in the team configuration
        captains_and_vps = []

        # Check captains and vice captains in the configuration and add them
        for team in [team1, team2]:
            team_id = str(team.id)
            team_data = teams.get(team_id, {})
            captain_id = team_data.get("captain", None)
            # Check for captain
            if captain_id:
                captain_member = guild.get_member(captain_id)
                if captain_member:
                    captains_and_vps.append(captain_member)
            
            # Check for vice-captains in the team (starters, subs, and members)
            for rank_key in ["starters", "subs", "member"]:
                for member_id, member_obj in team_data.get("member", {}).get(rank_key, {}).items():
                    if "permissions" in member_obj and "vize-captain" in member_obj["permissions"]:
                        member = guild.get_member(int(member_id))
                        if member:
                            captains_and_vps.append(member)

        # Add captains and vice captains to the channel's permission overwrites
        for captain_or_vp in captains_and_vps:
            overwrites[captain_or_vp] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        if category:
            for role in category.overwrites:
                if isinstance(role, discord.Role) and category.overwrites[role].view_channel:
                    overwrites[role] = discord.PermissionOverwrite(view_channel=True)

        # Create a new channel for the match
        channel_name = f"{team1.name}-vs-{team2.name}".lower().replace(" ", "-")
        new_channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites
        )

        embed = discord.Embed(
            title="Welcome!",
            description=f"Here you can plan the match {team1.mention} vs {team2.mention}\n **You have 3 days to schedule**",
            color=discord.Color.blurple()
        )
        welcomeEmbedView = MyCloseView()

        await new_channel.send(
            f"<@&1353495574556573717> <@&1353495581875769447> <@&1353495582609768541> \n{team1.mention} {team2.mention}",
            embed=embed,
            view=welcomeEmbedView
        )

        # Now ping the newly created channel using `#` symbol
        await interaction.response.send_message(
            f"Match channel {new_channel.mention} has been created",
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Challenge(bot))
