from .platform import bot, SUPERUSER

def build_help(title: str, items: dict, extra: str = ""):
    text = f"{title}\n"
    for cmd, desc in items.items():
        text += f"{cmd}  {desc}\n"
    if extra:
        text += "\n" + extra
    return text

@bot.on_command("whelp", aliases = "帮助")
async def _(session):
    await session.send(
        'GENERAL / 通用:\n'
        'wjoin 加入游戏\n'
        'wshow 展示现在状态\n'
        'wvote [id] 投票\n'
        'wpass 发言结束\n'
    )

@bot.on_command("whelpsu", permission = SUPERUSER)
async def _(session):

    extra = (
        'Vi->Villager Wi->Witch Pr->Predictor Gu->Guard\n'
        'Hu->Hunter Id->Idiot WW->WhiteWolf BW->BlackWolf\n'
        'ES->EvilSpirit Wo->Wolf\n')

    await session.send(build_help("SUPERUSER / 超管：", {
        "wkick @to": "踢人",
        "wstart": "开始游戏",
        "wstop": "中止游戏",
        "wset [IDLIST] [0/1] [阵营]": "设置本局配置",
        "wday": "直接进入白天",
        "www": "强制解除所有人禁言"
    }, extra))

@bot.on_command("wolfhelp")
async def _(session):

    extra = (
        "说明：\n"
        "主狼机制：系统随机指定主狼，只有主狼能使用 wkill。\n"
        "主狼死亡后自动切换。\n"
        "wcut 为即时操作，无需 wconf，请谨慎。"
    )

    await session.send(build_help("WOLF / 狼队：", {
        "wkill [id]": "主狼刀人",
        "wconf": "确认操作（空刀也要发）",
        "wsay [msg]": "狼队内部通讯",
        "wcut [id=0]": "自爆（仅私聊）",
        "wgun [id]": "黑狼开枪（0为空枪）",
    }, extra))

@bot.on_command("otherhelp")
async def _(session):

    await session.send(build_help("OTHER ROLES / 其他职业：", {
        "wpred [id]": "预言家查验",
        "wsave": "女巫救人",
        "wpois [id]": "女巫毒人",
        "wguard [id]": "守卫守护",
        "wgun [id]": "猎人/黑狼开枪",
        "wconf": "确认/跳过行动",
        "wcut [id]": "骑士决斗",
        "wcatch [id]": "摄梦人摄梦",
    }))