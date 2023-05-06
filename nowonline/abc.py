from abc import (  # Importing ABCMeta in an effort to use it in other files
    ABC,
    abstractmethod,
)

from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.commands import Cog

from .no_class import Event


class MixinMeta(ABC):
    bot: Red
    config: Config

    def __init__(self, *_args):
        self.bot: Red
        self.config: Config

    @abstractmethod
    async def declare_event(self, event: Event):
        pass


class CompositeMetaClass(type(Cog), type(ABC)):
    """
    Allows the metaclass used for proper type detection to coexist with discord.py's metaclass.
    Credit to https://github.com/Cog-Creators/Red-DiscordBot for all the logic.
    """

    pass
