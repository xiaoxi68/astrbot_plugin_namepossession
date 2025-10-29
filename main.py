import asyncio
import os
import random
from collections.abc import Iterable

from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register

from .service import NamePossessionService
from .storage import StateStore


@register(
    "namepossession",
    "薄暝",
    "随机夺舍 QQ 群友名字（群名）",
    "1.0.0",
)
class NamePossessionPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        base_dir = os.path.dirname(__file__)
        self.store = StateStore(os.path.join(base_dir, "data", "state.json"))
        self.service = NamePossessionService()
        self.config = config
        self._auto_task: asyncio.Task | None = None
        if self._is_auto_enabled():
            self._auto_task = asyncio.create_task(self._auto_loop())

    async def initialize(self):
        """Optional async initializer."""
        await self.store.initialize()

    async def terminate(self):
        if self._auto_task and not self._auto_task.done():
            self._auto_task.cancel()
            try:
                await self._auto_task
            except Exception:
                pass

    # ========== Commands ==========

    @filter.command("夺舍")
    async def possess_now(self, event: AstrMessageEvent):
        """在当前群随机“夺舍”——将机器人群名片改为随机群友名片/昵称。"""
        if event.get_platform_name() != "aiocqhttp":
            yield event.plain_result("仅支持 QQ(Napcat/OneBot) 平台使用该功能。")
            return

        group_id = event.message_obj.group_id
        if not group_id:
            yield event.plain_result("仅限群聊使用。")
            return

        if not self._is_group_allowed(int(group_id)):
            yield event.plain_result("当前群不在可用范围（名单规则）。")
            return

        # 获取 Napcat 客户端
        client = event.bot
        self_id = int(event.message_obj.self_id)

        ret = await self.service.random_possess(client, int(group_id), self_id)
        if not ret:
            yield event.plain_result("未能选择到合适的群友，稍后再试。")
            return

        target_id, target_name = ret
        await self.store.set_taken(str(self_id), str(group_id), target_id, target_name)
        yield event.plain_result(
            f"本次夺舍对象：{target_name}（{target_id}）。已修改机器人群名片。"
        )

    @filter.command("夺舍状态")
    async def possess_status(self, event: AstrMessageEvent):
        group_id = event.message_obj.group_id
        if not group_id:
            yield event.plain_result("仅限群聊使用。")
            return
        self_id = str(event.message_obj.self_id)
        taken = await self.store.get_taken(self_id, str(group_id))
        if not taken:
            yield event.plain_result("当前群暂无夺舍记录。")
            return
        yield event.plain_result(
            f"当前群最近一次夺舍对象：{taken['name']}（{taken['user_id']}）。"
        )

    # 自动开关通过配置项 auto_enabled 控制，不再提供手动指令

    # ========== Background loop ==========

    async def _auto_loop(self):
        # 随机间隔循环：在配置区间内随机等待，然后挑选一个可用群执行一次夺舍。
        while self._is_auto_enabled():
            try:
                # sleep 随机配置间隔
                sleep_sec = self._random_sleep_seconds()
                await asyncio.sleep(sleep_sec)

                platform = self.context.get_platform(
                    filter.PlatformAdapterType.AIOCQHTTP
                )
                if platform is None:
                    continue

                client = platform.get_client()
                login = await self.service.get_login_info(client)
                if not login:
                    continue

                self_id = int(login.get("user_id", 0))
                groups = await self.service.get_group_list(client)
                gids = [int(g.get("group_id", 0)) for g in groups]
                candidates = self._filter_groups(gids)
                if not candidates:
                    continue

                gid = random.choice(candidates)
                ret = await self.service.random_possess(client, gid, self_id)
                if ret:
                    user_id, name = ret
                    await self.store.set_taken(str(self_id), str(gid), user_id, name)
                    logger.info(f"auto possession in group {gid}: {name}({user_id})")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"auto_loop error: {e}")
                # 出错后短暂等待，避免热循环
                await asyncio.sleep(30)

    # ========== Config helpers ==========
    def _is_auto_enabled(self) -> bool:
        try:
            return bool(self.config.get("auto_enabled", False))
        except Exception:
            return False

    def _set_auto_enabled(self, enabled: bool) -> None:
        try:
            self.config["auto_enabled"] = bool(enabled)
            # AstrBotConfig 支持保存
            if hasattr(self.config, "save_config"):
                self.config.save_config()
        except Exception as e:
            logger.warning(f"save_config failed: {e}")

    def _group_mode(self) -> str:
        mode = str(self.config.get("group_mode", "none")).lower()
        return mode if mode in {"whitelist", "blacklist", "none"} else "none"

    def _group_list(self) -> set[int]:
        raw = self.config.get("group_list", [])
        ids: set[int] = set()
        if isinstance(raw, Iterable):
            for x in raw:
                try:
                    ids.add(int(str(x).strip()))
                except Exception:
                    continue
        return ids

    def _is_group_allowed(self, gid: int) -> bool:
        mode = self._group_mode()
        ids = self._group_list()
        if mode == "whitelist":
            return gid in ids
        if mode == "blacklist":
            return gid not in ids
        return True

    def _filter_groups(self, gids: Iterable[int]) -> list[int]:
        return [g for g in gids if g > 0 and self._is_group_allowed(g)]

    def _random_sleep_seconds(self) -> int:
        conf = self.config.get("auto_interval", {}) or {}
        try:
            min_m = int(conf.get("min_minutes", 60))
        except Exception:
            min_m = 60
        try:
            max_m = int(conf.get("max_minutes", 480))
        except Exception:
            max_m = 480
        if max_m < min_m:
            max_m = min_m
        minutes = random.randint(min_m, max_m)
        return max(30, minutes * 60)
