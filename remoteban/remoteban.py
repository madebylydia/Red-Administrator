import asyncio
import base64
from datetime import datetime
from typing import Dict, List, Literal, Optional, TypedDict, Union

import discord
from discord import embeds
from discord.errors import HTTPException
from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.modlog import create_case
from redbot.core.utils.chat_formatting import bold, inline, warning
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu
from redbot.core.utils.mod import get_audit_reason
from redbot.core.utils.predicates import MessagePredicate

from .utils import allowed_to_ban


class GlobalConfig(TypedDict):
    servers: List[int]
    allowed_users: List[int]
    send_modlog: bool


class TypedGuildList(TypedDict):
    guild_id: int
    guild_name: str
    guild_owner: discord.Member
    can_ban: bool


class UserTranslator(TypedDict):
    users: List[Union[discord.User, discord.Member]]
    not_found: List[int]
    errored: Dict[int, HTTPException]


class GuildBannableResult(TypedDict):
    all: List[int]
    bannable: List[discord.Guild]
    missing_permission: List[discord.Guild]
    not_found: List[int]


DEFAULT_GLOBAL_CONFIG = GlobalConfig(servers=[], allowed_users=[], send_modlog=False)


def yes_or_no(value: bool):
    return "Yes" if value else "No"


def tick(text: str):
    return f"✔️ {text}"


def yes_or_no_emoji(value: bool):
    return "✔️" if value else "❌"


class UserCase:
    def __init__(self, user: Union[discord.User, discord.Member], action: Literal["unban", "ban"]):
        self.user = user
        self.action: Literal["unban", "ban"] = action
        self.guilds_banned_or_unbanned: List[discord.Guild] = []
        self.fails: Dict[discord.Guild, Exception] = {}

    def banned_or_unbanned_in(self, guild: discord.Guild):
        self.guilds_banned_or_unbanned.append(guild)

    def failed_in(self, guild: discord.Guild, exception: Exception):
        self.fails[guild] = exception

    def to_embed(self):
        description = f"{'Banned' if self.action == 'ban' else 'Unbanned'} in {len(self.guilds_banned_or_unbanned)} guild(s), failed in {len(self.fails)} guild(s).\n\n{bold('Results')}\n"
        description += "\n".join(
            [f"✔️ {guild.name} ({guild.id})" for guild in self.guilds_banned_or_unbanned]
        )
        if self.fails:
            description += "\n" + "\n".join(
                [
                    f"❌ In {guild[0].name} ({guild[0].id}): {str(guild[1])}"
                    for guild in self.fails.items()
                ]
            )
        embed = discord.Embed(
            color=discord.Colour.dark_red(),
            title=f"{'Ban' if self.action == 'ban' else 'Unban'} Result For {str(self.user)}",
            description=description,
        )
        return embed


