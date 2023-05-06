from .remoteban import RemoteBan


async def setup(bot):
    cog = RemoteBan(bot)
    await bot.add_cog(cog)
