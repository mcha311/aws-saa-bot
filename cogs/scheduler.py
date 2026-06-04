import datetime
import logging
import os

import discord
from discord.ext import commands, tasks

from services.db import get_users_with_pending_review

log = logging.getLogger(__name__)
DAILY_REVIEW_ENABLED = os.getenv("DAILY_REVIEW_ENABLED", "false").lower() == "true"
KST = datetime.timezone(datetime.timedelta(hours=9))
_REVIEW_TIME = datetime.time(hour=9, minute=0, tzinfo=KST)


class Scheduler(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        if DAILY_REVIEW_ENABLED:
            self.daily_review.start()
            log.info("Daily review scheduler started (fires at 09:00 KST)")
        else:
            log.info("Daily review scheduler disabled (DAILY_REVIEW_ENABLED != true)")

    def cog_unload(self) -> None:
        self.daily_review.cancel()

    @tasks.loop(time=_REVIEW_TIME)
    async def daily_review(self) -> None:
        log.info("Running daily review DM task")
        users = await get_users_with_pending_review()
        sent = 0
        for user in users:
            try:
                discord_user = await self.bot.fetch_user(user["discord_id"])
                await discord_user.send("📚 오늘의 복습 문제가 있어요! `/review` 로 확인하세요.")
                sent += 1
            except discord.Forbidden:
                log.debug("Cannot DM user %s (DMs disabled)", user["discord_id"])
            except Exception as exc:
                log.warning("DM failed for %s: %s", user["discord_id"], exc)
        log.info("Daily review DMs sent: %d / %d", sent, len(users))

    @daily_review.before_loop
    async def before_daily_review(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Scheduler(bot))
