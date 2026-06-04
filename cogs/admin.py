import discord
from discord import app_commands
from discord.ext import commands

from services.db import reset_user_stats


class ResetConfirmView(discord.ui.View):
    def __init__(self, discord_id: int) -> None:
        super().__init__(timeout=30)
        self.discord_id = discord_id

    @discord.ui.button(label="초기화 확인", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id != self.discord_id:
            await interaction.response.send_message("본인의 기록만 초기화할 수 있습니다.", ephemeral=True)
            return
        for child in self.children:
            child.disabled = True  # type: ignore[union-attr]
        success = await reset_user_stats(self.discord_id)
        embed = discord.Embed(
            title="✅ 초기화 완료" if success else "ℹ️ 기록 없음",
            description="모든 퀴즈 기록과 오답 노트가 삭제되었습니다." if success else "초기화할 기록이 없습니다.",
            color=discord.Color.green() if success else discord.Color.greyple(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="취소", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        for child in self.children:
            child.disabled = True  # type: ignore[union-attr]
        embed = discord.Embed(title="취소됨", description="초기화가 취소되었습니다.", color=discord.Color.greyple())
        await interaction.response.edit_message(embed=embed, view=self)


class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="reset", description="내 퀴즈 기록과 오답 노트를 초기화합니다")
    async def reset(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(
            title="⚠️ 기록 초기화 확인",
            description="**모든 퀴즈 기록과 오답 노트**가 영구 삭제됩니다.\n이 작업은 되돌릴 수 없습니다.",
            color=discord.Color.orange(),
        )
        view = ResetConfirmView(interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Admin(bot))
