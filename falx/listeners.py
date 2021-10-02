from abc import ABCMeta
from contextlib import suppress

import discord
from redbot.core import commands
from .falxclass import Allowance

from .abc import MixinMeta


class Listeners(MixinMeta, metaclass=ABCMeta):
    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        guild_info = await Allowance.from_guild(guild, self.config)
        if not guild_info.is_allowed:
            if guild.owner:
                with suppress(discord.HTTPException):
                    await guild.owner.send(await self.get_leaving_message())
            await guild.leave()
        embed = self.generate_join_embed_for_guild(guild, is_accepted=guild_info.is_allowed)
        if channel := await self.get_notification_channel():
            await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        if await self.config.autoremove():
            guild_info = await Allowance.from_guild(guild, self.config)
            if not guild_info.is_allowed:
                return
            await guild_info.disallow_guild(str(self.bot.user), "Automatic Removal")
        embed = await self.generate_leave_embed_for_guild(guild)
        if channel := await self.get_notification_channel():
            await channel.send(embed=embed)
