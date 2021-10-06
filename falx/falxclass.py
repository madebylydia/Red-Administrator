from datetime import datetime
from typing import TypedDict

import discord
from redbot.core.config import Config


class GuildData(TypedDict):
    guild_id: int
    is_allowed: bool
    added_at: int
    author: str
    reason: str
    is_brut: bool


class Allowance:
    """
    Represent an allowance for a guild. This may not have all the attributes of a guild but
    it is a class to easily make change to Config without making much raw code.
    """

    def __init__(
        self,
        guild_id: int,
        *,
        is_allowed: bool,
        added_at: int,
        author: str,
        reason: str,
        is_brut: bool,
        config_instance: Config,
    ) -> None:
        self.guild_id: int = guild_id
        self.is_allowed: bool = is_allowed
        self.author: str = author
        self.added_at: int = added_at
        self.reason: str = reason

        self.is_brut: bool = is_brut

        self.__config: Config = config_instance

    def __repr__(self) -> str:
        return f"<Allowance guild_id={self.guild_id} is_allowed={self.is_allowed}>"

    async def allow_guild(self, author: discord.User, reason: str) -> bool:
        """
        Allow a guild and save it to Falx.

        Parameters
        ----------
        author: discord.User
            The user allowing the guild.
        reason: str
            The reason for adding.

        Returns
        -------
        bool: `True` if the guild has been added. `False` if the guild was already added.
        """
        if not self.is_allowed:
            self.author = str(author)
            self.is_allowed = True
            self.reason = reason
            self.added_at = round(datetime.now().timestamp())
            await self.save()
            return True
        return False

    async def disallow_guild(self, author: discord.User, reason: str = None):
        """
        Disallow a guild and save it to Falx.

        Parameters
        ----------
        author: discord.User
            The user removing the guild.
        reason: str
            The reason for removal.

        Returns
        -------
        bool: `True` if the guild has been removed. `False` if the guild was already removed.
        """
        if self.is_allowed:
            self.author = str(author)  # This can be the bot
            self.reason = reason if reason else "Automatic Removal (Guild has been left)"
            self.added_at = round(datetime.now().timestamp())
            self.is_allowed = False
            await self.save()
            return True
        return False

    async def save(self) -> bool:
        """
        Save changes to config.
        """
        if self.is_brut:
            self.is_brut = False
        await self.__config.guild_from_id(self.guild_id).set_raw(
            value={
                "is_allowed": self.is_allowed,
                "author": self.author,
                "added_at": self.added_at,
                "reason": self.reason,
                "is_brut": self.is_brut,
            }
        )
        return True

    def to_dict(self):
        return {
            "guild_id": self.guild_id,
            "is_allowed": self.is_allowed,
            "author": self.author,
            "added_at": self.added_at,
            "reason": self.reason,
            "is_brut": self.is_brut,
        }

    @classmethod
    def from_dict(cls, data: GuildData, config_instance: Config):
        """
        Return a guild's allowance from a guild's data.
        """
        return cls(
            guild_id=data["guild_id"],
            is_allowed=data["is_allowed"],
            author=data["author"],
            added_at=data["added_at"],
            reason=data["reason"],
            is_brut=data["is_brut"],
            config_instance=config_instance,
        )

    @classmethod
    async def from_guild(cls, guild: discord.Guild, config_instance: Config):
        """
        Return a guild's allowance from a guild.

        This will first pull data from Config then return the class.
        """
        data: GuildData = await config_instance.guild(guild).all()
        return cls(
            guild_id=guild.id,
            is_allowed=data["is_allowed"],
            author=data["author"],
            added_at=data["added_at"],
            reason=data["reason"],
            is_brut=data["is_brut"],
            config_instance=config_instance,
        )

    @classmethod
    async def from_guild_id(cls, guild_id: int, config_instance: Config):
        """
        Return a guild's allowance from a guild.

        This will first pull data from Config then return the class.
        """
        data: GuildData = await config_instance.guild_from_id(guild_id).all()
        return cls(
            guild_id=guild_id,
            is_allowed=data["is_allowed"],
            author=data["author"],
            added_at=data["added_at"],
            reason=data["reason"],
            is_brut=data["is_brut"],
            config_instance=config_instance,
        )
