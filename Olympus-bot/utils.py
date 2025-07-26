import json
import discord
from collections import OrderedDict
from discord.ui import View, Button
import math

CONFIG_PATH = "config.json"
TEAMS_PER_PAGE = 7 

def load_config():
    try:
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"server": {}}

def save_config(data):
    with open(CONFIG_PATH, "w") as f:
        json.dump(data, f, indent=4)

class LeaderboardView(View):
    def __init__(self, pages):
        super().__init__(timeout=None)
        self.pages = pages
        self.current_page = 0
        self.message = None

        self.prev_button = Button(label="Previous", style=discord.ButtonStyle.primary)
        self.next_button = Button(label="Next", style=discord.ButtonStyle.primary)

        self.prev_button.callback = self.prev_page
        self.next_button.callback = self.next_page

        self.add_item(self.prev_button)
        self.add_item(self.next_button)

    async def send(self, channel):
        self.message = await channel.send(embed=self.pages[0], view=self)
        await self.update_buttons()

    async def update_buttons(self):
        self.prev_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page == len(self.pages) - 1
        await self.message.edit(embed=self.pages[self.current_page], view=self)

    async def prev_page(self, interaction: discord.Interaction):
        if self.current_page > 0:
            self.current_page -= 1
            await self.update_buttons()
        await interaction.response.defer()

    async def next_page(self, interaction: discord.Interaction):
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            await self.update_buttons()
        await interaction.response.defer()

async def update_leaderboard(interaction: discord.Interaction):
    config = load_config()
    server_id = str(interaction.guild.id)

    if server_id not in config["server"]:
        await interaction.followup.send("Server data not found.", ephemeral=True)
        return

    leaderboard = config["server"][server_id].get("leaderboard", {})
    teams = config["server"][server_id].get("teams", {})

    sorted_leaderboard = OrderedDict(
        sorted(
            leaderboard.items(),
            key=lambda item: item[1]["elo"],
            reverse=True
        )
    )

    config["server"][server_id]["leaderboard"] = dict(sorted_leaderboard)
    save_config(config)

    entries = list(sorted_leaderboard.items())
    medals = [":first_place:", ":second_place:", ":third_place:", ":military_medal:", ":military_medal:"]

    ranked_teams = []
    for team_id, team_data in entries:
        role = interaction.guild.get_role(int(team_id))
        if not role:
            continue
        team_info = teams.get(str(role.id))
        if not team_info:
            continue
        ranked_teams.append((role, team_data, team_info))

    total_pages = math.ceil(len(ranked_teams) / TEAMS_PER_PAGE)
    pages = []

    for page_num in range(total_pages):
        embed = discord.Embed(
            title=f"Leaderboard (Page {page_num + 1}/{total_pages})",
            description="Current team rankings by ELO",
            color=discord.Color.gold()
        )

        start = page_num * TEAMS_PER_PAGE
        end = start + TEAMS_PER_PAGE

        for i, (role, team_data, team_info) in enumerate(ranked_teams[start:end], start=start + 1):
            record_wins = team_info.get("record_wins", 0)
            record_loses = team_info.get("record_loses", 0)
            medal = medals[i - 1] if i <= len(medals) else f"{i}."

            embed.add_field(
                name="\u200b",
                value=f"{medal} {role.mention}\nELO: {int(team_data['elo'])}\nRecord: Wins: {record_wins} - Losses: {record_loses}",
                inline=False
            )

        pages.append(embed)

    leaderboard_channel = interaction.guild.get_channel(1353503349768716318)
    if leaderboard_channel is None:
        await interaction.followup.send("Leaderboard channel not found.", ephemeral=True)
        return

    try:
        await leaderboard_channel.purge(limit=30)
        view = LeaderboardView(pages)
        await view.send(leaderboard_channel)
    except discord.Forbidden:
        await interaction.followup.send("Missing permissions to manage messages in the leaderboard channel.", ephemeral=True)
        return
    except discord.HTTPException as e:
        await interaction.followup.send(f"An error occurred while sending the leaderboard: {e}", ephemeral=True)
        return

    await interaction.followup.send("Leaderboard has been updated.", ephemeral=True)
