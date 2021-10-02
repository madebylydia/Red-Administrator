from abc import ABC
from typing import Optional, Union

import discord
from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.commands import Cog

from .falxclass import Allowance


class MixinMeta(ABC):
    bot: Red
    config: Config

    def get_approve_color(self, left_guild: bool) -> discord.Color:
        raise NotImplementedError()

    async def get_leaving_message(self) -> str:
        raise NotImplementedError()

    def generate_invite(self, guild_id: Optional[Union[str, int]] = None) -> str:
        raise NotImplementedError()

    async def generate_leave_embed_for_guild(self, guild: discord.Guild) -> discord.Embed:
        raise NotImplementedError()

    def generate_join_embed_for_guild(
        self, guild: discord.Guild, is_accepted: bool
    ) -> discord.Embed:
        raise NotImplementedError()

    async def get_notification_channel(self) -> Optional[discord.TextChannel]:
        raise NotImplementedError()

    async def maybe_get_guild(self, guild: Union[int, discord.Guild]) -> Allowance:
        raise NotImplementedError()


class CompositeMetaClass(type(Cog), type(ABC)):
    """
    Allows the metaclass used for proper type detection to coexist with discord.py's metaclass.
    Credit to https://github.com/Cog-Creators/Red-DiscordBot (mod cog) for all mixin stuff.
    """

    pass
