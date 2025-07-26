import discord
from discord.ext import commands
from discord import app_commands
from utils import load_config


class debug_update_elo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def send_results_embed(
        self, interaction, winner, looser, oldEloWinner, oldEloLooser,
        newEloWinner, newEloLooser,
        set1_team1_score, set1_team2_score, set1_winner,
        set2_team1_score, set2_team2_score, set2_winner,
        set3_team1_score, set3_team2_score, set3_winner,
        match_type, ff
    ):
        team1SetCounter = 0
        team2SetCounter = 0

        if set1_winner == winner:
            team1SetCounter += 1
        elif set1_winner == looser:
            team2SetCounter += 1

        if set2_winner == winner:
            team1SetCounter += 1
        elif set2_winner == looser:
            team2SetCounter += 1

        set3 = ""
        if set3_team1_score != 0 or set3_team2_score != 0:
            if set3_winner == winner:
                team1SetCounter += 1
            elif set3_winner == looser:
                team2SetCounter += 1
            set3 = f"\n**3. Set: {int(set3_team1_score)} - {int(set3_team2_score)} | {set3_winner.mention} **\n"

        ff_text = "(Surrender)" if ff else ""

        winner_diff = int(newEloWinner - oldEloWinner)
        looser_diff = int(oldEloLooser - newEloLooser)

        embed = discord.Embed(
            title=f"{match_type.name} - Match Result {ff_text} --DEBUGMODE--",
            description=(
                f"**{winner.mention}** vs **{looser.mention}**\n\n"
                f"**Sets: {team1SetCounter} - {team2SetCounter} **\n\n"
                f"**1. Set: {set1_team1_score} - {set1_team2_score} | {set1_winner.mention} **\n"
                f"**2. Set: {set2_team1_score} - {set2_team2_score} | {set2_winner.mention} **"
                f"{set3}"
                f"\n**Winner:** {winner.mention}\n"
                f"ELO: **{int(oldEloWinner)}** -> **{int(newEloWinner)}** ({'+' if winner_diff >= 0 else ''}{winner_diff})\n\n"
                f"**Loser:** {looser.mention}\n"
                f"ELO: **{int(oldEloLooser)}** -> **{int(newEloLooser)}** ({'' if looser_diff >= 0 else ''}{-looser_diff})"
            ),
            color=discord.Color.green()
        )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="debug-update-elo", description="DEBUG: Show match result + ELO calc (no save)")
    @app_commands.choices(
        match_type=[
            app_commands.Choice(name="Elo-Match", value="elo-match"),
            app_commands.Choice(name="League-Match", value="league-match")
        ]
    )
    async def debug_update_elo(
        self, interaction: discord.Interaction, match_type: app_commands.Choice[str],
        team1: discord.Role, team2: discord.Role, winner: discord.Role,
        set1_team1_score: int, set1_team2_score: int, set1_winner: discord.Role,
        set2_team1_score: int, set2_team2_score: int, set2_winner: discord.Role,
        set3_team1_score: int, set3_team2_score: int, set3_winner: discord.Role
    ):

        await interaction.response.defer(ephemeral=True)
        config = load_config()
        guild_id = str(interaction.guild.id)
        teams = config["server"][guild_id]["teams"]
        leaderboard = config["server"][guild_id]["leaderboard"]

        if any(team.name == "@everyone" for team in [team1, team2, winner]):
            await interaction.followup.send("You cannot use @everyone.", ephemeral=True)
            return
        if winner not in [team1, team2]:
            await interaction.followup.send("The winner must be one of the selected teams.", ephemeral=True)
            return
        if str(team1.id) not in teams or str(team2.id) not in teams:
            await interaction.followup.send("One or both teams are not registered.", ephemeral=True)
            return

        looser = team2 if winner == team1 else team1
        winner_id = str(winner.id)
        looser_id = str(looser.id)

        baseElo = 10
        loosingElo = 10
        eloBonus = 0

        sorted_leaderboard = sorted(leaderboard.items(), key=lambda x: x[1]["elo"], reverse=True)
        top5_ids = [team_id for team_id, _ in sorted_leaderboard[:7]]
        bonus_map = {0: 60, 1: 50, 2: 40, 3: 30, 4: 20, 5: 10, 6: 5}

        winner_bonus = bonus_map[top5_ids.index(winner_id)] if winner_id in top5_ids else 0
        looser_bonus = bonus_map[top5_ids.index(looser_id)] if looser_id in top5_ids else 0
        eloBonus = max(winner_bonus, looser_bonus)

        sorted_ids = list(leaderboard.keys())
        index1 = sorted_ids.index(str(team1.id))
        index2 = sorted_ids.index(str(team2.id))
        multiplicator = abs(index1 - index2)

        if index1 < index2:
            higherPos = team1
            lowerPos = team2
        else:
            higherPos = team2
            lowerPos = team1

        elo1 = leaderboard[str(team1.id)]["elo"]
        elo2 = leaderboard[str(team2.id)]["elo"]
        elo_diff = abs(elo1 - elo2)

        ff = False
         # --- Surrender Check ---
        if set1_team1_score + set1_team2_score == 25 and set2_team1_score + set2_team2_score == 25:
            ff = True
            winnerElo = baseElo + 5
            loosingElo = loosingElo
        elif (winner == higherPos and multiplicator >= 2) or (winner == higherPos and elo_diff > 65):

            if multiplicator >= 6 or elo_diff > 300:
                baseElo = 5
                if multiplicator >= 9 or elo_diff > 500:
                    baseElo = 3

            eloReduce = True
            winnerElo = baseElo
            loosingElo = loosingElo * 2
        elif (winner == lowerPos and multiplicator >= 2) or (winner == lowerPos and elo_diff > 65):
            eloReduce = False
            winnerElo = baseElo * multiplicator
            loosingElo = (loosingElo * 3) + eloBonus // 2
        else:
            eloReduce = False
            pointsBonus = (
                abs(set1_team1_score - set1_team2_score) +
                abs(set2_team1_score - set2_team2_score) +
                abs(set3_team1_score - set3_team2_score) / 4
            )
            winnerElo = baseElo + 5 + pointsBonus
            loosingElo = loosingElo + 10

        # --- Apply Bonus ---
        winnerElo += (eloBonus // 4) if ff or eloReduce else eloBonus

        oldEloWinner = leaderboard[winner_id]["elo"]
        oldEloLooser = leaderboard[looser_id]["elo"]
        newEloWinner = int(oldEloWinner + winnerElo)
        newEloLooser = int(max(0, oldEloLooser - loosingElo))

        # Send result (no updates to data)
        await self.send_results_embed(
            interaction, winner, looser, oldEloWinner, oldEloLooser,
            newEloWinner, newEloLooser,
            set1_team1_score, set1_team2_score, set1_winner,
            set2_team1_score, set2_team2_score, set2_winner,
            set3_team1_score, set3_team2_score, set3_winner,
            match_type, ff
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(debug_update_elo(bot))
