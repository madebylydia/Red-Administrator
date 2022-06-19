from abc import ABCMeta
from datetime import datetime
from json import dumps
from typing import Optional

import discord
from redbot.core import commands
from redbot.core.utils.chat_formatting import bold, inline, pagify, warning, text_to_file
from redbot.core.utils.predicates import MessagePredicate

from .abc import MixinMeta
from .falxclass import Allowance


class Commands(MixinMeta, metaclass=ABCMeta):
    @commands.group()
    @commands.is_owner()
    async def falx(self, ctx: commands.Context):
        """
        Falx - Automatic Guild Manager.
        """

    @falx.command(name="alter", aliases=["reason"])
    async def change_reason(self, ctx: commands.Context, guild_id: int, *, new_reason: str):
        """
        Change the reason of a guild that has been allowed.
        """
        allowance = await Allowance.from_guild_id(guild_id, self.config)
        if allowance.is_brut:
            await ctx.send("This guild was never approved or refused.")
            return
        allowance.reason = new_reason
        await allowance.save()
        await ctx.send("Done. Reason modified.")

    @falx.command(name="check")
    async def check_guild_status(self, ctx: commands.Context, guild_id: int):
        """
        Check if a guild is added to the list.
        """
        allowance = await self.maybe_get_guild(guild_id)
        is_joined = bool(self.bot.get_guild(guild_id))
        joined = f"I am {'' if allowance.is_allowed else 'still '}operating in this guild." if is_joined else f"I am not operating in this guild{' yet' if allowance.is_allowed else ''}."

        if allowance.is_brut:
            await ctx.send(f"This guild was never approved before.\n{joined}")
            return
        await ctx.send(
            f"This guild is {'allowed' if allowance.is_allowed else 'refused'}.\n"
            f"Reason: {allowance.reason}\n"
            f"Since: {datetime.fromtimestamp(allowance.added_at) if allowance.added_at else 'Never'}\n"
            f"By: {allowance.author}\n{joined}"
        )

    @falx.command(name="add")
    async def add_guild_to_falx(self, ctx: commands.Context, guild_id: int, *, reason: str):
        """
        Add a guild ID to the allowed guilds.
        """
        guild_allowance = await self.maybe_get_guild(guild_id)
        has_been_added = await guild_allowance.allow_guild(ctx.author, reason)
        await ctx.send(
            f"Done. Guild added.\n<{await self.generate_invite(guild_id)}>"
            if has_been_added
            else "Done. Guild was already added."
        )

    @falx.command(name="geninvite", aliases=["gen", "geninv", "invite", "inv"])
    async def generate_invite_for_guild(self, ctx: commands.Context, guild_id: int):
        """
        Generate an invite link for a guild.
        """
        if not (await self.maybe_get_guild(guild_id)).is_allowed:
            await ctx.send(
                warning(
                    "This guild is not allowed. Consider adding it to Falx in order to use the link."
                )
            )
        await ctx.send(f"Invitation: <{await self.generate_invite(guild_id)}>")

    @falx.command(name="remove", aliases=["del", "rem", "rm"])
    async def remove_guild_to_falx(self, ctx: commands.Context, guild_id: int, *, reason: str):
        """
        Remove a guild from allowed guilds.
        """
        guild_allowance = await self.maybe_get_guild(guild_id)
        if guild_allowance.is_brut:
            await ctx.send("This guild was never added before.")
            return
        has_been_removed = await guild_allowance.disallow_guild(ctx.author, reason)
        await ctx.send(
            "Done. Guild removed." if has_been_removed else "Done. Guild was already removed."
        )

    @falx.command(name="list", aliases=["ls"])
    async def listing(self, ctx: commands.Context):
        """
        List guilds that has been added to the whitelist.
        """
        guilds_data = await self.config.all_guilds()
        guilds = []
        for guild in guilds_data.items():
            guild[1]["guild_id"] = guild[0]
            guilds.append(Allowance.from_dict(guild[1], self.config))
        msg = "These guilds has been whitelisted:\n"
        for guild in guilds:
            possible_guild = self.bot.get_guild(guild.guild_id)
            if guild.is_allowed:
                msg += (
                    f"\nGuild ID: {guild.guild_id} "
                    f"({inline(possible_guild.name) if possible_guild else inline('Guild not found')})"
                    f"\nReason: {guild.reason}\nSince: "
                    f"{datetime.fromtimestamp(guild.added_at) if guild.added_at else 'Never'}\n"
                    f"By: {guild.author}\n"
                )
        for message_part in pagify(msg):
            await ctx.send(message_part)

    @falx.command(name="fetch")
    async def add_all_already_joined_guilds(self, ctx: commands.Context):
        """
        Fetch all joined guilds and add them to the whitelist.
        """
        await ctx.send(
            "This will get all actual guilds and put them into the whitelist.\n"
            "Are you sure you want me to do that? (y/N)"
        )
        pred = MessagePredicate.yes_or_no(ctx)
        await self.bot.wait_for("message", check=pred)
        if not pred.result:
            return await ctx.send("Ignored.")
        has_been_added = 0
        async with ctx.typing():
            for guild in self.bot.guilds:
                guild_allowance = await Allowance.from_guild(guild, self.config)
                await guild_allowance.allow_guild(self.bot.user, "Automatic addition")
                has_been_added += 1
        await ctx.send(
            f"Done. {has_been_added} guild{'s' if has_been_added != 1 else ''} has been added."
        )

    @falx.command(name="setchannel")
    async def set_channel(self, ctx: commands.Context, *, channel: Optional[discord.TextChannel] = None):
        """
        Set the channel to send new guilds notification.
        """
        notification_channel = await self.config.notification_channel()

        if channel == channel and not notification_channel and (not channel):
            await ctx.send("No channel are set. Please set one.")
            return

        if channel:
            await self.config.notification_channel.set(channel.id)
        else:
            await self.config.notification_channel.clear()
        await ctx.send(
            (
                f"The channel has been changed from {inline(str(notification_channel))} "
                f"to {inline(str(channel.id) if channel else 'None')}."
            )
        )

    @falx.command(name="settings")
    async def show_falx_settings(self, ctx: commands.Context):
        """
        Show Falx's settings.
        """
        config = await self.config.all()
        data = text_to_file(dumps(config, indent=2), filename="config.json")

        if config["notification_channel"]:
            if notification_channel := self.bot.get_channel(config["notification_channel"]):
                notification_channel = f"{notification_channel.mention} - {notification_channel.name} ({notification_channel.id})"
            else:
                notification_channel = "Cannot found the notification channel, was it deleted?"
        else:
            notification_channel = "Not set"
        embed = discord.Embed(
            title="Settings of Falx",
            description=f"This is the settings of Falx, actually, Falx is {bold('enabled' if config['enabled'] else 'disabled')}, you can see more informations below.",
            color=await self.bot.get_embed_color(ctx.channel),
        )
        embed.add_field(name="Enabled", value=str(config["enabled"]))
        embed.add_field(name="Notification channel", value=notification_channel)
        if len(config["leaving_message"]) > 1024:
            embed.add_field(name="Leaving message", value=f"{config['leaving_message'][:1021]}...")
        else:
            embed.add_field(name="Leaving message", value=config["leaving_message"])
        embed.add_field(name="Autoremove", value=str(config["autoremove"]))

        await ctx.send(embed=embed, file=data)

    @falx.command(name="leavingmessage")
    async def change_leaving_message(self, ctx: commands.Context, *, new_message: Optional[str] = None):
        """
        Change/Reset the message sent to the guild's owner when leaving a guild.

        You can use these variables in your message and they'll automatically change into their corresponding
        values.

        `$bot_name`: The bot's name.
        `$owners_name`: A list with owner's name + discriminator.
        """
        if not new_message:
            await self.config.leaving_message.clear()
            await ctx.send("Leaving message has been reset.")
            return
        if len(new_message) >= 1500:
            await ctx.send("Sorry, but the message must be less than 1500 characters.")
            return
        await self.config.leaving_message.set(new_message)
        await ctx.tick()

    @falx.command(name="autoremove")
    async def falx_change_autoremove(self, ctx: commands.Context, activate: bool):
        """
        Tell if Falx should remove the guild from whitelist when leaving the guild.

        By default `True`
        """
        await self.config.autoremove.set(activate)
        await ctx.send(
            "Done. I will now remove guilds from Falx when leaving."
            if activate
            else "Done. I will no longer remove whitelisted guild from Falx when leaving."
        )

    @falx.command(name="enable")
    async def falx_enable(self, ctx: commands.Context, activate: bool):
        """
        Enable or disable Falx.
        """
        if self.is_enabled == activate:
            await ctx.send(f"Falx is already {'enabled' if activate else 'disabled'}.")
            return
        self.is_enabled = activate
        await self.config.enabled.set(activate)
        await ctx.send("Done. Falx is now enabled." if activate else "Done. Falx is now disabled.")
