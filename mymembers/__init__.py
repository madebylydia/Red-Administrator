from redbot.core.bot import Red

from .mymembers import MyMembers


def setup(bot: Red):
    cog = MyMembers(bot)
    bot.add_cog(cog)
