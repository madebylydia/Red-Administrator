import json
from typing import Dict, List, Optional, Union

from redbot.core.utils.chat_formatting import text_to_file
from redbot.vendored.discord.ext import menus

from .typehint import UserInfosResult


class MembersPage(menus.ListPageSource):
    def __init__(self, data, *, json: Optional[List[dict]] = None):
        self.__cache_edit: Dict[int, bool] = {}
        self.__was_initialized: bool = False
        self.__json: Optional[Dict[str, Union[List[dict], str]]] = json
        super().__init__(data, per_page=1)

    async def format_page(self, menu: menus.MenuPages, entry: UserInfosResult):
        if menu.current_page not in self.__cache_edit:
            foot_but_not_the_sport_just_the_footer = entry["embed"].footer
            entry["embed"].set_footer(
                text=foot_but_not_the_sport_just_the_footer.text
                + f"\nPage {menu.current_page + 1}/{self.get_max_pages()}",
                icon_url=foot_but_not_the_sport_just_the_footer.icon_url,
            )
            self.__cache_edit[menu.current_page] = True
        if self.__was_initialized:
            return {"content": entry["content"], "embed": entry["embed"]}
        try:
            if self.__json:
                return {
                    "content": entry["content"],
                    "embed": entry["embed"],
                    "file": text_to_file(self.__json["data"], filename=self.__json["filename"]),
                }
            else:
                return {"content": entry["content"], "embed": entry["embed"], "file": None}
        finally:
            self.__was_initialized = True
