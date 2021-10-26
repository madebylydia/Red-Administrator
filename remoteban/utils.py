from typing import Dict, List, Optional

import discord
from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import bold, inline, quote


async def make_embed(
    bot: Red,
    ctx: commands.Context,
    success_servers: Optional[List[discord.Guild]],
    failed_servers: Optional[Dict[discord.Guild, str]],
    not_found_users: Optional[List[int]],
    already_banned_or_unbanned: Optional[List[discord.Member]],
) -> discord.Embed:
    stringy_thingy = str()

    if success_servers:
        stringy_thingy += f"{bold('Successfully (un)banned')}\n" + "\n".join(
            [f"{quote(f'{server.name}')}" for server in success_servers]
        )
    if already_banned_or_unbanned:
        stringy_thingy += (
            "\n"
            if stringy_thingy
            else ""
            + f"{bold('Already (un)banned in those server(s)')}\n"
            + "\n".join([f"{quote(inline(server.name))}" for server in already_banned_or_unbanned])
        )
    if failed_servers:
        stringy_thingy += (
            "\n"
            if stringy_thingy
            else ""
            + f"{bold('Failed in the following server(s)')}\n"
            + "\n".join(
                [f"{quote(f'{keys[0]} - Reason: {keys[1]}')}" for keys in failed_servers.items()]
            )
        )
    if not_found_users:
        stringy_thingy += (
            "\n"
            if stringy_thingy
            else ""
            + f"{bold('Already (un)banned')}\n"
            + "\n".join([f"{quote(user)}" for user in not_found_users])
        )
    return discord.Embed(
        title="Banning result",
        description=stringy_thingy,
        colour=await bot.get_embed_color(ctx.channel),
    )


def allowed_to_ban():
    async def predicate(ctx: commands.Context):
        if await ctx.bot.is_owner(ctx.author):
            return True
        await ctx.bot.wait_until_red_ready()
        is_oki = await Config.get_conf(
            None, identifier=5578554655885, force_registration=True, cog_name="RemoteBan"
        ).allowed_users()
        return True if ctx.author.id in is_oki else False

    return commands.check(predicate)
