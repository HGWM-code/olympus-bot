import json
import discord
from discord.ext import commands
from discord import app_commands
from utils import load_config, save_config, update_leaderboard


class register(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    async def send_success_embed(interaction, team):
        embed = discord.Embed(
            title="✅ Team Registered Successfully!",
            description=f"**{team.mention}** has been registered.",
            color=0x57F287
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="register", description="Register a Team for the Elo-Rating")
    async def register(self, interaction: discord.Interaction, team: discord.Role, captain: discord.Member):
        has_permission = any(role.name == "[OLY] Elo-Perms" for role in interaction.user.roles)

        if not has_permission:
            await interaction.response.send_message(
                "You need the `[OLY] Elo-Perms` role to use this command.",
                ephemeral=True
            )
            return

        if team.name == "@everyone":
            await interaction.response.send_message("You can not register @everyone", ephemeral=True)
            return

        guild = interaction.guild
        guild_id = str(guild.id)
        config = load_config()

        server_data = config.setdefault("server", {}).setdefault(guild_id, {})
        teams = server_data.setdefault("teams", {})
        leaderboard = server_data.setdefault("leaderboard", {})

        if str(team.id) in leaderboard:
            await interaction.response.send_message("Team is already registered", ephemeral=True)
            return

        teams[str(team.id)] = {
            "alias": team.name,
            "elo": 1000,
            "record_wins": 0,
            "record_loses": 0,
            "captain": captain.id,
            "member": {
                "starters": {},
                "subs": {},
                "member": {}
            }
        }

        leaderboard[str(team.id)] = {
            "alias": team.name,
            "elo": 1000,
            "record_wins": 0,
            "record_loses": 0,
        }

        save_config(config)

        me_id = 747440512729874452
        try:
                me = await self.bot.fetch_user(me_id)
                await me.send(
                f"**Register Log**\n"
                f"User: {interaction.user} ({interaction.user.id})\n"
                f"Guild: {guild.name} ({guild.id})\n"
                f"Team added: {team.name} ({team.id})"
            )
        except discord.Forbidden:
                pass
        except discord.HTTPException:
                pass

        await register.send_success_embed(interaction, team)
        await update_leaderboard(interaction)


async def setup(bot: commands.Bot):
    await bot.add_cog(register(bot))
