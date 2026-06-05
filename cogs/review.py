import json
import logging
import traceback

import discord
from discord import app_commands
from discord.ext import commands

from services.db import get_or_create_user, get_wrong_notes, save_attempt, update_mastery

log = logging.getLogger(__name__)


class ReviewView(discord.ui.View):
    def __init__(self, note: dict, db_user_id: int, discord_user_id: int) -> None:
        super().__init__(timeout=120)
        self.note = note
        self.db_user_id = db_user_id
        self.discord_user_id = discord_user_id
        self.answered = False
        self.message: discord.Message | None = None

        for option in ("A", "B", "C", "D"):
            btn = discord.ui.Button(
                label=option,
                style=discord.ButtonStyle.secondary,
                custom_id=f"review_{note['question_id']}_{option}",
            )
            btn.callback = self._make_callback(option)
            self.add_item(btn)

    def _make_callback(self, option: str):
        async def callback(interaction: discord.Interaction) -> None:
            if interaction.user.id != self.discord_user_id:
                await interaction.response.send_message(
                    "본인의 오답 노트 문제만 답할 수 있습니다.", ephemeral=True
                )
                return
            if self.answered:
                await interaction.response.send_message(
                    "이미 답변하셨습니다!", ephemeral=True
                )
                return

            self.answered = True
            for child in self.children:
                child.disabled = True  # type: ignore[union-attr]

            correct = self.note["answer"]
            is_correct = option == correct
            opts = json.loads(self.note["options_json"])

            await save_attempt(self.db_user_id, self.note["question_id"], option, is_correct)
            result = await update_mastery(self.db_user_id, self.note["question_id"], is_correct)

            consec = result["consecutive_correct"]
            mastered = result["mastered"]

            if mastered:
                title = "🏆 마스터 완료!"
                desc = "2회 연속 정답! 이 문제를 오답 노트에서 졸업했습니다."
                color = discord.Color.purple()
            elif is_correct:
                title = f"✅ 정답! ({consec}/2 연속)"
                desc = "한 번 더 맞히면 마스터됩니다."
                color = discord.Color.green()
            else:
                title = "❌ 오답!"
                desc = None
                color = discord.Color.red()

            embed = discord.Embed(title=title, description=desc, color=color)
            embed.add_field(
                name="선택한 답", value=f"**{option}.** {opts[option]}", inline=False
            )
            if not is_correct:
                embed.add_field(
                    name="정답",
                    value=f"**{correct}.** {opts[correct]}",
                    inline=False,
                )
            embed.add_field(
                name="해설", value=self.note["explanation"][:1020], inline=False
            )

            await interaction.response.edit_message(view=self)
            await interaction.followup.send(embed=embed, ephemeral=True)

        return callback

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True  # type: ignore[union-attr]
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.NotFound:
                pass


def _review_embed(note: dict) -> discord.Embed:
    opts = json.loads(note["options_json"])
    options_text = "\n".join(f"**{k}.** {v}" for k, v in opts.items())
    embed = discord.Embed(
        title=f"📝 오답 노트 복습 — {note['domain']}",
        description=note["question"],
        color=discord.Color.orange(),
    )
    embed.add_field(name="선택지", value=options_text, inline=False)
    embed.set_footer(
        text=f"틀린 횟수 {note['wrong_count']}회  •  연속 정답 {note['consecutive_correct']}/2"
        "  •  A/B/C/D를 눌러 답하세요  •  2분 제한"
    )
    return embed


class Review(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="review", description="오답 노트를 복습합니다")
    async def review(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True)

        try:
            db_user_id = await get_or_create_user(
                interaction.user.id, interaction.user.name
            )
            notes = await get_wrong_notes(db_user_id)

            if not notes:
                embed = discord.Embed(
                    title="📭 오답 노트가 비어있어요",
                    description="/quiz를 풀다 보면 오답이 오답 노트에 쾳입니다.\n"
                    "그러면 여기서 복습할 수 있어요!",
                    color=discord.Color.green(),
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            note = notes[0]  # highest wrong_count first
            view = ReviewView(note, db_user_id, interaction.user.id)
            msg = await interaction.followup.send(embed=_review_embed(note), view=view)
            view.message = msg

        except Exception as exc:
            log.error("review error: %s", traceback.format_exc())
            await interaction.followup.send(f"오류가 발생했습니다: {exc}", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Review(bot))
