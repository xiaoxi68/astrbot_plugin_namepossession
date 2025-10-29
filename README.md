# namepossession

随机“夺舍”QQ群成员的群名片（Napcat/OneBot）。

- 指令：`/夺舍` 在当前群随机选择一名群友，将机器人的群名片改为该用户名片（或昵称），并轻戳该用户。
- 指令：`/夺舍状态` 查看当前群已“夺舍”的对象。

注意：本插件仅在 QQ(OneBot/Napcat) 平台生效；不会伪装为其他用户发言，只会修改机器人自己的群名片。

配置（AstrBot WebUI → 插件管理 → namepossession）
- auto_enabled: 是否启用定时随机“夺舍”（通过配置控制，不提供手动开启/关闭指令）。
- group_mode: 群名单模式，`whitelist`/`blacklist`/`none`。
- group_list: 群号列表（数字或字符串均可），与 `group_mode` 共同生效。
- auto_interval: 随机间隔（分钟）区间，包含 `min_minutes` 与 `max_minutes`。

行为说明
- 定时模式：插件按配置的随机间隔，在允许的群中随机挑选一群执行一次“夺舍”。
- 仅修改当前群的机器人群名片，不会影响其他群聊。
- 手动命令也会套用名单规则；若当前群不在可用范围会提示阻止。
