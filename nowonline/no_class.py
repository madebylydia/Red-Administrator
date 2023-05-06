from datetime import datetime
from enum import Enum
from string import Template
from typing import Optional, TypedDict

import discord
from redbot.core.bot import Red
from redbot.core.commands import Context


class EventTypeTyping(TypedDict):
    color: discord.Color
    emoji: str
    title: Template


class EVENT_TYPE(Enum):
    ON_CONNECT = {
        "color": discord.Color.dark_green(),
        "emoji": "🔗",
        "title": Template("$bot is connected."),
    }
    ON_READY = {
        "color": discord.Color.green(),
        "emoji": "⚡",
        "title": Template("$bot is ready."),
    }
    ON_SHARD_CONNECT = {
        "color": discord.Color.dark_purple(),
        "emoji": "🔗",
        "title": Template("Shard $shard_id is connected."),
    }
    ON_SHARD_READY = {
        "color": discord.Color.purple(),
        "emoji": "⚡",
        "title": Template("Shard $shard_id is ready."),
    }
    ON_RESUMED = {
        "color": discord.Color.gold(),
        "emoji": "⏳",
        "title": Template("$bot has resumed his session."),
    }
    ON_SHARD_RESUMED = {
        "color": discord.Color.gold(),
        "emoji": "⏳",
        "title": Template("Shard $shard_id has resumed his session."),
    }
    ON_DISCONNECT = {
        "color": discord.Color.red(),
        "emoji": "🛑",
        "title": Template("$bot is disconnected."),
    }
    ON_SHARD_DISCONNECT = {
        "color": discord.Color.red(),
        "emoji": "🛑",
        "title": Template("Shard $shard_id is disconnected."),
    }


class Event:
    """
    The representation of an event from events.py.
    This class will format everything the cog may need for proper display.
    """

    def __init__(
        self, event_type: EVENT_TYPE, bot: Red, *, shard_id: Optional[int] = None
    ) -> None:
        self.event_type = event_type.name
        self.created_at = datetime.utcnow()

        self._shard_id: Optional[int] = shard_id

        self.__bot: Red = bot
        self.__values: EventTypeTyping = event_type.value

    def to_embed(self):
        embed = discord.Embed(
            color=self.__values["color"],
            title=self.__values["title"].safe_substitute(
                bot=self.__bot.user.name, shard_id=getattr(self, "_shard_id", None)
            ),
        )
        embed.description = f"Event triggered at: {self.created_at.strftime('%H:%M:%S')}"
        embed.set_footer(text=f"NowOnline | {self.event_type} | Shard: {self._shard_id}")
        return embed


class Case:
    """
    A case is the representation of when the bot goes down.

    A case is automatically created when the bot shutdown, which create an open case.
    It is then updated when the bot comes back to life.
    Else, a case is automatically created after the bot comes suddenly back to life.
    """

    def __init__(self, bot: Red, *, case_id: int):
        self.bot: Red = bot
        self.case_id: int = case_id

    def to_json(self):
        return {"case_id": self.case_id}

    @classmethod
    async def convert(cls, ctx: Context, argument: int):
        """
        This function is automatically called when running a command requiring a case.
        It shouldn't be used manually.
        """
        return cls(ctx.bot, case_id=argument)