class RemoteBan(commands.Cog):
    """
    Ban users remotely. Available to owner(s) of the bot only.
    """

    def __init__(self, bot: Red, *args, **kwargs):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=5578554655885, force_registration=True)
        self.config.register_global(**DEFAULT_GLOBAL_CONFIG)
        self.__has_accepted_conditions: bool = False
        super().__init__(*args, **kwargs)

    async def translate_users(self, users_list: Union[discord.User, int]) -> UserTranslator:
        not_found = []
        users = []
        errored = {}
        for user in users_list:
            if isinstance(user, (discord.User, discord.Member)):
                users.append(user)
                continue
            try:
                fetched_user = await self.bot.get_or_fetch_user(user)
                # Preparing for https://github.com/Cog-Creators/Red-DiscordBot/pull/4838
                if not fetched_user:
                    not_found.append(user)
                else:
                    users.append(fetched_user)
            except discord.NotFound:
                not_found.append(user)
            except discord.HTTPException as error:
                errored[user] = error
        return UserTranslator(users=users, not_found=not_found, errored=errored)

    def check_ban_permission_in_guild(self, guild: discord.Guild) -> Optional[bool]:
        return guild.me.guild_permissions.ban_members

    async def start_interactive_questionning(self, ctx: commands.Context) -> bool:
        await ctx.author.send(
            "Before we allow you to add external users from being able, we need to tell you about consequences.\n"
            "The good side of letting others users using `rban` is to do the same thing as you (Apart from setting up the cog), the bad side is that you have to trust the persons you will add.\n"
            "Respecting sudo's warning, we boils down to these three things:\n\n"
            "#1) Respect the privacy of others.\n"
            "#2) Think before you type.\n"
            "#3) With great power comes great responsibility.\n\n"
            'We want you to understand that adding external users can be a problem, and you do not want bad things to happen. We made the cog as "legit" as possible to try to make things as non-destructive as possible while still keeping the main goal.\n'
            f"Before adding any external users, {bold('you need to enter a key pass')} to be sure you have understood the risks.\n\n"
            f"{bold('To obtain the key pass, please contact:')} {inline('Capt. Pred#0495')}."
        )
        await ctx.author.send(
            bold("ENTER KEY PASS - YOU HAVE 5 MINUTES BEFORE YOU HAVE TO REEXECUTE THE COMMAND.")
        )
        check_ctx = MessagePredicate.same_context(channel=ctx.author.dm_channel, user=ctx.author)
        try:
            message = await ctx.bot.wait_for("message", check=check_ctx, timeout=300)
        except asyncio.TimeoutError:
            await ctx.author.send(bold("NO KEY PASS RECEIVED - REEXECUTE THE COMMAND."))
            return False
        if message.content == base64.b64decode(
            b"SSBoZXJlYnkgYWxsb3cgdG8gYWRkIGV4dGVybmFsIHVzZXJzIHRvIHRoZSBjb2csIFJlbW90ZUJhbiwgYW5kIGFncmVlIHRvIGJlaW5nIHVuYWJsZSB0byBibGFtZSB0aGUgY3JlYXRvciBvZiB0aGUgY29nIFJlbW90ZUJhbiBmb3IgZGFtYWdlIGNhdXNlZCBieSB0aGUgY29nIHRvIERpc2NvcmQgc2VydmVycy4="
        ).decode("utf-8"):
            self.__has_accepted_conditions = True
            await ctx.author.send(
                bold(
                    "KEY PASS ACCEPTED - YOU CAN NOW USE EXTERNAL USERS MANAGER COMMANDS AS YOU LIKE UNTIL BOT RESTART."
                )
            )
            return True
        else:
            await ctx.author.send(bold("KEY PASS INVALID"))
            return False

    async def add_server(self, ctx_author: discord.User, guild: Union[int, discord.Guild]):
        if not isinstance(guild, discord.Guild):
            guild = self.bot.get_guild(guild)
        if not guild:
            raise commands.UserFeedbackCheckFailure(
                "I am not in this guild. Make me join it first."
            )
        if not guild.channels:
            raise LookupError("Cannot check permissions in guild - no channels are available.")
        if not self.check_ban_permission_in_guild(guild):
            raise commands.UserFeedbackCheckFailure(
                "I do not have the necessary permissions to ban users in this guild."
            )
        if guild.owner != ctx_author:
            if not ctx_author.guild_permissions.administrator:
                raise commands.UserFeedbackCheckFailure(
                    "You are not owning this guild or you are not an administrator. I cannot let you do that."
                )
        async with self.config.servers() as guilds:
            if guild.id in guilds:
                raise commands.UserFeedbackCheckFailure("This guild is already registered.")
            guilds.append(guild.id)
        return True

    async def add_user(self, user: int):
        async with self.config.allowed_users() as users:
            if user in users:
                return False
            users.append(user)
        return True

    async def remove_user(self, user: int):
        async with self.config.allowed_users() as users:
            if user not in users:
                return False
            users.remove(user)
        return True

    async def remove_server(self, guild: Union[int, discord.Guild]):
        if isinstance(guild, discord.Guild):
            guild_id = guild.id
        else:
            guild_id = guild
        async with self.config.servers() as guilds:
            if guild not in guilds:
                raise commands.UserFeedbackCheckFailure("This guild is not registered.")
            guilds.remove(guild_id)
        return True

    async def obtain_guilds_where_bannable(self) -> GuildBannableResult:
        guilds_config = await self.config.servers()
        guilds = []
        not_found_guilds = []
        for guild in guilds_config:
            if fetched_guild := self.bot.get_guild(guild):
                guilds.append(fetched_guild)
            else:
                not_found_guilds.append(guild)
        guilds_without_ban_permissions: List[discord.Guild] = [
            guild for guild in guilds if not self.check_ban_permission_in_guild(guild)
        ]
        guilds = [guild for guild in guilds if guild not in guilds_without_ban_permissions]
        return {
            "all": guilds_config,
            "bannable": guilds,
            "missing_permission": guilds_without_ban_permissions,
            "not_found": not_found_guilds,
        }

    async def ban_users(
        self,
        users: UserTranslator,
        guilds: GuildBannableResult,
        ban_author: discord.User,
        reason: str,
    ) -> List[UserCase]:
        create_modlog_case = await self.config.send_modlog()
        users_cases: List[UserCase] = []

        for user in users["users"]:
            user_case = UserCase(user, "ban")
            users_cases.append(user_case)  # I love immutable objects... :')
            for guild in guilds:
                try:
                    await guild.ban(
                        user, reason=get_audit_reason(ban_author, reason=reason, shorten=True)
                    )
                    if create_modlog_case:
                        await create_case(
                            self.bot,
                            guild,
                            datetime.now(),
                            "ban",
                            user,
                            ban_author,
                            get_audit_reason(ban_author, reason=reason),
                        )
                    user_case.banned_or_unbanned_in(guild)
                except (discord.HTTPException, discord.Forbidden) as error:
                    user_case.failed_in(guild, error)
        return users_cases

    @staticmethod
    def get_all_embeds(
        users_cases: List[UserCase],
        fetched_users: UserTranslator,
        guilds_removed: Optional[List[str]],
        action: Literal["unban", "ban"],
    ) -> List[discord.Embed]:
        embeds = []
        wording = "unban" if action == "unban" else "ban"
        total_fails = sum([len(user.fails) for user in users_cases])
        total_success = sum([len(user.guilds_banned_or_unbanned) for user in users_cases])
        first_embed = discord.Embed(
            color=discord.Color.dark_orange(),
            title="Summary",
            description=(
                "A total of {users_count} user(s) have been processed.\n\n"
                "A total of {total_success} {wording}, for a total of {total_fails} failure(s).\n"
                "A more in depth result is available in this menu."
            ).format(
                users_count=bold(str(len(fetched_users["users"]))),
                total_success=bold(str(total_success)),
                wording=bold(str(wording)),
                total_fails=bold(str(total_fails)),
            ),
        )
        if guilds_removed:
            first_embed.add_field(
                name=warning("One or more guilds have been removed"),
                value=(
                    "These guilds did not process bans because I am missing permissions to ban users or an error happened:\n"
                    + "\n".join([f"- {guild}" for guild in guilds_removed])
                ),
            )
        else:
            first_embed.add_field(
                name=tick("All guilds have processed bans"),
                value="No errors related to guild's permissions occured when banning users in guilds.",
            )
        embeds.append(first_embed)
        for user in users_cases:
            embeds.append(user.to_embed())
        return embeds

    async def unban_users(
        self,
        users: UserTranslator,
        guilds: GuildBannableResult,
        unban_author: discord.User,
        reason: str,
    ) -> List[UserCase]:
        create_modlog_case = await self.config.send_modlog()
        users_cases: List[UserCase] = []

        for user in users["users"]:
            user_case = UserCase(user, "unban")
            users_cases.append(user_case)  # I love immutable objects... :')
            for guild in guilds:
                try:
                    await guild.unban(
                        user, reason=get_audit_reason(unban_author, reason, shorten=True)
                    )
                    if create_modlog_case:
                        await create_case(
                            self.bot,
                            guild,
                            datetime.now(),
                            "unban",
                            user,
                            unban_author,
                            get_audit_reason(unban_author, reason=reason),
                        )
                    user_case.banned_or_unbanned_in(guild)
                except (discord.HTTPException, discord.Forbidden) as error:
                    user_case.failed_in(guild, error)
        return users_cases

    @commands.group(name="remoteban", aliases=["rban"])
    @allowed_to_ban()
    async def rban(self, ctx: commands.Context):
        """
        Base command for remote banning.
        """

    @rban.command(name="ban")
    async def ban_user(
        self,
        ctx: commands.Context,
        users: commands.Greedy[Union[discord.User, int]] = None,
        *,
        reason: str = "No reason providen",
    ):
        """
        Ban an user from set guilds.
        """
        if not users:
            return await ctx.send_help()
        async with ctx.typing():
            guilds = await self.obtain_guilds_where_bannable()
            fetched_users = await self.translate_users(users)
            result = await self.ban_users(fetched_users, guilds["bannable"], ctx.author, reason)
        guilds_not_processed = [str(guild.id) for guild in guilds["missing_permission"]] + [
            str(guild) for guild in guilds["not_found"]
        ]
        embeds = self.get_all_embeds(result, fetched_users, guilds_not_processed, "ban")
        await menu(ctx, embeds, DEFAULT_CONTROLS, timeout=60)

    @rban.command(name="unban")
    async def unban_user(
        self,
        ctx: commands.Context,
        users: commands.Greedy[Union[discord.User, int]] = None,
        *,
        reason: str = "No reason providen",
    ):
        """
        Unban an user from set guilds.
        """
        if not users:
            return await ctx.send_help()
        async with ctx.typing():
            guilds = await self.obtain_guilds_where_bannable()
            fetched_users = await self.translate_users(users)
            result = await self.unban_users(fetched_users, guilds["bannable"], ctx.author, reason)
        guilds_not_processed = [str(guild.id) for guild in guilds["missing_permission"]] + [
            str(guild) for guild in guilds["not_found"]
        ]
        embeds = self.get_all_embeds(result, fetched_users, guilds_not_processed, "unban")
        await menu(ctx, embeds, DEFAULT_CONTROLS, timeout=60)

    @rban.group(name="set")
    @commands.is_owner()
    async def settings(self, ctx: commands.Context):
        """
        Change settings of the cog.
        """

    @settings.command(name="addserver", aliases=["addserv", "as", "mk"])
    async def add_server_in_remoteban(self, ctx: commands.Context, guild: int):
        """
        Register a guild where remote ban should apply bans.
        """
        if await self.add_server(ctx.author, guild):
            await ctx.send("Success, server will now execute remote bans.")

    @settings.command(name="listservers", aliases=["listserv", "ls"])
    async def list_servers_in_remoteban(self, ctx: commands.Context):
        """
        List registered guilds.
        """
        guilds = await self.config.servers()
        guild_obj: List[TypedGuildList] = []
        for guild_id in guilds:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                await self.remove_server(guild)
                continue
            can_ban = guild.me.guild_permissions.ban_members
            guild_obj.append(
                TypedGuildList(
                    guild_id=guild_id,
                    guild_name=guild.name,
                    guild_owner=guild.owner,
                    can_ban=can_ban,
                )
            )
        await ctx.send(
            (
                "These guilds will remote ban users you want to ban:\n"
                "{guilds}".format(
                    guilds="\n".join(
                        [
                            f"{g['guild_name']} ({g['guild_id']}) - Owned by {g['guild_owner']} / Bot has permission to ban: {g['can_ban']}"
                            for g in guild_obj
                        ]
                    )
                )
            )
            if guild_obj
            else "There is no guilds registered."
        )

    @settings.command(name="removeserver", aliases=["removeserv", "rms", "rm"])
    async def remove_server_in_remoteban(self, ctx: commands.Context, guild: int):
        """
        Remove a registered guild where remote ban is applying bans.
        """
        if await self.remove_server(guild):
            await ctx.send("Success, server will no longer execute remote bans.")

    @settings.command(name="modlogentry")
    async def set_modlog_entries_on_ban(self, ctx: commands.Context, *, state: bool = None):
        """
        Determine if a modlog entry should be created when banning a member.
        """
        if state is None:
            return await ctx.send(
                "Create a modlog entry on ban: " + yes_or_no(await self.config.send_modlog())
            )
        await self.config.send_modlog.set(state)
        await ctx.tick()

    @settings.group(name="users", aliases=["u", "user"])
    async def user_manager(self, ctx: commands.Context):
        """
        Decide which users has access to remote ban.

        We trust you are using this command because you have admins wanting to use `rban`.
        However, we try to boils down to these three things:
            #1) Respect the privacy of others.
            #2) Think before you type.
            #3) With great power comes great responsibility.
        """

    @user_manager.command(name="add")
    async def add_external_users_to_remoteban(self, ctx: commands.Context, *, user_id: int):
        """
        Add an external user being able to run `rban` commands.
        """
        if not self.__has_accepted_conditions:
            if not await self.start_interactive_questionning(ctx):
                return
        if await self.add_user(user_id):
            return await ctx.send(
                f"{ctx.author.mention} User ID added; Remember, With great power comes great responsibility."
            )
        else:
            await ctx.send(f"This user has already been added.")

    @user_manager.command(name="list", aliases=["ls"])
    async def list_external_users_in_remoteban(self, ctx: commands.Context):
        """
        List all external users.
        """
        if not self.__has_accepted_conditions:
            if not await self.start_interactive_questionning(ctx):
                return
        users = await self.config.allowed_users()
        msg_user = ""
        for user in users:
            fetched_user = self.bot.get_user(user)
            msg_user += (
                f"{user} - {str(fetched_user) if fetched_user else 'User cannot be found'}\n"
            )
        await ctx.send(
            f"These users have been allowed:\n{msg_user}"
            if users
            else "No external users were allowed."
        )

    @user_manager.command(name="remove", aliases=["rm"])
    async def remove_external_users_to_remoteban(self, ctx: commands.Context, *, user_id: int):
        """
        Remove an external user from being able to run `rban` commands.
        """
        if not self.__has_accepted_conditions:
            if not await self.start_interactive_questionning(ctx):
                return
        if await self.remove_user(user_id):
            return await ctx.send(f"{ctx.author.mention} User ID removed.")
        else:
            await ctx.send(f"This user is not allowed already.")

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        async with self.config.servers() as guilds:
            if guild.id in guilds:
                guilds.remove(guild.id)
