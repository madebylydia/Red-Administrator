from redbot.core.commands import Cog

from .abc import ABCMeta, MixinMeta
from .no_class import EVENT_TYPE, Event


class Events(MixinMeta, metaclass=ABCMeta):
    # Listener: On Connect/Ready

    @Cog.listener()
    async def on_connect(self):
        event = Event(EVENT_TYPE.ON_CONNECT, self.bot)
        await self.declare_event(event)

    @Cog.listener()
    async def on_ready(self):
        event = Event(EVENT_TYPE.ON_READY, self.bot)
        await self.declare_event(event)

    @Cog.listener()
    async def on_shard_connect(self, shard_id: int):
        event = Event(EVENT_TYPE.ON_SHARD_CONNECT, self.bot, shard_id=shard_id)
        await self.declare_event(event)

    @Cog.listener()
    async def on_shard_ready(self, shard_id: int):
        event = Event(EVENT_TYPE.ON_SHARD_READY, self.bot, shard_id=shard_id)
        await self.declare_event(event)

    # Listener: On Resume/Resumed/Reconnect

    @Cog.listener()
    async def on_resumed(self):
        event = Event(EVENT_TYPE.ON_RESUMED, self.bot)
        await self.declare_event(event)

    @Cog.listener()
    async def on_shard_resumed(self, shard_id: int):
        event = Event(EVENT_TYPE.ON_SHARD_RESUMED, self.bot, shard_id=shard_id)
        await self.declare_event(event)

    # Listener: On Disconnect

    @Cog.listener()
    async def on_disconnect(self):
        event = Event(EVENT_TYPE.ON_DISCONNECT, self.bot)
        await self.declare_event(event)

    @Cog.listener()
    async def on_shard_disconnect(self, shard_id: int):
        event = Event(EVENT_TYPE.ON_SHARD_DISCONNECT, self.bot, shard_id=shard_id)
        await self.declare_event(event)
