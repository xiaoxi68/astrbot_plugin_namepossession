import random

from astrbot.api import logger


class NamePossessionService:
    """Domain logic for name possession on QQ (OneBot/Napcat).

    This service depends on the client object that exposes `api.call_action`.
    """

    def __init__(self):
        pass

    async def get_login_info(self, client) -> dict | None:
        try:
            info = await client.api.call_action("get_login_info")
            return info
        except Exception as e:
            logger.error(f"get_login_info failed: {e}")
            return None

    async def get_group_list(self, client) -> list:
        try:
            groups = await client.api.call_action("get_group_list")
            return groups or []
        except Exception as e:
            logger.error(f"get_group_list failed: {e}")
            return []

    async def get_group_member_list(self, client, group_id: int) -> list:
        try:
            members = await client.api.call_action(
                "get_group_member_list", group_id=group_id, no_cache=True
            )
            return members or []
        except Exception as e:
            logger.error(f"get_group_member_list failed: {e}")
            return []

    async def set_group_card(
        self, client, group_id: int, user_id: int, card: str
    ) -> bool:
        try:
            await client.api.call_action(
                "set_group_card", group_id=group_id, user_id=user_id, card=card
            )
            return True
        except Exception as e:
            logger.error(f"set_group_card failed: {e}")
            return False

    async def poke_user(self, client, group_id: int, user_id: int) -> None:
        try:
            await client.api.call_action(
                "group_poke", group_id=group_id, user_id=user_id
            )
        except Exception as e:
            logger.warning(f"group_poke failed: {e}")

    @staticmethod
    def _display_name_of(member: dict) -> str:
        card = (member or {}).get("card")
        nickname = (member or {}).get("nickname")
        return (card or nickname or "群友").strip()

    async def random_possess(
        self, client, group_id: int, self_id: int
    ) -> tuple[int, str] | None:
        """Pick a random member and set bot's group card to theirs.

        Returns (user_id, name) if succeeded.
        """
        members = await self.get_group_member_list(client, group_id)
        if not members:
            logger.info(f"no members found in group {group_id}")
            return None

        # Exclude bot self and members without id
        candidates = [m for m in members if int(m.get("user_id", 0)) != int(self_id)]
        if not candidates:
            return None

        target = random.choice(candidates)
        target_id = int(target.get("user_id"))
        target_name = self._display_name_of(target)

        if not await self.set_group_card(client, group_id, int(self_id), target_name):
            return None

        # log after successful rename
        logger.info(
            f"namepossession: set_group_card success group={group_id} self={self_id} "
            f"new_card='{target_name}' from user={target_id}"
        )

        await self.poke_user(client, group_id, target_id)
        return target_id, target_name
