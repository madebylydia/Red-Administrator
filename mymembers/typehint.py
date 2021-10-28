import json
from typing import TypedDict

import discord


class UserInfosResult(TypedDict, total=False):
    content: str
    embed: discord.Embed
    json: str
