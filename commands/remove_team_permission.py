import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, Tuple
from utils import load_config, save_config
from datetime import datetime
from zoneinfo import ZoneInfo

# Display label, stored value for permissions
PERMISSION_OPTIONS = [
    ("Add Member", "add-member"),
    ("Remove Member", "remove-member"),
    ("Vice-Captain", "vize-captain"),
]

class remove_team_permission(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ---------- helpers ----------
    @staticmethod
    def _get_guild_config(config: dict, guild_id: int) -> dict:
        gid = str(guild_id)
        if "server" not in config:
            config["server"] = {}
        if gid not in config["server"]:
            config["server"][gid] = {
                "teams": {},
                "leaderboard": {},
                "join_cooldowns": {}
            }
        return config["server"][gid]

    @staticmethod
    def _find_member_entry(team_data: dict, user_id: int) -> Optional[Tuple[str, dict]]:
        """Find user in starters/subs/member. Returns (rank_key, member_obj) or None."""
        user_id_str = str(user_id)
        members = team_data.get("member", {})
        for rank_key in ("starters", "subs", "member"):
            rank_dict = members.get(rank_key, {})
            if user_id_str in rank_dict:
                return rank_key, rank_dict[user_id_str]
        return None

    @staticmethod
    def _author_is_captain_or_vize(team_data: dict, author_id: int) -> bool:
        """True if the author is the captain or has the vize-captain permission in this team."""
        if team_data.get("captain") == author_id:
            return True
        found = remove_team_permission._find_member_entry(team_data, author_id)
        if not found:
            return False
        _rank, member_obj = found
        perms = member_obj.get("permissions", {}) or {}
        return bool(perms.get("vize-captain"))

    # ---------- interactive UI ----------
    class PermissionSelectView(discord.ui.View):
        def __init__(self, *, available_options, timeout: int = 120):
            super().__init__(timeout=timeout)
            self.value: Optional[bool] = None  
            self.selected_values: list[str] = []

            select = discord.ui.Select(
                placeholder="Select permissions to remove…",
                min_values=1,
                max_values=len(available_options),
                options=[discord.SelectOption(label=label, value=value) for label, value in available_options],
            )

            async def on_select(interaction: discord.Interaction):
                self.selected_values = select.values
                await interaction.response.defer()

            select.callback = on_select  
            self.add_item(select)

        @discord.ui.button(label="Confirm", style=discord.ButtonStyle.success)
        async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
            if not self.selected_values:
                await interaction.response.send_message(
                    "Please select at least one permission.", ephemeral=True
                )
                return
            self.value = True
            try:
                await interaction.response.edit_message(content="Permissions selected", view=None)
            except discord.InteractionResponded:
                await interaction.edit_original_response(content="Permissions selected", view=None)
            self.stop()

        @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
        async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.value = False
            try:
                await interaction.response.edit_message(content="Selection cancelled.", view=None)
            except discord.InteractionResponded:
                await interaction.edit_original_response(content="Selection cancelled.", view=None)
            self.stop()

    # ---------- slash command ----------
    @app_commands.command(name="remove-team-permission", description="Remove permissions from a team member")
    async def remove_team_permission(
        self,
        interaction: discord.Interaction,
        team: discord.Role,
        user: discord.Member,
    ):
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        if guild is None:
            return await interaction.followup.send(
                "This command can only be used in a server.",
                ephemeral=True
            )

        config = load_config()
        gconf = self._get_guild_config(config, guild.id)
        teams = gconf.get("teams", {})
        team_id_str = str(team.id)

        if team_id_str not in teams:
            return await interaction.followup.send(
                f"{team.mention} is not registered.",
                ephemeral=True
            )

        team_data = teams[team_id_str]

        if not self._author_is_captain_or_vize(team_data, interaction.user.id):
            return await interaction.followup.send(
                "You must be the Captain or have **vize-captain** permission in this team.",
                ephemeral=True
            )

        found = self._find_member_entry(team_data, user.id)
        if not found:
            return await interaction.followup.send(
                f"{user.mention} is not in this team (neither Starter, Sub, nor Member).",
                ephemeral=True
            )

        rank_key, member_obj = found

        permissions = member_obj.get("permissions", {})
        if not permissions:
            return await interaction.followup.send(
                f"{user.mention} has no permissions to remove.",
                ephemeral=True
            )

        # Show the permission selection view
        view = self.PermissionSelectView(available_options=PERMISSION_OPTIONS)
        await interaction.followup.send(
            f"Select permissions to remove from {user.mention} in **{team.name}**:",
            view=view,
            ephemeral=True,
        )

        timeout = await view.wait()
        if timeout or view.value is False:
            return

        selected = view.selected_values

        # Remove selected permissions
        for perm in selected:
            if perm in permissions:
                del permissions[perm]
                # Remove corresponding role if necessary
                if perm == "vize-captain":
                    vize_captain_role = discord.utils.get(guild.roles, name="[OLY] Vice Captain")
                    if vize_captain_role:
                        await user.remove_roles(vize_captain_role)

        # Update team data
        teams[team_id_str]["member"][rank_key][str(user.id)] = member_obj
        gconf["teams"] = teams
        config["server"][str(guild.id)] = gconf
        save_config(config)

        # Log channel ID
        log_channel_id = 1403886456300245012 
        channel = guild.get_channel(log_channel_id)
        if channel:
            embed = discord.Embed(
                title="Team Permission Removed",
                description=f"Permissions have been removed from {user.mention} in **{team.name}**.",
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Removed by", value=interaction.user.mention, inline=True)
            embed.add_field(name="Permissions removed", value=", ".join(selected), inline=True)
            embed.set_thumbnail(url=user.display_avatar.url)
            await channel.send(embed=embed)

        # Confirmation message
        pretty = ", ".join(selected)
        await interaction.followup.send(
            f"Removed permissions: **{pretty}** from {user.mention} in **{team.name}**.",
            ephemeral=True,
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(remove_team_permission(bot))
