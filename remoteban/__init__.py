from .remoteban import RemoteBan


def setup(bot):
    cog = RemoteBan(bot)
    bot.add_cog(cog)
