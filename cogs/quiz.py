import json
import random

import discord
from discord import app_commands
from discord.ext import commands

from services.db import get_or_create_user, save_attempt, save_question, upsert_wrong_note
from services.llm import explain_concept, generate_quiz

DOMAINS = ["EC2", "S3", "VPC", "IAM", "RDS", "Lambda", "CloudFront", "Route53"]


class QuizView(discord.ui.View):
    def __init__(self, quiz_data: dict, question_id: int) -> None:
        super().__init__(timeout=120)
        self.quiz_data = quiz_data
        self.question_id = question_id
        self.answered: set[int] = set()
        self.message: discord.Message | None = None

        for option in ("A", "B", "C", "D"):
            btn = discord.ui.Button(
                label=option,
                style=discord.ButtonStyle.secondary,
                custom_id=f"quiz_{question_id}_{option}",
            )
            btn.callback = self._make_callback(option)
            self.add_item(btn)

    def _make_callback(self, option: str):
        async def callback(interaction: discord.Interaction) -> None:
            uid = interaction.user.id
            if uid in self.answered:
                await interaction.response.send_message("이미 답변하셨습니다!", ephemeral=True)
                return
            self.answered.add(uid)
            db_user_id = await get_or_create_user(uid, interaction.user.name)
            correct = self.quiz_data["answer"]
            is_correct = option == correct
            opts = self.quiz_data["options"]
            await save_attempt(db_user_id, self.question_id, option, is_correct)
            if not is_correct:
                await upsert_wrong_note(db_user_id, self.question_id)
            color = discord.Color.green() if is_correct else discord.Color.red()
            title = "✅ 정답!" if is_correct else "❌ 오답!"
            embed = discord.Embed(title=title, color=color)
            embed.add_field(name="선택한 답", value=f"**{option}.** {opts[option]}", inline=False)
            if not is_correct:
                embed.add_field(name="정답", value=f"**{correct}.** {opts[correct]}", inline=False)
            embed.add_field(name="해설", value=self.quiz_data["explanation"][:1020], inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        return callback

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True  # type: ignore[union-attr]
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.NotFound:
                pass


def _quiz_embed(quiz_data: dict, domain: str) -> discord.Embed:
    opts = quiz_data["options"]
    options_text = "\n".join(f"**{k}.** {v}" for k, v in opts.items())
    embed = discord.Embed(
        title=f"AWS SAA-C03 퀴즈 — {domain}",
        description=quiz_data["question"],
        color=discord.Color.blue(),
    )
    embed.add_field(name="선택지", value=options_text, inline=False)
    embed.set_footer(text="A / B / C / D 버튼을 눌러 답하세요  •  제한 시간 2분")
    return embed


class Quiz(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="quiz", description="AWS SAA-C03 4지선다 문제를 풀어보세요")
    @app_commands.describe(domain="출제 도메인 (미입력 시 랜덤)")
    @app_commands.choices(domain=[app_commands.Choice(name=d, value=d) for d in DOMAINS])
    async def quiz(self, interaction: discord.Interaction, domain: str | None = None) -> None:
        await interaction.response.defer(thinking=True)
        selected_domain = domain or random.choice(DOMAINS)
        try:
            quiz_data = await generate_quiz(selected_domain)
            question_id = await save_question(
                domain=selected_domain,
                content=quiz_data["question"],
                options_json=json.dumps(quiz_data["options"], ensure_ascii=False),
                answer=quiz_data["answer"],
                explanation=quiz_data["explanation"],
            )
            view = QuizView(quiz_data, question_id)
            msg = await interaction.followup.send(embed=_quiz_embed(quiz_data, selected_domain), view=view)
            view.message = msg
        except Exception as exc:
            import logging, traceback
            logging.getLogger(__name__).error("quiz error: %s", traceback.format_exc())
            await interaction.followup.send(f"오류가 발생했습니다: {exc}", ephemeral=True)

    @app_commands.command(name="explain", description="AWS 개념을 설명합니다")
    @app_commands.describe(concept="설명할 AWS 개념 (예: S3 Lifecycle, VPC Peering)")
    async def explain(self, interaction: discord.Interaction, concept: str) -> None:
        await interaction.response.defer(thinking=True)
        try:
            explanation = await explain_concept(concept)
        except Exception as exc:
            await interaction.followup.send(f"설명 생성 중 오류가 발생했습니다: {exc}", ephemeral=True)
            return
        embed = discord.Embed(
            title=f"AWS 개념 설명: {concept}",
            description=explanation[:4000],
            color=discord.Color.gold(),
        )
        embed.set_footer(text="AWS SAA-C03 Study Bot")
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Quiz(bot))
