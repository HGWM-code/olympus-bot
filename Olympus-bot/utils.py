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
        super().__init__(timeout=120)
        self.pages = pages
        self.current_page = 0
        self.message = None

        self.prev_button = Button(label="◀️ Zurück", style=discord.ButtonStyle.primary)
        self.next_button = Button(label="Weiter ▶️", style=discord.ButtonStyle.primary)

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

    medals = ["🥇", "🥈", "🥉", "🏅", "🏅"]
    entries = list(sortedLeaderboard.items())
    total_pages = math.ceil(len(entries) / TEAMS_PER_PAGE)
    pages = []

    for page_num in range(total_pages):
        embed = discord.Embed(
            title=f"🏆 Leaderboard (Seite {page_num+1}/{total_pages})",
            description="Aktuelle Team-Rangliste nach ELO",
            color=discord.Color.gold()
        )

        for i in range(TEAMS_PER_PAGE):
            index = page_num * TEAMS_PER_PAGE + i
            if index >= len(entries):
                break

            team_id, team_data = entries[index]
            role = interaction.guild.get_role(int(team_id))
            if not role:
                continue

            team_info = config["server"][server_id]["teams"].get(str(role.id), {})
            wins = team_info.get("record_wins", 0)
            losses = team_info.get("record_loses", 0)

            medal = medals[index] if index < len(medals) else f"**{index+1}.)**"
            embed.add_field(
                name="‎",
                value=f"{medal} {role.mention}\nELO: **{int(team_data['elo'])}**\nRecord: **Wins: {wins}** - **Losses: {losses}**",
                inline=False
            )

        pages.append(embed)

    leaderboard_channel = interaction.guild.get_channel(1353503349768716318)
    await leaderboard_channel.purge(limit=30)

    view = LeaderboardView(pages)
    await view.send(leaderboard_channel)

    await interaction.response.send_message("📊 Leaderboard wurde aktualisiert – mit Seitenansicht!", ephemeral=True)
