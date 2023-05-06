from datetime import datetime
from string import Template
from typing import Optional, Union

import discord
from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import (
    bold,
    humanize_list,
    humanize_number,
    inline,
)

from .abc import CompositeMetaClass
from .commands import Commands
from .falxclass import Allowance
from .listeners import Listeners

DEFAULT_LEAVING_TEXT = (
    "Someone on your server invited me ($bot_name) but your server is not whitelisted. "
    "In order to add me in your server, you are required to contact my owner.\nFor that "
    "reason, I will be leaving your server until you get whitelisted, then you'll be able to "
    "invite me again!"
)
DEFAULT_GUILD_SETTINGS = {
    "is_allowed": False,
    "author": None,
    "added_at": None,
    "reason": None,
    "is_brut": True,
}
DEFAULT_GLOBAL_SETTINGS = {
    "notification_channel": None,
    "leaving_message": DEFAULT_LEAVING_TEXT,
    "autoremove": True,
    "enabled": True,
}


class Falx(commands.Cog, Commands, Listeners, name="Falx", metaclass=CompositeMetaClass):
    """
    Automatic guild manager.

    This cog act as a guild approve system. Only the bot's owner(s) can use these commands. Each guild must be
    whitelisted before inviting the bot, otherwise the bot will automatically leave the server. If the bot leaves
    a guild that has been whitelisted before, their guild will be removed from the whitelist and will require a
    new validation.
    """

    def __init__(self, bot: Red, *args, **kwargs):
        self.config: Config = Config.get_conf(self, 554312654, force_registration=True)
        self.config.register_global(**DEFAULT_GLOBAL_SETTINGS)
        self.config.register_guild(**DEFAULT_GUILD_SETTINGS)
        self.bot: Red = bot

        self.is_enabled: Optional[bool] = None

        super().__init__(*args, **kwargs)

    def get_approve_color(self, left_guild: bool) -> discord.Color:
        """
        Get a colour for the embed if the guild is left.
        """
        return discord.Color.red() if left_guild else discord.Color.green()

    async def should_leave_guild(self, guild: discord.Guild) -> bool:
        """
        Determine if the guild should be left.
        """
        if self.is_enabled:
            guild_info = await Allowance.from_guild(guild, self.config)
            return not guild_info.is_allowed
        return False

    async def get_leaving_message(self) -> str:
        message = await self.config.leaving_message()

        # This will get owners and return their name in an humanized list
        owners = humanize_list(
            [
                str(fetched_owner)
                for fetched_owner in (self.bot.get_user(owner) for owner in self.bot.owner_ids)
                if fetched_owner
            ]
        )
        return Template(message).safe_substitute(
            {
                "bot_name": self.bot.user.display_name,
                "owners_name": owners,
            }
        )

    async def generate_invite(self, guild_id: Optional[Union[str, int]] = None) -> str:
        url = await self.bot.get_invite_url()
        if guild_id:
            url += f"&guild_id={str(guild_id)}"
        return url

    async def get_notification_channel(self) -> Optional[discord.TextChannel]:
        channel_id = await self.config.notification_channel()
        return self.bot.get_channel(channel_id) if channel_id else channel_id

    def generate_join_embed_for_guild(
        self, guild: discord.Guild, is_accepted: bool
    ) -> discord.Embed:
        description = (
            f"Falx detected that {bold(self.bot.user.name)} has joined "
            f"{inline(guild.name)}.\n\n"
        )
        embed = discord.Embed(
            title=f"[Falx] {self.bot.user.name} joined a guild.",
            description=description,
            color=self.get_approve_color(not is_accepted),
        )
        embed.add_field(
            name="Information",
            value=f"Name: {guild.name}\nID: {guild.id}\nOwner: {str(guild.owner)}",
        )
        humans = len([human for human in guild.members if not human.bot])
        bots = len([human for human in guild.members if human.bot])
        percentage = bots / guild.member_count * 100 if guild.member_count else None
        embed.add_field(
            name="Members count",
            value=f"{guild.member_count} members.\n{humans} humans.\n{bots} bots.\nRatio: {round(percentage) if percentage else 'N/A'}% bots.",
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        if guild.splash:
            embed.set_image(url=guild.splash.url)
        embed.set_footer(
            text="This guild was approved."
            if is_accepted
            else "This guild was left automatically as it hasn't been approved.",
            icon_url=self.bot.user.avatar.url if self.bot.user and self.bot.user.avatar else None,
        )
        return embed

    async def generate_leave_embed_for_guild(self, guild: discord.Guild) -> discord.Embed:
        autoremove = await self.config.autoremove()
        description = (
            f"Falx detected that {bold(self.bot.user.name)} has left " f"{inline(guild.name)}."
        )
        if autoremove:
            description += (
                "\nThe Falx's policy removed this whitelisted guild from the list of Falx's "
                "whitelisted guilds."
            )
        embed = discord.Embed(
            title=f"[Falx] {self.bot.user.name} left a guild.",
            description=description,
            color=discord.Color.gold(),
        )
        embed.add_field(
            name="Information",
            value=f"Name: {guild.name}\nID: {guild.id}\nOwner: {str(guild.owner)}",
        )
        embed.add_field(name="Member count", value=f"{guild.member_count} members.")
        embed.set_thumbnail(url=guild.icon_url)
        if guild.splash:
            embed.set_image(url=guild.splash_url)
        if guild.me:
            embed.set_footer(
                text=(
                    "This guild was joined "
                    f"{humanize_number((datetime.now() - guild.me.joined_at).days)} days ago."
                ),
                icon_url=self.bot.user.avatar_url,
            )
        else:
            embed.set_footer(
                text=(
                    "Unable to determine when the guild was joined. (Missing "
                    "information about the bot in the guild)"
                ),
                icon_url=self.bot.user.avatar_url,
            )
        return embed

    async def maybe_get_guild(self, guild: Union[int, discord.Guild]) -> Allowance:
        if isinstance(guild, discord.Guild):
            guild = guild.id
        return await Allowance.from_guild_id(guild, self.config)

    async def cog_load(self):
        self.is_enabled = await self.config.enabled()

async def setup(bot: Red):
    falx = Falx(bot)
    await bot.add_cog(falx)
    await falx.cog_load()
