import logging
from typing import Optional

from redbot.core import Config, commands
from redbot.core.bot import Red

from .abc import CompositeMetaClass
from .events import Events
from .no_class import Case, Event

DEFAULT_CASE_CONFIG = {}
DEFAULT_GUILD_CONFIG = {"channel": None, "ping_role": None}

Log = logging.getLogger("red.predeactor.nowonline")
Log.setLevel(logging.INFO)


class NowOnline(Events, commands.Cog, name="NowOnline", metaclass=CompositeMetaClass):
    def __init__(self, bot: Red):
        self.bot = bot
        self.config: Config = Config.get_conf(
            self,
            identifier=56462255452,
            force_registration=True,
            cog_name="NowOnline",
        )

        self.config.register_guild(**DEFAULT_GUILD_CONFIG)

        # I still would like to determine how to make things correct here before registering anything.
        # self.config.init_custom("case", 1)
        # self.config.register_custom("case", **DEFAULT_CASE_CONFIG)

        self._last_known_name: Optional[str] = None

    def find_bot_name(self):
        """
        Attempt to find bot's name when connecting. Useful for when the bot's is stil not
        connected and discord.py trigger an event without the name.
        """
        Log.debug("[find_bot_name] Attempting to find bot's name.")
        if self.bot.user:
            Log.debug(
                f"[cog_load] Found bot's name ({self.bot.user.name}), applying as last know name."
            )
            self._last_known_name = self.bot.user.name

    async def fetch_from_last_connect(self):
        """
        A function to call when we're reconnected to the gateway, so we can fetch all needed
        informations we might need to insert in the cache.
        """
        pass

    async def cog_load(self):
        Log.debug("[cog_load] Waiting until Red is connected to retrieve name.")
        await self.bot.wait_until_red_ready()
        Log.debug("[cog_load] Retrieving bot's name.")
        self.find_bot_name()

        Log.info("[cog_load] NowOnline is now loaded and available.")

    async def declare_event(self, event: Event):
        """
        Alert an ongoing event on the bot.
        """
        Log.debug(f"Declared event: {event.event_type}")
        if self.bot.is_ready:
            Log.warning("Red is not ready, waiting before sending event into channel.")
            await self.bot.wait_until_red_ready()
            Log.debug("Red is now ready.")
        
        await self.bot.get_channel(133251234164375552).send(embed=event.to_embed())

    def cog_unload(self):
        Log.info(f"[cog_unload] Is shard 0 closed: {self.bot.shards[0].is_closed()}.")

def setup(bot: Red):
    Log.info("Loading NowOnline...\n\t\t\tMade by Capt. Pred#0495 - Red-Administrator.")
    cog = NowOnline(bot)
    bot.add_cog(cog)
    bot.loop.create_task(cog.cog_load())
