import logging
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from services.db import init_db

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("aws-saa-bot")

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN is not set in the environment / .env file")

EXTENSIONS = (
    "cogs.quiz",
    "cogs.review",
    "cogs.stats",
    "cogs.admin",
    "cogs.scheduler",
)


class SAABot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self) -> None:
        await init_db()
        log.info("Database initialised")

        for ext in EXTENSIONS:
            await self.load_extension(ext)
            log.info("Loaded extension: %s", ext)

        await self.tree.sync()
        log.info("Slash commands synced")

    async def on_ready(self) -> None:
        log.info("Logged in as %s (id=%s)", self.user, self.user.id)  # type: ignore[union-attr]

    async def on_app_command_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        log.error("Unhandled app_command error: %s", error, exc_info=error)
        msg = f"예기치 않은 오류: {error}"
        try:
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
        except Exception:
            pass


def main() -> None:
    bot = SAABot()
    bot.run(DISCORD_TOKEN, log_handler=None)


if __name__ == "__main__":
    main()
