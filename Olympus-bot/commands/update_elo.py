import json
import discord
from discord.ext import commands
from discord import app_commands
from utils import load_config, save_config, update_leaderboard


class update_elo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def send_results_embed(self, interaction, winner, looser, leaderboard, oldEloWinner, oldEloLooser, set1_team1_score, set1_team2_score, set1_winner, set2_team1_score, set2_team2_score, set2_winner, set3_team1_score, set3_team2_score, set3_winner, config, guild_id, match_type, ff):
        winnerElo = leaderboard[str(winner.id)]["elo"]
        looserElo = leaderboard[str(looser.id)]["elo"]

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

        if set3_team1_score == 0 and set3_team2_score == 0:
            set3 = f"\n"
        elif set3_winner == winner:
            team1SetCounter += 1
            set3 = f"\n**3. Set: {int(set3_team1_score)} - {int(set3_team2_score)} | {set3_winner.mention} **\n"

        config["server"][guild_id]["teams"][str(looser.id)]["record_loses"] += 1
        config["server"][guild_id]["leaderboard"][str(looser.id)]["record_loses"] += 1

        config["server"][guild_id]["teams"][str(winner.id)]["record_wins"] += 1
        config["server"][guild_id]["leaderboard"][str(winner.id)]["record_wins"] += 1

        save_config(config)

        if ff == True:
            ff_text = "(Surrender)"
        else: 
            ff_text = ""

        embed = discord.Embed(
            title=f"{match_type.name} - Match Result \n {ff_text}",
            description=(
                f"**{winner.mention}** vs **{looser.mention}**\n\n"
                f"**Sets: {team1SetCounter} - {team2SetCounter} **\n\n"
                f"**1. Set: {set1_team1_score} - {set1_team2_score}  |  {set1_winner.mention} **\n"
                f"**2. Set: {set2_team1_score} - {set2_team2_score}  |  {set2_winner.mention} **"
                f"{set3}"
                f"**Winner:** {winner.mention}\n"
                f"ELO: **{int(oldEloWinner)}** → **{int(winnerElo)}** (+{int(abs(winnerElo - oldEloWinner))})\n\n"
                f"**Loser:** {looser.mention}\n"
                f"ELO: **{int(oldEloLooser)}** → **{int(looserElo)}** (-{int(abs(looserElo - oldEloLooser))})"
            ),
            color=discord.Color.green()
        )

        result_channel = interaction.guild.get_channel(1387116562292408400)
        await result_channel.send(embed=embed)
        await update_leaderboard(interaction)

    @app_commands.command(name="update-elo", description="Send the results of a match and update the ELO rating")
    @app_commands.choices(
        match_type=[
            app_commands.Choice(name="Elo-Match", value="elo-match"),
            app_commands.Choice(name="League-Match", value="league-match")
        ]
    )
    async def update_elo(self, interaction: discord.Interaction, match_type: app_commands.Choice[str], team1: discord.Role, team2: discord.Role, winner: discord.Role, set1_team1_score: int, set1_team2_score: int, set1_winner: discord.Role, set2_team1_score: int, set2_team2_score: int, set2_winner: discord.Role, set3_team1_score: int, set3_team2_score: int, set3_winner: discord.Role):
        has_permission = any(role.name == "elo-perms" for role in interaction.user.roles)

        if not has_permission:
            await interaction.response.send_message("You need the `elo-perms` role to use this command.", ephemeral=True)
            return 
        
        config = load_config()
        guild_id = str(interaction.guild.id)
        teams = config["server"][guild_id]["teams"]
        leaderboard = config["server"][guild_id]["leaderboard"]

        baseElo = 10
        loosingElo = 10

        if any(team.name == "@everyone" for team in [team1, team2, winner]):
            await interaction.response.send_message("You cannot use @everyone.", ephemeral=True)
            return

        if winner not in [team1, team2]:
            await interaction.response.send_message("The winner must be one of the two selected teams.", ephemeral=True)
            return

        if str(team1.id) not in teams or str(team2.id) not in teams:
            await interaction.response.send_message("One or both teams are not registered.", ephemeral=True)
            return

        looser = team2 if winner == team1 else team1
        winner_id = str(winner.id)
        looser_id = str(looser.id)

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

        if set1_team1_score + set1_team2_score == 25:
            if set2_team1_score + set2_team2_score == 25:

                ff = True

                winnerElo = baseElo + 5
                loosingElo = baseElo


        elif (winner == higherPos and multiplicator >= 2) or (winner == higherPos and elo_diff > 65):
            winnerElo = baseElo
            loosingElo = baseElo * 2
        elif (winner == lowerPos and multiplicator >= 2) or (winner == lowerPos and elo_diff > 65):
            winnerElo = baseElo * multiplicator
            loosingElo = (baseElo * 2) + eloBonus // 2
        else:
            winnerElo = baseElo + 5
            loosingElo = baseElo

        if ff == True:
            winnerElo += (eloBonus // 3)
        else:
            winnerElo += eloBonus

        oldEloWinner = leaderboard[winner_id]["elo"]
        oldEloLooser = leaderboard[looser_id]["elo"]

        leaderboard[winner_id]["elo"] += winnerElo
        leaderboard[looser_id]["elo"] = max(0, leaderboard[looser_id]["elo"] - loosingElo)

        teams[winner_id]["elo"] = leaderboard[winner_id]["elo"]
        teams[looser_id]["elo"] = leaderboard[looser_id]["elo"]

        save_config(config)

        await self.send_results_embed(
            interaction, winner, looser, leaderboard, oldEloWinner, oldEloLooser,
            set1_team1_score, set1_team2_score, set1_winner,
            set2_team1_score, set2_team2_score, set2_winner,
            set3_team1_score, set3_team2_score, set3_winner,
            config, guild_id, match_type, ff
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(update_elo(bot))
