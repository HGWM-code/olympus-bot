import discord
from discord.ext import commands
from discord import app_commands
from utils import load_config

class ListMember(commands.Cog):
    def __init__(self, bot: commands.Bot, config: dict):
        self.bot = bot
        self.config = config

    def mention_or_id(self, guild: discord.Guild, uid: str) -> str:
        if not uid:
            return "-"
        member = guild.get_member(int(uid))
        return member.mention if member else f"<@{uid}>"

    def format_members(self, guild, member_dict):
        if not member_dict:
            return "None"
        lines = []
        for mid, data in member_dict.items():
            position = data.get("position", "Unknown")
            lines.append(f"{self.mention_or_id(guild, mid)} - {position}")
        return "\n".join(lines)

    @app_commands.command(name="list-member", description="Show the starters, subs, and members of a team")
    @app_commands.describe(team="The team role")
    async def list_member(self, interaction: discord.Interaction, team: discord.Role):
        config = load_config()
        guildID = str(interaction.guild.id)
        teamID = str(team.id)
        team_data = config["server"].get(guildID, {}).get("teams", {}).get(teamID, {})

        embed = discord.Embed(
            title=f"Team: {team.name}",
            color=team.color if hasattr(team, "color") else discord.Color.yellow()
        )

        captain_id = team_data.get("captain")
        captain = self.mention_or_id(interaction.guild, captain_id) if captain_id else "Unknown"
        embed.add_field(name="Captain", value=captain, inline=False)

        starters = team_data.get("member", {}).get("starters", {})
        subs = team_data.get("member", {}).get("subs", {})
        members = team_data.get("member", {}).get("member", {})

        embed.add_field(
            name="Starters",
            value=self.format_members(interaction.guild, starters),
            inline=False
        )
        embed.add_field(
            name="Subs",
            value=self.format_members(interaction.guild, subs),
            inline=False
        )
        embed.add_field(
            name="Members",
            value=self.format_members(interaction.guild, members),
            inline=False
        )

        if not starters and not subs and not members:
            embed.clear_fields()
            embed.add_field(name="Captain", value=captain, inline=False)
            embed.add_field(name="Members", value="No members.", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    from utils import load_config
    await bot.add_cog(ListMember(bot, load_config()))
