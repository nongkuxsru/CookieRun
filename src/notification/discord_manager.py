from __future__ import annotations

from src.notification.discord_notifier import DiscordNotifier


class DiscordManager:
    def __init__(self, config):
        self.found = DiscordNotifier(
            config.get("discord.found_webhook_url", "")
        )

        self.status = DiscordNotifier(
            config.get("discord.status_webhook_url", "")
        )

        self.error = DiscordNotifier(
            config.get("discord.error_webhook_url", "")
        )