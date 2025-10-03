import json
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from utils import load_config, save_config

class ConfirmationView(discord.ui.View):
    def __init__(self, guild, interaction, team, user, starter_amount, sub_amount, config):
        super().__init__(timeout=86400)
        self.guild = guild
        self.interaction = interaction
        self.team = team
        self.user = user
        self.starter_amount = starter_amount
        self.sub_amount = sub_amount
        self.config = config

    async def disable_all_buttons(self, interaction):
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        await interaction.message.edit(view=self)

    @staticmethod
    async def send_registration_log(interaction, team, user, starter_amount, sub_amount, config):
        log_channel_id = config["server"][str(interaction.guild.id)]["setup"]["transactions_channel"]
        
        guild = interaction.guild
        # ensure channel id is int
        channel = interaction.guild.get_channel(int(log_channel_id))
        if not channel:
            return

        members = config["server"][str(guild.id)]["teams"][str(team.id)]["member"]
        starter_amount = len(members.get("starters", {}))
        sub_amount = len(members.get("subs", {}))
        roster_count = starter_amount + sub_amount

        embed = discord.Embed(
            title=f"{team.name} Transaction",
            description=f"{team.mention} have **signed** {user.mention}.",
            color=discord.Color.green(),
            timestamp=datetime.now(ZoneInfo("Europe/Berlin"))
        )
        embed.set_author(
            name=guild.name,
            icon_url=guild.icon.url if guild.icon else discord.Embed.Empty
        )
        embed.add_field(name="Added by", value=interaction.user.mention, inline=True)
        embed.add_field(name="Roster", value=f"{roster_count}/10", inline=True)
        embed.set_thumbnail(url=user.display_avatar.url)

        await channel.send(embed=embed)

    @staticmethod
    async def send_leave_log(interaction, team, user, config):
        log_channel_id = config["server"][str(interaction.guild.id)]["setup"]["transactions_channel"]
        guild = interaction.guild
        # ensure channel id is int
        channel = guild.get_channel(log_channel_id)
        if not channel:
            return

        members = config["server"][str(guild.id)]["teams"][str(team.id)]["member"]
        starter_amount = len(members.get("starters", {}))
        sub_amount = len(members.get("subs", {}))
        roster_count = starter_amount + sub_amount

        embed = discord.Embed(
            title=f"{team.name} Transaction",
            description=f"{user.mention} has **left** {team.mention}.",
            color=discord.Color.red(),
            timestamp=datetime.now(ZoneInfo("Europe/Berlin"))
        )
        embed.set_author(
            name=guild.name,
            icon_url=guild.icon.url if guild.icon else discord.Embed.Empty
        )
        embed.add_field(name="Roster", value=f"{roster_count}/10", inline=True)
        embed.set_thumbnail(url=user.display_avatar.url)

        await channel.send(embed=embed)
        @discord.ui.button(label="I have been Force signed", style=discord.ButtonStyle.red)
        async def force_signed(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user.id != self.user.id:
                await interaction.followup.send("You're not allowed to respond to this request.", ephemeral=True)
                return

            await interaction.response.defer(ephemeral=True)

            # Disable the button clicked by the user (to prevent multiple presses)
            button.disabled = True
            await interaction.message.edit(view=self)

            guild = self.guild
            guild_id = str(guild.id)
            team = self.team
            user = self.user
            user_id = str(user.id)

            config = load_config()
            team_data = config.get("server", {}).get(guild_id, {}).get("teams", {}).get(str(team.id))

            if not team_data:
                await interaction.followup.send("Team not found.", ephemeral=True)
                return

            members = team_data.get("member", {})
            removed = False
            # Remove the user from the team (starters, subs, member)
            for bucket in ("starters", "subs", "member"):
                bucket_map = members.get(bucket, {})
                if user_id in bucket_map:
                    del bucket_map[user_id]
                    removed = True
                    break

            if not removed:
                await interaction.followup.send("You are not a member of this team.", ephemeral=True)
                return

            # Clear existing cooldown if present
            try:
                jc = config["server"][guild_id]["join_cooldowns"].get(user_id, {})
                jc.pop("joined_cooldown", None)
                if not jc:
                    del config["server"][guild_id]["join_cooldowns"][user_id]
            except KeyError:
                pass

            save_config(config)

            # Remove the team role from the user
            try:
                member_obj = await guild.fetch_member(user.id)
                await member_obj.remove_roles(team, reason="Force signed: user left team")
            except discord.Forbidden:
                await interaction.followup.send("I can't remove that role. Check Manage Roles and role hierarchy.", ephemeral=True)
                return
            except discord.HTTPException as e:
                await interaction.followup.send("Failed to remove the role (HTTP error).", ephemeral=True)
                print(f"Role removal error: {e}")
                return

            # Log the leave action (make sure we use int channel id)
            log_channel_id = config["server"][guild_id]["setup"].get("transactions_channel")
            if log_channel_id:
                channel = guild.get_channel(int(log_channel_id))
                if channel:
                    embed = discord.Embed(
                        title=f"{team.name} Transaction",
                        description=f"{user.mention} has **left** {team.mention}.",
                        color=discord.Color.red(),
                        timestamp=datetime.now(ZoneInfo("Europe/Berlin"))
                    )
                    embed.set_author(name=guild.name, icon_url=guild.icon.url if guild.icon else discord.Embed.Empty)
                    embed.set_thumbnail(url=user.display_avatar.url)
                    try:
                        await channel.send(embed=embed)
                    except discord.Forbidden:
                        await interaction.followup.send("I can’t send embeds in the transactions channel (missing permission).", ephemeral=True)
                else:
                    await interaction.followup.send("Transactions channel not found. Check the channel ID in config.", ephemeral=True)
            else:
                await interaction.followup.send("Transactions channel not set in config.", ephemeral=True)

            await interaction.followup.send(f"You left {team.mention}.", ephemeral=True)
            self.stop()

class add_member(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def validation_check(self, interaction, team, user, config, guild_id, position, starter_amount, sub_amount, rank, has_team_permission):
        config_team = config["server"][guild_id]["teams"]

        if str(team.id) not in config_team:
            await interaction.followup.send(f"{team.mention} is not registered.", ephemeral=True)
            return False

        config_member = config_team[str(team.id)]["member"]

        member = []
        in_team = False
        has_permission = False

        ws_amount = 0
        ds_amount = 0
        setter_amount = 0
        lib_amount = 0
        
        transactions_channel_id = config["server"][guild_id]["setup"].get("transactions_channel", None)
        if transactions_channel_id is None:
            await interaction.followup.send("Transactions channel is not set up.", ephemeral=True)
            return False  # ensure the validator aborts

        # --- count starters & positions (safe access) ---
        for uid, data in (config_member.get("starters") or {}).items():
            starter_amount += 1
            member.append(uid)

            pos = (data or {}).get("position")
            if pos == "wing-spiker":
                ws_amount += 1
            if pos == "defensive-specialist":
                ds_amount += 1
            if pos == "libero":
                lib_amount += 1
            if pos == "setter":
                setter_amount += 1

        # --- PERMISSION CHECK ---
        invoker_id = str(interaction.user.id)
        team_key = str(team.id)
        team_block = config_team[team_key]

        if has_team_permission:
            has_permission = True
        else:
            # Captain always allowed
            if str(team_block.get("captain")) == invoker_id:
                has_permission = True
            else:
                # Check explicit per-user permissions across buckets
                has_permission = False
                member_block = team_block.get("member", {}) or {}
                for bucket in ("starters", "subs", "member"):
                    user_entry = (member_block.get(bucket, {}) or {}).get(invoker_id)
                    if not isinstance(user_entry, dict):
                        continue
                    perms = user_entry.get("permissions", {}) or {}
                    # accept both vice/vize captain spellings
                    vc = bool(perms.get("vize-captain"))
                    if bool(perms.get("add-member")) or vc:
                        has_permission = True
                        break

        # in-team check (safe dict access)
        for t_id, t in config_team.items():
            mblk = (t.get("member") or {})
            if str(user.id) in (mblk.get("starters") or {}):
                in_team = (t_id != str(team.id))
                if in_team:
                    break

        for uid in (config_member.get("subs") or {}).keys():
            sub_amount += 1
            member.append(uid)

        for uid in (config_member.get("member") or {}).keys():
            member.append(uid)

        if not in_team:
            for t_id, t in config_team.items():
                mblk = (t.get("member") or {})
                if str(user.id) in (mblk.get("subs") or {}):
                    in_team = (t_id != str(team.id))
                    if in_team:
                        break

        if not has_permission:
            await interaction.followup.send(
                f"You have no permission adding member to {team.mention}",
                ephemeral=True
            )
            return False

        if str(user.id) in member:
            await interaction.followup.send(f"{user.mention} is already part of the Team", ephemeral=True)
            return False

        if rank.value == "member" and position.value != "member":
            await interaction.followup.send(f"Please Select Member Position when you select Member as Rank", ephemeral=True)
            return False

        if position.value == "member" and rank.value != "member":
            await interaction.followup.send(f"Please select Member Rank when you select Member as Position", ephemeral=True)
            return False

        if rank.value == "starters" and starter_amount >= 6:
            await interaction.followup.send(f"{team.mention} already has 6 Starters.", ephemeral=True)
            return False

        if rank.value == "subs" and sub_amount >= 4:
            await interaction.followup.send(f"{team.mention} already has 4 Subs.", ephemeral=True)
            return False

        if rank.value == "starters":
            if position.value == "wing-spiker" and ws_amount == 2:
                await interaction.followup.send(
                    f"{team.mention} already has 2 Wing-Spiker in the Starting 6.", ephemeral=True
                )
                return False
            if position.value == "defensive-specialist" and ds_amount == 2:
                await interaction.followup.send(
                    f"{team.mention} already has 2 Defensive-Specialists in the Starting 6.", ephemeral=True
                )
                return False
            if position.value == "libero" and lib_amount == 1:
                await interaction.followup.send(
                    f"{team.mention} already has a Libero in the Starting 6.", ephemeral=True
                )
                return False
            if position.value == "setter" and setter_amount == 1:
                await interaction.followup.send(
                    f"{team.mention} already has a Setter in the Starting 6.", ephemeral=True
                )
                return False

        if rank.value != "member":
            if in_team:
                await interaction.followup.send(f"{user.mention} is already in a Team.", ephemeral=True)
                return False

        return True


    @app_commands.choices(
        position=[
            app_commands.Choice(name="Wing Spiker", value="wing-spiker"),
            app_commands.Choice(name="Setter", value="setter"),
            app_commands.Choice(name="Libero", value="libero"),
            app_commands.Choice(name="Defensive Specialist", value="defensive-specialist"),
            app_commands.Choice(name="Member", value="member")
        ],
        rank=[
            app_commands.Choice(name="Starter", value="starters"),
            app_commands.Choice(name="Sub", value="subs"),
            app_commands.Choice(name="Member", value="member")
        ]
    )
    @app_commands.command(name="add_member", description="Add a Member to a Team")
    async def add_member(
        self,
        interaction: discord.Interaction,
        team: discord.Role,
        user: discord.Member,
        position: app_commands.Choice[str],
        rank: app_commands.Choice[str]
    ):
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        guild_id = str(guild.id)
        config = load_config()
        has_team_permission = any(role.name == "[OLY] Team Perms" for role in interaction.user.roles)

        starter_amount = 0
        sub_amount = 0

        valid_request = await add_member.validation_check(
            self, interaction, team, user, config, guild_id, position, starter_amount, sub_amount, rank, has_team_permission
        )

        if valid_request:

            if not has_team_permission:

                if rank.value != "member":
                    tz = ZoneInfo("Europe/Berlin")
                    cooldowns = config["server"][guild_id].setdefault("join_cooldowns", {})
                    user_cd = cooldowns.setdefault(str(user.id), {})
                    cooldown_list = user_cd.setdefault("joined_cooldown", [])

                    now = datetime.now(tz)
                    cooldown_end = None
                    if cooldown_list:
                        try:
                            cd = datetime.fromisoformat(cooldown_list[0])
                            if cd.tzinfo is None:
                                cd = cd.replace(tzinfo=tz)
                            cooldown_end = cd
                        except Exception:
                            cooldown_end = None

                    if cooldown_end and now < cooldown_end:
                        await interaction.followup.send(
                            f"{user.mention} is on cooldown until **{cooldown_end.strftime('%Y-%m-%d %H:%M:%S %Z')}**.",
                            ephemeral=True
                        )
                        return

                config["server"][guild_id]["teams"][str(team.id)]["member"][rank.value][str(user.id)] = {
                    "position": position.value, "rank": rank.value, "permissions": {}
                }

                save_config(config)

                if rank.value != "member":
                    cooldown_end = datetime.now(tz) + timedelta(days=3)
                    config["server"][guild_id].setdefault("join_cooldowns", {}).setdefault(
                        str(user.id), {}
                    )["joined_cooldown"] = [cooldown_end.isoformat()]

                save_config(config)

                if rank.value != "member":
                    member = await guild.fetch_member(user.id)
                    try:
                        await member.add_roles(team, reason="Team add")
                    except discord.Forbidden:
                        await interaction.followup.send(
                            "I can't add that role. Check Manage Roles and role hierarchy.",
                            ephemeral=True
                        )
                        return
                    except discord.HTTPException as e:
                        await interaction.followup.send("Couldn't assign the role (HTTP error).", ephemeral=True)
                        print(e)
                        return

                try:
                    view = ConfirmationView(guild, interaction, team, user, starter_amount, sub_amount, config)
                    await user.send(
                        f"You have been signed to **{team.name}** as a **{position.name}**.\n"
                        f"You have 24h to mark as force signed. If you miss the time please contact a Staff member.",
                        view=view
                    )
                    await interaction.followup.send(f"{user.mention} has been added to {team.mention}", ephemeral=True)
                except discord.Forbidden:
                    pass

                await ConfirmationView.send_registration_log(interaction, team, user, starter_amount, sub_amount, config)

            else:
                config["server"][guild_id]["teams"][str(team.id)]["member"][rank.value][str(user.id)] = {
                    "position": position.value, "rank": rank.value, "permissions": {}
                }
                save_config(config)

                if rank.value != "member":
                    member = await guild.fetch_member(user.id)
                    try:
                        await member.add_roles(team, reason="Team add")
                    except discord.Forbidden:
                        await interaction.followup.send(
                            "I can't add that role. Check Manage Roles and role hierarchy.",
                            ephemeral=True
                        )
                        return
                    except discord.HTTPException as e:
                        await interaction.followup.send("Couldn't assign the role (HTTP error).", ephemeral=True)
                        print(e)
                        return

                try:
                    view = ConfirmationView(guild, interaction, team, user, starter_amount, sub_amount, config)
                    await user.send(
                        f"You have been signed to **{team.name}** as a **{position.name}**.\n"
                        f"You have 24h to mark as force signed. If you miss the time please contact a Staff member.",
                        view=view
                    )
                    await interaction.followup.send(f"{user.mention} has been added to {team.mention}", ephemeral=True)
                except discord.Forbidden:
                    pass

                await ConfirmationView.send_registration_log(interaction, team, user, starter_amount, sub_amount, config)

async def setup(bot: commands.Bot):
    await bot.add_cog(add_member(bot))
