import discord
from discord import app_commands
from discord.ext import commands

from services.db import get_leaderboard, get_or_create_user, get_user_stats


def _bar(pct: float, length: int = 8) -> str:
    filled = round(pct / 100 * length)
    return "█" * filled + "░" * (length - filled)


class Stats(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="stats", description="내 학습 통계를 확인합니다")
    async def stats(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)

        try:
            db_user_id = await get_or_create_user(
                interaction.user.id, interaction.user.name
            )
            s = await get_user_stats(db_user_id)

            total = s["total"]
            correct = s["correct"]
            wrong = total - correct
            accuracy = (correct / total * 100) if total > 0 else 0.0

            embed = discord.Embed(
                title=f"📊 {interaction.user.display_name}의 학습 통계",
                color=discord.Color.blue(),
            )
            embed.add_field(name="송 문제", value=str(total), inline=True)
            embed.add_field(name="정답", value=str(correct), inline=True)
            embed.add_field(name="오답", value=str(wrong), inline=True)
            embed.add_field(
                name="전체 정답률", value=f"{_bar(accuracy)} {accuracy:.1f}%", inline=True
            )
            embed.add_field(
                name="오답 노트 잔여", value=f"{s['unmastered_wrong']}문제", inline=True
            )
            embed.add_field(
                name="학습 스트릭", value=f"🔥 {s['streak']}일 연속", inline=True
            )

            if s["domain_stats"]:
                lines = []
                for domain, ds in s["domain_stats"].items():
                    acc = (ds["correct"] / ds["total"] * 100) if ds["total"] > 0 else 0.0
                    lines.append(
                        f"`{domain:<12}` {_bar(acc)} {acc:.0f}%  ({ds['total']}문제)"
                    )
                embed.add_field(
                    name="도메인별 정답률",
                    value="\n".join(lines),
                    inline=False,
                )

            await interaction.followup.send(embed=embed)

        except Exception as exc:
            import logging
            import traceback

            logging.getLogger(__name__).error(
                "stats error: %s", traceback.format_exc()
            )
            await interaction.followup.send(f"오류가 발생했습니다: {exc}", ephemeral=True)

    @app_commands.command(name="leaderboard", description="서버 Top 5 학습 랜킹을 봅니다")
    async def leaderboard(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True)

        try:
            discord_ids: list[int] | None = None
            if interaction.guild:
                cached = [m.id for m in interaction.guild.members if not m.bot]
                if cached:
                    discord_ids = cached

            top = await get_leaderboard(discord_ids=discord_ids)

            if not top:
                embed = discord.Embed(
                    title="🏆 학습 리더보드",
                    description="아직 데이터가 부족합니다.\n최소 3문제 이상 풀면 랜킹에 올라갑니다!",
                    color=discord.Color.gold(),
                )
                await interaction.followup.send(embed=embed)
                return

            medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
            lines = []
            for i, u in enumerate(top):
                acc = (u["correct"] / u["total"] * 100) if u["total"] > 0 else 0.0
                lines.append(
                    f"{medals[i]} **{u['username']}** — "
                    f"{_bar(acc, 6)} {acc:.1f}% ({u['total']}문제)"
                )

            embed = discord.Embed(
                title="🏆 학습 리더보드 Top 5",
                description="\n".join(lines),
                color=discord.Color.gold(),
            )
            embed.set_footer(text="최소 3문제 이상 풀어야 집계됩니다")
            await interaction.followup.send(embed=embed)

        except Exception as exc:
            import logging
            import traceback

            logging.getLogger(__name__).error(
                "leaderboard error: %s", traceback.format_exc()
            )
            await interaction.followup.send(f"오류가 발생했습니다: {exc}", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Stats(bot))
