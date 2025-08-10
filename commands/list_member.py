import discord
from discord.ext import commands
from discord import app_commands
from typing import Union

def mention_or_id(guild: discord.Guild, uid: Union[str, None]) -> str:
    if not uid:
        return "—"
    m = guild.get_member(int(uid))
    return m.mention if m else f"<@{uid}>"

def pick_by_position(starters: dict, pos: str, taken: set[str]) -> Union[str, None]:
    for uid, data in starters.items():
        if uid in taken:
            continue
        if str(data.get("position", "")).lower() == pos:
            taken.add(uid)
            return uid
    return None

def label(pos: Union[str, None]) -> str:
    return {
        "wing-spiker": "Wing-Spiker",
        "setter": "Setter",
        "defensive-specialist": "Defensive Specialist",
        "libero": "Libero",
    }.get((pos or "").lower(), "Member")

def chunk_pairs(lines: list[str]) -> tuple[str, str]:
    left, right = [], []
    for i, line in enumerate(lines):
        (left if i % 2 == 0 else right).append(line)
    return "\n".join(left) or "—", "\n".join(right) or "—"

class list_member(commands.Cog):
    def __init__(self, bot: commands.Bot, config: dict):
        self.bot = bot
        self.config = config

    @app_commands.command(name="list-member", description="Show team members of a team")
    @app_commands.describe(team="Team role")
    async def list_member(self, interaction: discord.Interaction, team: discord.Role):
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        guild_id = str(guild.id)
        team_id = str(team.id)

        server = self.config.get("server", {}).get(guild_id, {})
        team_data = server.get("teams", {}).get(team_id)
        if not team_data:
            await interaction.followup.send("Team not found.", ephemeral=True)
            return

        alias = team_data.get("alias", team.name)
        captain_id = str(team_data.get("captain")) if team_data.get("captain") else None

        buckets = team_data.get("member", {}) or {}
        starters = buckets.get("starters", {}) or {}
        subs = buckets.get("subs", {}) or {}
        others = buckets.get("member", {}) or {}

        # Check if the team is empty
        if not starters and not subs and not others:
            await interaction.followup.send(f"The team **{alias}** is empty.", ephemeral=True)
            return

        # Define the positions we want to display (wing-spiker, setter, etc.)
        desired = [
            ["wing-spiker", "setter", "wing-spiker"],
            ["defensive-specialist", "libero", "defensive-specialist"],
        ]

        used: set[str] = set()
        picked = []
        for row in desired:
            picked_row = []
            for pos in row:
                # First try to pick from the starters
                uid = pick_by_position(starters, pos, used)
                if not uid:
                    # If no starter found, try subs
                    uid = pick_by_position(subs, pos, used)
                picked_row.append((pos, uid))
            picked.append(picked_row)

        subs_lines = [
            f"{mention_or_id(guild, uid)} — {label(d.get('position'))}"
            for uid, d in subs.items()
        ]
        subs_left, subs_right = chunk_pairs(subs_lines)

        members_lines = [mention_or_id(guild, uid) for uid in others.keys()]

        color = team.color if isinstance(team.color, discord.Color) else discord.Color.blurple()
        embed = discord.Embed(title=f"{alias} Members", color=color)
        embed.add_field(name="Captain", value=mention_or_id(guild, captain_id), inline=False)

        embed.add_field(name="Starters:", value="", inline=False)
        for pos, uid in picked[0]:
            embed.add_field(name=label(pos), value=mention_or_id(guild, uid), inline=True)
        for pos, uid in picked[1]:
            embed.add_field(name=label(pos), value=mention_or_id(guild, uid), inline=True)

        embed.add_field(name="Subs:", value=subs_left, inline=True)
        embed.add_field(name="\u200b", value=subs_right, inline=True)

        if members_lines:
            embed.add_field(name="Members:", value="\n".join(members_lines), inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    from utils import load_config
    await bot.add_cog(list_member(bot, load_config()))
