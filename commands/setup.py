import json
import discord
from discord.ext import commands
from discord import app_commands
from utils import load_config
from utils import save_config


class setup_server(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setup", description="Setup the bot")
    async def setup_server(self, interaction: discord.Interaction, leaderboard_channel: discord.TextChannel, elo_update_channel: discord.TextChannel, elo_matches_category: discord.CategoryChannel, transactions_channel: discord.TextChannel, log_channel: discord.TextChannel):
      has_permission = any(role.name == "[OLY] Setup" for role in interaction.user.roles)

      if not has_permission:
         await interaction.response.send_message(
                "You need the `[OLY] Setup` role to use this command.",
                ephemeral=True
            )
         return 

      guild = interaction.user.guild
      guild_id = guild.id
      config = load_config()

      config["server"][str(guild_id)]["setup"]["leaderboard_channel"] = leaderboard_channel.id
      config["server"][str(guild_id)]["setup"]["elo_update_channel"] = elo_update_channel.id
      config["server"][str(guild_id)]["setup"]["elo_matches_category"] = elo_matches_category.id
      config["server"][str(guild_id)]["setup"]["transactions_channel"] = transactions_channel.id
      config["server"][str(guild_id)]["setup"]["log_channel"] = log_channel.id
      save_config(config)

      await interaction.response.send_message(
            "Setup completed successfully!",
            ephemeral=True
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(setup_server(bot))
