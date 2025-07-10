import json
import discord
from collections import OrderedDict

CONFIG_PATH = "config.json"

def load_config():
    try:
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"server": {}}

def save_config(data):
    with open(CONFIG_PATH, "w") as f:
        json.dump(data, f, indent=4)

async def update_leaderboard(interaction):
    config = load_config()
    server_id = str(interaction.guild.id)

    leaderboard = config["server"][server_id]["leaderboard"]

    sortedLeaderboard = OrderedDict(
        sorted(
            leaderboard.items(),
            key=lambda item: item[1]["elo"],
            reverse=True
        )
    )

    config["server"][server_id]["leaderboard"] = dict(sortedLeaderboard)

    save_config(config)

    embed = discord.Embed(
        title="🏆 Leaderboard",
        description="Current team rankings by ELO",
        color=discord.Color.gold()
    )
    medals = ["🥇", "🥈", "🥉", "🏅", "🏅"]

    for i, (team_id, team_data) in enumerate(sortedLeaderboard.items(), start=1):
        role = interaction.guild.get_role(int(team_id))
        record_wins = config["server"][server_id]["teams"][str(role.id)]["record_wins"]
        record_loses = config["server"][server_id]["teams"][str(role.id)]["record_loses"]
        if role:
            medal = medals[i-1] if i <= 5 else f"**{i}.)**"
            embed.add_field(
                name="‎",
                value=f"{medal} {role.mention}\nELO: **{int(team_data['elo'])}**\n Record: **Wins: {record_wins}** - **Losses: {record_loses}**",
                inline=False
            )

    leaderboardChannel = interaction.guild.get_channel(1353503349768716318)

    await leaderboardChannel.purge(limit=30)
    await leaderboardChannel.send(embed=embed)

    await interaction.response.send_message("Leaderboard has been updated.", ephemeral=True)
