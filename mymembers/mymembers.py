import json
from datetime import datetime
from typing import Dict, List

import discord
from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import (
    bold,
    error,
    humanize_list,
    inline,
    text_to_file,
    warning,
)
from redbot.vendored.discord.ext.menus import MenuPages

from .menu import MembersPage
from .typehint import UserInfosResult

DEFAULT_GUILD_CONFIG = {
    "channel": None,
    "enabled": False,
    "obtain_json": True,
    "timestamp_style": "F",
}


class TimestampConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> str:
        if argument not in ("t", "T", "d", "D", "f", "F", "R"):
            raise commands.BadArgument(
                "This argument is incorrect, it must be one of 't', 'T', 'd', 'D', 'f', 'F' or "
                "'R'."
            )
        return argument


class MyMembers(commands.Cog):
    """
    MyMembers - Obtain informations about your joining & leaving members!
    """

    def __init__(self, bot: Red, *args, **kwargs):
        self.bot = bot

        self.config: Config = Config.get_conf(
            self,
            identifier=8546153255,
            force_registration=True,
            cog_name="MyMembers",
            allow_old=False,
        )
        self.config.register_guild(**DEFAULT_GUILD_CONFIG)

        self._timestamp_cache: Dict[int, str] = {}

        super().__init__(*args, **kwargs)

    async def get_timestamp_value(self, time_obj: datetime, guild: discord.Guild) -> str:
        """
        Return the timestamp with the correct form that the guild want.
        """
        timestamp_style = self._timestamp_cache.get(guild.id)
        if not timestamp_style:
            timestamp_style = await self.config.guild(guild).timestamp_style()
            self._timestamp_cache[guild.id] = timestamp_style
        return f"<t:{round(time_obj.timestamp())}:{timestamp_style}>"

    @staticmethod
    def get_guild_dict(guild: discord.Guild, user: discord.Member) -> dict:
        """
        Return information about a guild under the form of a dict.

        It is prohibited to return information about others users from this guild, exception for
        the guild owner and the bot itself, if necessary.
        """
        user_in_guild = guild.get_member(user.id)
        voice_region = guild.region
        if isinstance(voice_region, discord.enums.VoiceRegion):
            voice_region = voice_region.name
        if premium_role := guild.premium_subscriber_role:
            premium_role = premium_role.name
        if afk_channel := guild.afk_channel:
            afk_channel = afk_channel.name
        if rules_channel := guild.rules_channel:
            rules_channel = rules_channel.name
        if system_channel := guild.system_channel:
            system_channel = system_channel.name
        if public_updates_channel := guild.public_updates_channel:
            public_updates_channel = public_updates_channel.name
        return {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "name": guild.name,
            "id": guild.id,
            "created_at": guild.created_at.isoformat(timespec="seconds"),
            "description": guild.description,
            # I want to kill myself really hard...
            "icon_url": str(guild.icon_url),
            "icon_url_as_png": str(guild.icon_url_as(format="png")),
            "icon_url_as_jpg": str(guild.icon_url_as(format="jpg")),
            "banner_url": str(guild.banner_url) if guild.banner_url else None,
            "banner_url_as_png": str(guild.banner_url_as(format="png"))
            if guild.banner_url
            else None,
            "banner_url_as_jpg": str(guild.banner_url_as(format="jpg"))
            if guild.banner_url
            else None,
            "discovery_splash_url": str(guild.discovery_splash_url)
            if guild.discovery_splash_url
            else None,
            "discovery_splash_url_as_png": str(guild.discovery_splash_url_as(format="png"))
            if guild.discovery_splash_url
            else None,
            "discovery_splash_url_as_jpg": str(guild.discovery_splash_url_as(format="jpg"))
            if guild.discovery_splash_url
            else None,
            "splash_url": str(guild.splash_url) if guild.splash_url else None,
            "splash_url_as_png": str(guild.splash_url_as(format="png"))
            if guild.splash_url
            else None,
            "splash_url_as_jpg": str(guild.splash_url_as(format="jpg"))
            if guild.splash_url
            else None,
            "is_large_guild": guild.large,
            "preferred_locale": guild.preferred_locale,
            "voice_region": voice_region,
            "mfa_level": guild.mfa_level,
            "explicit_content_filter": guild.explicit_content_filter.name,
            "verification_level": guild.verification_level.name,
            "features": guild.features,
            "default_notifications": guild.default_notifications.name,
            "bitrate_limit": guild.bitrate_limit,
            "premium_role": premium_role,
            "premium_total_subscribers": guild.premium_subscription_count,
            "premium_actual_tier": guild.premium_tier,
            "filesize_limit_in_bytes": float(guild.filesize_limit),
            "categories_total": len(guild.categories),
            "channels_total": len(guild.channels),
            "channels_text_total": len(guild.text_channels),
            "channels_voice_total": len(guild.voice_channels),
            "channels_stage_total": len(guild.stage_channels),
            "afk_channel": afk_channel,
            "rules_channel": rules_channel,
            "system_channel": system_channel,
            "public_updates_channel": public_updates_channel,
            "roles_total": len(guild.roles),
            "emojis_total": len(guild.emojis),
            "emojis_limit": guild.emoji_limit,
            "members_count": guild.member_count,
            "max_members": guild.max_members,
            "max_presences": guild.max_presences,
            "max_video_channel_users": guild.max_video_channel_users,
            "guild_is_unavailable": not guild.unavailable,
            "bot_chuncked_guild": guild.chunked,
            "bot_joined_at": guild.me.joined_at.isoformat(timespec="seconds"),
            "user_joined_at": user_in_guild.joined_at.isoformat(timespec="seconds"),
            "user_has_nickname": bool(user.nick),
            "user_display_name": user.display_name,
            "user_avatar_url": str(user.avatar_url),
            "user_avatar_url_as_png": str(user.avatar_url_as(format="png")),
            "user_avatar_url_as_jpg": str(user.avatar_url_as(format="jpg")),
            "user_permissions_in_guild": user.guild_permissions.value,
            "user_is_guild_owner": user.guild.owner_id == user.id,
            "user_has_boosted_guild_since": user.premium_since.isoformat(timespec="seconds")
            if user.premium_since
            else None,
        }

    def get_member_dict(self, user: discord.Member) -> dict:
        try:
            guilds_lookup = user.mutual_guilds
        except AttributeError:
            # Edge case where the user requets infos for the bot itself.
            guilds_lookup = self.bot.guilds
        return {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "user": str(user),
            "name": user.name,
            "id": user.id,
            "discriminator": user.discriminator,
            "has_nickname": bool(user.nick),
            "display_name": user.display_name,
            "is_bot": user.bot,
            "is_system": user.system,
            "is_avatar_animated": user.is_avatar_animated(),
            "default_avatar": str(user.default_avatar_url),
            "avatar_url": str(user.avatar_url),
            "avatar_url_as_png": str(user.avatar_url_as(format="png")),
            "avatar_url_as_jpg": str(user.avatar_url_as(format="jpg")),
            "created_at": user.created_at.isoformat(timespec="seconds"),
            "joined_at": user.joined_at.isoformat(timespec="seconds"),
            "is_guild_owner": user.guild.owner_id == user.id,
            "permissions_in_guild": user.guild_permissions.value,
            "is_pending_on_membership_screening": user.pending,
            "has_boosted_guild_since": user.premium_since.isoformat(timespec="seconds")
            if user.premium_since
            else None,
            "mutual_guilds_with_bot": [
                self.get_guild_dict(guild, user) for guild in guilds_lookup
            ],
            "status": user.raw_status,
            "status_on_desktop": user.desktop_status.name,
            "status_on_mobile": user.mobile_status.name,
            "status_on_web": user.web_status.name,
            "user_flags": user.public_flags.all(),
        }

    async def get_info_for_member(
        self, bot: Red, member: discord.Member, get_json: bool
    ) -> UserInfosResult:
        try:
            guilds_lookup = member.mutual_guilds
        except AttributeError:
            # Edge case where the user requets infos for the bot itself.
            guilds_lookup = self.bot.guilds
        user_flags = (
            humanize_list(
                [f"{inline(val.name)}" for val in member.public_flags.all()],
                style="standard-short",
            )
            if member.public_flags.all()
            else "None"
        )
        footer_text = (
            f"Generated by {str(bot.user)} at {datetime.now().isoformat(timespec='seconds')}\n"
            f"Contain JSON informations: {str(get_json)}"
        )
        msg_content = (
            f"User has joined the guild at: {await self.get_timestamp_value(member.joined_at, member.guild) if member.joined_at else inline('CANNOT DETERMINE DATE')}\n"
            f"User was created at: {await self.get_timestamp_value(member.created_at, member.guild)}\n"
            "Difference between guild joined/account creation "
            f"{bold(str((member.joined_at - member.created_at).days)) if member.joined_at else inline('CANNOT DETERMINE DATE')} days.\n"
            f"Since today, user is in the guild since {bold(str((datetime.now() - member.joined_at).days)) if member.joined_at else inline('CANNOT DETERMINE DATE')} days.\n"
        )
        user_information = self.get_member_dict(member) if get_json else None
        desc = (
            f"Status: {member.raw_status.title()}\nHas a nickname: {bool(member.nick)}\n"
            f"Display name: {member.display_name}\nUser flags: {user_flags}"
        )
        embed = discord.Embed(
            color=member.color,
            title=f"Information for {str(member)} (ID: {member.id})",
            description=desc,
        )
        embed.set_thumbnail(url=member.avatar_url)
        embed.add_field(name="Total of shared guilds", value=str(len(guilds_lookup)))
        embed.add_field(name="Is a bot", value=str(member.bot))
        embed.add_field(name="Is system", value=member.system)
        embed.add_field(name="Has an animated avatar", value=member.is_avatar_animated())
        embed.add_field(name="Is pending on Membership Screening", value=str(member.pending))
        if member.premium_since:
            embed.add_field(
                name="Guild boosted since",
                value=await self.get_timestamp_value(member.premium_since, member.guild),
            )
        embed.add_field(
            name="Guild permissions",
            value=(
                humanize_list(
                    [
                        inline(str(perm[0].title().replace("_", " ")))
                        for perm in member.guild_permissions
                        if perm[1]
                    ]
                )
                + f" - Value: {bold(str(member.guild_permissions.value))}"
            )
            if not member.guild_permissions.administrator
            else f"{inline('Administrator')} - Value: {bold(str(member.guild_permissions.value))}",
        )
        embed.add_field(name="Is guild owner", value=str(member.guild.owner_id == member.id))
        embed.set_footer(icon_url=str(bot.user.avatar_url), text=footer_text)
        return UserInfosResult(
            content=msg_content,
            embed=embed,
            json=json.dumps(user_information, sort_keys=True, indent=2) if get_json else None,
        )

    @commands.group(name="mymembers", aliases=["mm", "mym"])
    @commands.admin()
    async def mymembers(self, ctx: commands.Context):
        """
        MyMembers base command.
        """

    @mymembers.command(name="obtain", aliases=["get"])
    async def cmd_get_user_info(
        self,
        ctx: commands.Context,
        users: commands.Greedy[discord.Member],
        include_json: bool = False,
    ):
        """
        Obtain information about an user from this guild.
        """
        to_del = await ctx.send("Please wait, getting data...")
        embeds: List[UserInfosResult] = []
        for user in users:
            embeds.append(await self.get_info_for_member(ctx.bot, user, include_json))
        if len(embeds) > 1:
            # We must process JSON objects and assemble them together, for the sake of message
            # editing when we will use the menu
            total_data = {
                "data": [],
                "filename": f"report-from-{str(self.bot.user)}-to-{str(ctx.author)}-at-{datetime.now().isoformat(timespec='seconds')}.json",
            }
            if include_json:
                for user_data in embeds:
                    json_as_string = user_data["json"]
                    json_as_dict = json.loads(json_as_string)
                    total_data["data"].append(json_as_dict)
                total_data = json.dumps(total_data, sort_keys=True, indent=2)

            menu = MenuPages(
                MembersPage(embeds, json=total_data), timeout=300, delete_message_after=True
            )
            await to_del.delete()
            await menu.start(ctx)
        else:
            if include_json:
                embeds[0]["file"] = text_to_file(
                    embeds[0]["json"],
                    filename=f"report-from-{str(self.bot.user)}-to-{str(ctx.author)}-at-{datetime.now().isoformat(timespec='seconds')}.json",
                )
            del embeds[0]["json"]
            await to_del.delete()
            await ctx.send(**embeds[0])

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        config = await self.config.guild(member.guild).all()
        if not config["enabled"] or (not config["channel"]):
            return
        chan = self.bot.get_channel(config["channel"])
        if not chan:
            return
        infos = await self.get_info_for_member(self.bot, member, config["obtain_json"])
        if config["obtain_json"]:
            infos["file"] = text_to_file(
                infos["json"],
                filename=f"report-for-guild-{member.guild.name}-at-{datetime.now().isoformat(timespec='seconds')}.json",
            )
        del infos["json"]
        infos["content"] = (
            "\N{WHITE HEAVY CHECK MARK} This user has joined the guild!\n\n"
        ) + infos["content"]
        await chan.send(**infos)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        config = await self.config.guild(member.guild).all()
        if not config["enabled"] or (not config["channel"]):
            return
        chan = self.bot.get_channel(config["channel"])
        if not chan:
            return
        infos = await self.get_info_for_member(self.bot, member, config["obtain_json"])
        if config["obtain_json"]:
            infos["file"] = text_to_file(
                infos["json"],
                filename=f"report-for-guild-{member.guild.name}-at-{datetime.now().isoformat(timespec='seconds')}.json",
            )
        del infos["json"]
        infos["content"] = warning("This user has left the guild!\n\n") + infos["content"]
        await chan.send(**infos)

    @mymembers.group(name="set")
    async def cmd_set(self, ctx: commands.Context):
        """
        Set parameters for MyMembers.
        """

    @cmd_set.command(name="settings", aliases=["dump"])
    async def cmd_settings(self, ctx: commands.Context):
        """
        Return the settings of MyMember.
        """
        config = await self.config.guild(ctx.guild).all()
        color = discord.Color.green() if config["enabled"] else discord.Color.red()
        embed = discord.Embed(
            color=color,
            title=f"Settings of MyMember for {ctx.guild.name}",
            description=(
                f"This is the settings of MyMember for guild {ctx.guild.name}, actually, "
                f"MyMembers is {bold('enabled') if config['enabled'] else bold('disabled')}, you "
                "can see more informations below."
            ),
        )
        embed.add_field(name="Enabled", value=config["enabled"])
        embed.add_field(name="Channel", value=config["channel"])
        if config["channel"]:
            fetched_channel = self.bot.get_channel(config["channel"])
            if fetched_channel:
                embed.set_field_at(
                    1, name="Channel", value=f"{fetched_channel.mention} ({fetched_channel.name})"
                )
        embed.add_field(name="Include JSON", value=config["obtain_json"])
        embed.add_field(name="Timestamp Style", value=inline(config["timestamp_style"]))
        await ctx.send(embed=embed)

    @cmd_set.command(
        name="channel", aliases=["c", "chan"]
    )  # The first one to piss me off with this alias get a free ban. Legit.
    async def cmd_set_channel(self, ctx: commands.Context, *, channel: discord.TextChannel):
        """
        Set the channel where informations are sent.
        """
        set_channel = await self.config.guild(ctx.guild).channel.set(channel.id)
        react = await ctx.tick()
        if not react:  # lmao who do that?
            await ctx.send("Channel has been set.")

    @cmd_set.command(name="enable", aliases=["e", "activate", "start"])
    async def cmd_set_enable(self, ctx: commands.Context, *, enable: bool):
        """
        Enable or disable MyMembers.
        """
        set_channel = await self.config.guild(ctx.guild).channel()
        if not set_channel:
            return await ctx.send(error("Please setup a channel before enabling MyMembers."))
        if not self.bot.get_channel(set_channel):
            return await ctx.send(
                error(f"I cannot find {bold(str(set_channel))}, please set another channel.")
            )
        await self.config.guild(ctx.guild).enabled.set(enable)
        await ctx.send("MyMembers is now enabled." if enable else "MyMembers is now disabled.")

    @cmd_set.command(name="includejson", aliases=["ij"])
    async def cmd_set_include_json(self, ctx: commands.Context, *, include_json: bool):
        await self.config.guild(ctx.guild).include_json.set(include_json)
        await ctx.send(
            "Success, a JSON file will now be sent when a member join/leave."
            if include_json
            else "Success, I will no longer include the JSON file when a member join/leave."
        )

    @cmd_set.command(name="timestampstyle", aliases=["ts", "timeset", "tss"])
    async def cmd_set_timestampstyle(
        self, ctx: commands.Context, *, timestamp: TimestampConverter
    ):
        """
        Set the timestamp style to show when showing information.

        You can use https://whatismyti.me/#/discordtimestamps to know what style to use.
        """
        await self.config.guild(ctx.guild).timestamp_style.set(timestamp)
        await ctx.send(
            f"Success, timestamp style has been set to the letter {inline(timestamp)}. (Example: "
            f"<t:0:{timestamp}>)"
        )
