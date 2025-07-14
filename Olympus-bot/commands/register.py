import json
import discord
from discord.ext import commands
from discord import app_commands
from utils import load_config
from utils import save_config
from utils import update_leaderboard


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
        await interaction.channel.send(embed=embed)
        await interaction.response.send_message("Team registered", ephemeral=True)

    @app_commands.command(name="register", description="Register a Team for the Elo-Rating")
    async def register(self, interaction: discord.Interaction, team: discord.Role):
        has_permission = any(role.name == "elo-perms" for role in interaction.user.roles)

        if not has_permission:
            await interaction.response.send_message(
                "You need the `elo-perms` role to use this command.",
                ephemeral=True
            )
            return 

        if team.name == "@everyone":
            await interaction.response.send_message("You can not register @everyone", ephemeral=True)

        else:

            guild = interaction.user.guild
            guild_id = guild.id
            config = load_config()

            leaderboard = config["server"][str(guild_id)]["leaderboard"]

            if team not in leaderboard:
                config["server"][str(guild_id)]["teams"][team.id] = {"alias": team.name, "elo": 1000, "record_wins": 0, "record_loses": 0}
                config["server"][str(guild_id)]["leaderboard"][team.id] = {"alias": team.name, "elo": 1000, "record_wins": 0, "record_loses": 0}

                save_config(config)
            
                await register.send_success_embed(interaction, team)
                await update_leaderboard(interaction)
            else:
                await interaction.response.send_message("The Team you are trying to register is already registered.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(register(bot))
