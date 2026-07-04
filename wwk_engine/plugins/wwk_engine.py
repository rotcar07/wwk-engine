import asyncio
import random
import numpy

from collections import namedtuple
from dataclasses import dataclass
from collections.abc import Collection
from .platform_nb2 import bot, GROUP, PRIVATE, GROUP_SUPERUSER, SUPERUSER

class Status:
    PRE = "pre"                     #游戏前
    EVE = "eve"                     #夜晚
    DAY_PRE = "day-pre"             #在 eve 和 day-yy 之间过渡
    DAY_LW = "day-yy"               #白天开始结算后的遗言
    DAY_DIS = "day-dis"             #白天的讨论
    DAY = "day"                     #直接白天时的指示
    DAY_VOT = "day-vot"             #初次投票
    DAY_VOT_UP = "day-Vot"          #上擂投票
    DAY_VOT_END = "day-votend"      #初次投票结束
    VOT_END = "vot-end"             #投票结束
    CUT = "cut"                     #狼队自爆
    END = "end"                     #结束

@dataclass
class Player:
    id: int
    qid: int
    role: str
    dead: bool
    is_op: bool
    ori_id: str

player_list = []
status = Status.PRE
show_id = False
role_list = []
end_target = 0
game_log = []
wolf_team = []
SavePot = PoitPot = ESOp = WolfOp = WitchOp = lstGO = lstDC = GuardOp = PredOp = DCOp = KnOp = day_cnt = 0
GunOp = ""
die_list = []
dis_start = is_rev = cur_id = 0
bear_roar = -1
guned_list = []
gun_queue = []
pk_list = []
vote_list = {}
vote_for = []
can_vote_cnt = 0
is_idiot_dead = False

ROLE_DICT = {
    "WW": "白狼",
    "BW": "黑狼",
    "ES": "恶灵",
    "Wo": "狼",
    "Wi": "女巫",
    "Vi": "村民",
    "Pr": "预言家",
    "Gu": "守卫",
    "Hu": "猎人",
    "Id": "白痴",
    "Kn": "骑士",
    "Be": "熊",
    "DC": "摄梦人",
}
WOLF = ['Wo', 'WW', 'BW', 'ES']
NOT_OP = ['Id', 'Hu', 'Vi', 'Kn']

def build_help(title: str, items: dict, extra: str = ""):
    text = f"{title}\n"
    for cmd, desc in items.items():
        text += f"{cmd}  {desc}\n"
    if extra:
        text += "\n" + extra
    return text

@bot.on_command("whelp", aliases="帮助")
async def _(session):
    await session.send(
        'GENERAL / 通用:\n'
        'wjoin 加入游戏\n'
        'wshow 展示现在状态\n'
        'wvote [id] 投票\n'
        'wpass 发言结束\n'
    )

@bot.on_command("whelpsu", permission=SUPERUSER)
async def _(session):

    extra = (
        'Vi->Villager Wi->Witch Pr->Predictor Gu->Guard\n'
        'Hu->Hunter Id->Idiot WW->WhiteWolf BW->BlackWolf\n'
        'ES->EvilSpirit Wo->Wolf\n')

    await session.send(build_help("SUPERUSER / 超管：", {
        "wkick @to": "踢人",
        "wstart": "开始游戏",
        "wstop": "中止游戏",
        "wset [IDLIST] [0/1] [阵营]": "设置身份列表和是否诸神",
        "wday": "直接进入白天",
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

@bot.on_friend_request()
async def _(session):
    await session.approve()

async def get_by_qid(qid:int):
    for i in player_list:
        if i.qid == qid:
            return i.id
    return -1

async def get_by_role(role:str):
    for i in player_list:
        if i.role == role:
            return i.id
    return -1

async def ban(qid:int, time = 3600):
    x = await get_by_qid(qid)
    if x == -1 or not time or not is_idiot_dead or player_list[x-1].role != 'Id':
        try:
            await bot.set_group_ban(user_id = qid, duration = time)
        except:
            pass 

@bot.on_command("wjoin", aliases = '加入', permission = GROUP)
async def _(session):
    global player_list
    if status != Status.PRE:
        await session.send("游戏已开始")
        return
    for pl in player_list:
        if pl.qid == session.event.user_id:
            await session.send("您已加入", at_sender = True)
            return
    raw_info = await bot.get_group_member_info(user_id = session.event.user_id)
    raw_info = raw_info['card']
    raw_info = raw_info.split('|')[-1].strip()
    player_list.append(Player(0, session.event.user_id, '', False, False, raw_info))
    await session.send("已加入", at_sender = True)

@bot.on_command("wkick", aliases = '踢', permission = GROUP_SUPERUSER)
async def _(session):
    global player_list
    if status != Status.PRE:
        await session.send("游戏已开始")
        return
    msg = session.event.message
    print(msg)
    for sub in msg:
        if sub.type == "at":
            qid = int(sub.data["qq"])
            if qid == bot.bot_qid:
                continue
            for pl in player_list:
                if pl.qid == qid:
                    player_list.remove(pl)
                    break
    await session.send("踢人已完成")

def build_observe_msg():
    msg = ''
    for pl in player_list:
        x = ''
        if pl.dead and not pl.id in die_list:
            x = 'DEAD'
        else:
            x = 'ALIVE'
        msg += f'{pl.id} {x} {ROLE_DICT[pl.role]}\n'
    return msg
    
def build_player_msg():
    msg = ''
    for pl in player_list:
        x = ''
        if pl.dead and (not pl.id in die_list or (status != Status.EVE and status != Status.DAY_PRE and status != Status.VOT_END)):
            x = 'DEAD'
        else:
            x = 'ALIVE'
        msg += f'{pl.id} {x}'
        if show_id and x == 'DEAD':
            msg += f' {ROLE_DICT[pl.role]}\n'
        else:
            msg += '\n'
    return msg

def find_next_player(cur_id:int):
    if is_rev == 1:
        if cur_id == 1:
            cur_id = len(player_list)
        else:
            cur_id -= 1
        while player_list[cur_id-1].dead:
            if cur_id == 1:
                cur_id = len(player_list)
            else:
                cur_id -= 1
    else:
        if cur_id == len(player_list):
            cur_id = 1
        else:
            cur_id += 1
        while player_list[cur_id-1].dead:
            if cur_id == len(player_list):
                cur_id = 1
            else:
                cur_id += 1
    return cur_id

@bot.on_command("wshow", aliases = '看看你的', permission = GROUP | PRIVATE)
async def _(session):
    global player_list
    if status == Status.PRE:
        cnt = 0
        msg = f"目前共 {len(player_list)} 人加入 wwk\n"
        for pl in player_list:
            cnt += 1
            if session.event.message_type == 'group':
                msg += f'{cnt}. ' + MessageSegment.at(pl.qid) + '\n'
            else:
                msg += f'{cnt}. {pl.ori_id}\n'
        await session.send(msg)
        return
    cur = -1
    for pl in player_list:
        if pl.qid == session.event.user_id:
            cur = pl.id - 1
            break
    if (cur == -1 or (player_list[cur].dead == True and (not (cur+1) in die_list or (status != Status.DAY_PRE and status != Status.VOT_END and status != Status.CUT)))) and session.event.message_type == 'private':
        msg = build_observe_msg()
        await session.send(msg)
    else:
        msg = build_player_msg()
        await session.send(msg)

@bot.on_command("wset", aliases = '设置',permission = GROUP_SUPERUSER)
async def _(session):
    global role_list, show_id, end_target, game_log
    # print(session.current_arg_text)
    x = session.current_arg_text.split()
    if not x:
        return
    if x[0] == '八神':
        x = ["WWBWESWiPrIdHuGu",'1','神']
    elif x[0] == '八神2':
        x = ['WWBWESWiPrIdHuDC','1','神']
    elif '七人' in x[0]:
        x = ['PrWiHuGuViWoWW','0','民']
    elif '九人' in x[0]:
        x = ['PrWiHuGuIdKnWWBWES','0','城']
    if len(x) <= 2 or len(x[0]) % 2 == 1 or not x[1].isdigit() or int(x[1]) < 0 or int(x[1]) > 1 or not x[2] in ['边','城','民','神']:
        await session.send("wset 不合法")
        return
    role_list.clear()
    for i in range(0,len(x[0]),2):
        role_list.append(f'{x[0][i]}{x[0][i+1]}')
    if int(x[1]) == 1:
        show_id = True
    else:
        show_id = False
    end_target = x[2]
    msg = ''
    for i in role_list:
        msg += ROLE_DICT[i] + ' '
    msg += '\n'
    if show_id:
        msg += '死后公开身份'
    else:
        msg += '死后不公开身份'
    msg += ' 屠' + end_target
    game_log = [msg]
    await session.send("wset 成功\n" + msg)

async def reset():
    global player_list, status
    status = Status.END
    for pl in player_list:
        await bot.set_group_card(user_id = pl.qid, card = pl.ori_id)
    ls = await bot.get_group_member_list()
    for i in ls:
        if i['user_id'] == bot.bot_qid:
            continue
        await ban(qid = i['user_id'], time = 0)
    logger = []
    for i in game_log:
        logger.append({
                "type": "node",
                "data": {
                    "name": "bot",
                    "uin": str(bot.bot_qid),
                    "content": i
                }
            })
    await bot.send_group_forward_msg(messages = logger)
    player_list.clear()
    status = Status.PRE     

@bot.on_command("wstop", aliases = '停止',permission = SUPERUSER)
async def _(session):
    await bot.send_group_msg("游戏已终止！")
    await reset()

@bot.on_command("wnotice",permission = SUPERUSER)
async def _(session):
    global status
    if status == Status.DAY_VOT or status == Status.DAY_VOT_UP:
        for i in range(1,len(player_list)+1):
            if vote_for[i] == -1:
                await bot.send_private_msg(user_id = player_list[i-1].qid, message = '您还未投票')
    elif status == Status.EVE:
        unoped = []
        for i in player_list:
            if not i.dead and not i.is_op and not i.role in NOT_OP and not(i.id in wolf_team and i.id != wolf_team[0]):
                unoped.append(i)
        for i in unoped:
            await bot.send_private_msg(user_id = i.qid, message = '您还未操作')        

@bot.on_command("www",permission = SUPERUSER)
async def _(session):
    qid_list = await bot.get_group_member_list()
    for i in qid_list:
        if i['user_id'] == bot.bot_qid:
            continue
        await ban(qid = i['user_id'], time = 0)

@bot.on_command("wstart", aliases = '启动', permission = GROUP_SUPERUSER)
async def _(session):
    global player_list, status, day_cnt, is_idiot_dead, KnOp, game_log, ESOp, GunOp
    if session.event.group_id != bot.group_id:
        return
    if status != Status.PRE:
        await session.send("游戏已开始")
        return
    try:
        if len(player_list) < len(role_list):
            await session.send("人数不够！")
            return
        if len(player_list) > len(role_list):
            await session.send("人数太多！")
            return
        if not player_list:
            return
    except:
        await session.send("出事了")
        return
    await session.send("游戏开始！")
    status = Status.EVE
    random.shuffle(player_list)
    random.shuffle(role_list)
    msg = ''
    day_cnt = 0
    is_idiot_dead = False
    GunOp = ""
    for i in range(len(player_list)):
        player_list[i].id = i+1
        player_list[i].role = role_list[i]
        msg += f'{i+1} | {player_list[i].ori_id}\n'
        await bot.set_group_card(user_id = player_list[i].qid, card = f'{i+1} | {player_list[i].ori_id}')
        await bot.send_private_msg(user_id = player_list[i].qid, message = f"您的编号是 {player_list[i].id}，您的身份是{ROLE_DICT[role_list[i]]}")
    await session.send(msg)
    wolf_team.clear()
    for pl in player_list:
        if pl.role in WOLF:
            wolf_team.append(pl.id)
    global SavePot, PoitPot, lstGO
    SavePot = PoitPot = lstGO = ESOp = 0
    KnOp = 0
    await night_move()

async def good_win():
    await bot.send_group_msg(message = '好人胜利！')
    await bot.send_group_msg(message = build_observe_msg())
    await reset()

async def wolf_win():
    await bot.send_group_msg(message = '狼人胜利！')
    await bot.send_group_msg(message = build_observe_msg())
    await reset()

async def night_move():
    global status, player_list, WolfOp, WitchOp, GuardOp, lstGO, PredOp, day_cnt, game_log, bear_roar, lstDC, DCOp
    ls = await bot.get_group_member_list()
    for i in ls:
        if i['user_id'] == bot.bot_qid:
            continue
        await ban(qid = i['user_id'])
    day_cnt += 1
    game_log.append(build_observe_msg())
    await bot.send_group_msg(message = build_player_msg())
    for i in range(len(player_list)):
        player_list[i].is_op = False
    lstGO = GuardOp 
    lstDC = DCOp
    WolfOp = WitchOp = GuardOp = PredOp = DCOp = 0
    status = Status.EVE
    await bot.send_group_msg(message = "天黑请闭眼")
    game_log.append(f"第 {day_cnt-1} 夜：")
    msg = '你的队友：\n'
    for i in wolf_team:
        pl = player_list[i-1]
        msg = msg + str(pl.id) + ' ' + ROLE_DICT[pl.role] + '\n'
    for i in wolf_team:
        await bot.send_private_msg(user_id = player_list[i-1].qid, message = msg)
    await bot.send_private_msg(user_id = player_list[wolf_team[0]-1].qid, message = '您是主狼')
    bear_roar = -1
    for i in player_list:
        if i.role == 'Be':
            if bear_roar == -1:
                bear_roar = 0
            xx = i.id
            while player_list[xx-1].dead or xx == i.id:
                if xx == 1:
                    xx = len(player_list)
                else:
                    xx -= 1
            if xx in wolf_team:
                bear_roar = 1
            xx = i.id
            while player_list[xx-1].dead or xx == i.id:
                if xx == len(player_list):
                    xx = 1
                else:
                    xx += 1
            if xx in wolf_team:
                bear_roar = 1

async def die(id, can_op = True, from_gun = 0, queue = False):
    global wolf_team, player_list, die_list, guned_list
    if status == Status.END:
        return
    if id in die_list:
        if not can_op and id in guned_list:
            guned_list.remove(id)
        return
    if player_list[id-1].dead:
        return
    die_list.append(id)
    player_list[id-1].dead = True
    if id in wolf_team:
        if len(wolf_team) == 1:
            await good_win()
            return
        wolf_team.remove(id)
    else:
        cnt = 0
        vi_cnt = 0
        for i in player_list:
            if not i.id in wolf_team and not i.dead:
                cnt += 1
                if i.role == 'Vi':
                    vi_cnt += 1
        f = (vi_cnt == 0)
        ff = (cnt == vi_cnt)
        if end_target == '边' and (f or ff):
            await wolf_win()
            return
        if end_target == '神' and ff:
            await wolf_win()
            return
        if end_target == '民' and f:
            await wolf_win()
            return
        if end_target == '城' and (f and ff):
            await wolf_win()
            return
    if can_op and player_list[id-1].role in ['BW','Hu']:
        if queue == True:
            gun_queue.append(id)
            return
        msg = build_player_msg()
        await bot.send_private_msg(user_id = player_list[id-1].qid, message = msg)
        if from_gun:
            await bot.send_private_msg(user_id = player_list[id-1].qid, message = f"{from_gun} 枪了您")
        await bot.send_private_msg(user_id = player_list[id-1].qid, message = "您已死 是否用枪\n 回 wgun [id] 枪人，id=0 表示空枪")
        guned_list.append(id)

async def day_move():
    global status, player_list, SavePot, PoitPot, wolf_team, guned_list, die_list, game_log, ESOp
    status = "day-pre"
    die_list = []
    guned_list.clear()
    msg = ''
    if WolfOp:
        msg += f'狼队刀了 {WolfOp}\n'
    if WitchOp == 1:
        msg += '女巫救下刀口\n'
    elif WitchOp < 0:
        msg += f'女巫毒 {-WitchOp}\n'
    if PredOp:
        msg += f'预言家预言 {PredOp} 的身份\n'
    if GuardOp:
        msg += f'守卫守了 {GuardOp}'
    if DCOp:
        msg += f'摄梦人摄了 {DCOp} 的梦'
    game_log.append(msg)
    game_log.append("结算：")
    if WolfOp > 0:
        if DCOp == WolfOp:
            game_log.append(f"刀 {WolfOp} 视作空刀")
        else:
            if WitchOp == 1:
                SavePot = 1
                if GuardOp == WolfOp:
                    game_log.append(f"{WolfOp} 被奶穿")
                    await die(WolfOp, can_op = False, queue = True)
            else:
                if GuardOp != WolfOp:
                    game_log.append(f"{WolfOp} 被刀")
                    await die(WolfOp, queue = True)
    if status != Status.DAY_PRE:
        return
    if DCOp == lstDC and DCOp != 0:
        x = DCOp
        if player_list[x-1].role == 'ES':
            if ESOp:
                game_log.append(f"摄梦人连续两晚摄恶灵 {x}，恶灵免疫")
            else:
                ESOp = 1
                dcid = await get_by_role('DC')
                game_log.append(f"摄梦人连续两晚摄恶灵 {x}，恶灵反伤摄梦人 {dcid}")
                await die(dcid, queue = True)
        else:
            game_log.append(f"摄梦人连续两晚摄梦 {x}，{x} 死亡")
            await die(x,can_op = False, queue = True)
    if PredOp > 0:
        PredId = await get_by_role('Pr')
        if player_list[PredOp-1].role in WOLF:
            await bot.send_private_msg(user_id = player_list[PredId-1].qid, message = f'{PredOp} 号身份为坏')
            game_log.append(f"{PredOp} 被查杀")
        else: 
            await bot.send_private_msg(user_id = player_list[PredId-1].qid, message = f'{PredOp} 号身份为好')
            game_log.append(f"{PredOp} 是金水")
        if player_list[PredOp-1].role == 'ES' and not ESOp:
            ESOp = 1
            if DCOp == PredId:
                game_log.append(f'预言家 {PredId} 被恶灵反伤，由于摄梦人，反伤失效')
            else:
                game_log.append(f"预言家 {PredId} 被恶灵反伤")
                await die(PredId, queue = True)
    if status != Status.DAY_PRE:
        return
    if WitchOp < 0:
        if player_list[-WitchOp-1].role == 'ES':
            if ESOp:
                game_log.append(f"恶灵 {-WitchOp} 免疫伤害")
            else:
                ESOp = 1
                WitId = await get_by_role('Wi')
                if DCOp == WitId:
                    game_log.append(f"女巫 {WitId} 被恶灵反伤，由于摄梦人，反伤失效")
                else:
                    game_log.append(f"女巫 {WitId} 被恶灵反伤")
                    await die(WitId, queue = True)
        else:
            game_log.append(f"{-WitchOp} 被毒死")
            await die(-WitchOp, can_op = False, queue = True)
        PoitPot = 1
    if status != Status.DAY_PRE:
        return
    dcid = await get_by_role('DC')
    if dcid != -1:
        if player_list[dcid-1].dead and DCOp and not player_list[DCOp-1].dead:
            if player_list[DCOp-1].role == 'ES':
                game_log.append(f"摄梦人 {dcid} 连带恶灵 {DCOp} 无效")
            else:
                game_log.append(f"摄梦人 {dcid} 连带 {DCOp}")
                await die(DCOp, can_op = False, queue = True)
    if status != Status.DAY_PRE:
        return
    for i in gun_queue:
        msg = build_player_msg()
        await bot.send_private_msg(user_id = player_list[i-1].qid, message = msg)
        await bot.send_private_msg(user_id = player_list[i-1].qid, message = "您已死 是否用枪\n 回 wgun [id] 枪人，id=0 表示空枪")
        guned_list.append(i)
    gun_queue.clear()
    await asyncio.sleep(10)
    if len(guned_list) == 0:
        await last_word()

async def last_word():
    global die_list, status, dis_start, is_rev, game_log, GunOp
    if status == Status.DAY_PRE:
        status = Status.DAY_LW
        if bear_roar != -1:
            if bear_roar:
                await bot.send_group_msg(message = '熊咆哮了')
                game_log.append("熊咆哮了")
            else:
                await bot.send_group_msg(message = '熊没有咆哮')
                game_log.append("熊没有咆哮")
        if not die_list:
            await bot.send_group_msg(message = '昨晚是平安夜')
            game_log.append("昨晚为平安夜")
            dis_start = random.randint(0,len(player_list)-1)
            is_rev = random.randint(0,1)
            while player_list[dis_start].dead:
                dis_start = (dis_start + 1) % len(player_list)
            dis_start += 1
            await discuss()
        else:
            die_list = list(numpy.unique(die_list))
            die_list.sort()
            if random.randint(0,1) == 1:
                die_list.reverse()
            l = len(die_list)
            x = die_list[random.randint(0,l - 1)]
            is_rev = random.randint(0,1)
            dis_start = find_next_player(x)
            msg = build_player_msg()
            await bot.send_group_msg(message = msg)
            game_log.append(msg)
            game_log.append(' '.join(map(str,die_list)) + '死了')
            if GunOp:
                await bot.send_group_msg(message = GunOp)
            GunOp = ""
            if day_cnt == 1:
                await bot.send_group_msg(message = ' '.join(map(str,die_list)) + '死了，按照给定的顺序发遗言，发完言记得 wpass')
                await ban(qid = player_list[die_list[0]-1].qid, time = 0)
                await bot.send_group_msg(message = MessageSegment.at(player_list[die_list[0]-1].qid) + '请发遗言。')
            else:
                await bot.send_group_msg(message = ' '.join(map(str,die_list)) + '死了，非首夜夜晚死的没有遗言。')
                die_list.clear()
                await discuss()
        return
    elif status == Status.VOT_END:
        die_list = list(numpy.unique(die_list))
        die_list.sort()
        random.shuffle(die_list)
        msg = build_player_msg()
        await bot.send_group_msg(message = msg)
        await bot.send_group_msg(message = ' '.join(map(str,die_list)) + '死了，按照给定的顺序发遗言。')
        await bot.send_group_msg(message = MessageSegment.at(player_list[die_list[0]-1].qid) + '请发遗言。')
        game_log.append(' '.join(map(str,die_list)) + "死了")
        await ban(qid = player_list[die_list[0]-1].qid, time = 0)

async def discuss():
    global status, cur_id, game_log
    status = Status.DAY_DIS
    cur_id = dis_start
    game_log.append(f"第 {day_cnt} 天")
    await bot.send_group_msg(message = '进入白天发言阶段')
    if is_idiot_dead:
        for i in player_list:
            if i.role == 'Id' and not i.dead:
                await bot.send_group_msg(message = f'{i.id} 号白痴翻牌，可以在讨论阶段插麦。')
                await ban(qid = i.qid, time = 0)
    order = "递增" if is_rev == 0 else "递减"
    await bot.send_group_msg(message = f"从 {MessageSegment.at(player_list[dis_start-1].qid)} 开始发言，顺序为{order}")
    await ban(qid = player_list[dis_start-1].qid, time = 0)

@bot.on_command('wday',aliases = '直接白天', permission = SUPERUSER)
async def _(session):
    global status, player_list
    if session.event.group_id != bot.group_id:
        return
    if status != Status.EVE:
        await session.send("已经白天或游戏尚未开始")
        return
    status = Status.EVE
    await session.send("设置直接白天成功")
    await day_move()

@bot.on_command('wsay',aliases = '说', permission=PRIVATE)
async def _(session):
    global wolf_team
    q = 0
    for i in wolf_team:
        if session.event.user_id == player_list[i-1].qid:
            q = i
            break
    if q == 0:
        return
    if status == Status.DAY:
        await session.send("白天狼队不能聊天")
        return
    if status != Status.EVE:
        await session.send("现在不是晚上")
        return
    for i in wolf_team:
        if q != i:
            await bot.send_private_msg(user_id = player_list[i-1].qid, message = f"{q} 号说：{session.current_arg_text}") 

@bot.on_command('wconf',aliases = '确认', permission=PRIVATE)
async def _(session):
    global player_list
    if status != Status.EVE:
        await session.send("现在不是晚上")
        return
    id = await get_by_qid(session.event.user_id)
    if id == 0 or player_list[id-1].is_op or player_list[id-1].dead or player_list[id-1].role in NOT_OP or (id in wolf_team and id != wolf_team[0]):
        await session.send("您不可操作")
        return
    player_list[id-1].is_op = True
    await session.send("操作确认成功")
    if id == wolf_team[0]:
        id = await get_by_role('Wi')
        for i in wolf_team:
            if not i == wolf_team[0]:
                await bot.send_private_msg(user_id = player_list[i-1].qid,message = f"操作已确认")
        if id == 0 or player_list[id-1].dead or SavePot == 1:
            pass
        else:
            if WolfOp == 0:
                await bot.send_private_msg(user_id = player_list[id-1].qid, message = "狼队空刀")
            else:
                await bot.send_private_msg(user_id = player_list[id-1].qid, message = f"刀口是 {WolfOp}")
    NotOp = []
    for i in player_list:
        if not i.dead and not i.is_op and not i.role in NOT_OP and not(i.id in wolf_team and i.id != wolf_team[0]):
            NotOp.append(i)
    if len(NotOp) == 0:
        await day_move()

@bot.on_command('wpred', aliases = ['预言','预'],permission=PRIVATE)
async def _(session):
    global PredOp
    if status != Status.EVE:
        await session.send("现在不是晚上")
        return
    x = session.current_arg_text
    if not x.isdigit() or int(x) < 1 or int(x) > len(player_list):
        await session.send("操作不合法")
        return
    to = int(x)
    z = await get_by_qid(session.event.user_id)
    if z == -1:
        await session.send("操作不合法")
        return
    if player_list[z-1].role != 'Pr' or player_list[to-1].dead or player_list[z-1].is_op or player_list[z-1].dead:
        await session.send("操作不合法")
        return
    PredOp = to
    await session.send(f'您将预知 {to} 的身份')

@bot.on_command('wsave',aliases = '救', permission=PRIVATE)
async def _(session):
    global WitchOp
    if status != Status.EVE:
        await session.send("现在不是晚上")
        return
    z = await get_by_qid(session.event.user_id)
    if z == -1 or player_list[z-1].role != 'Wi' or player_list[z-1].is_op or player_list[z-1].dead or SavePot == 1 or WolfOp == 0:
        await session.send("操作不合法")
        return
    if day_cnt != 1 and z == WolfOp:
        await session.send("女巫非首夜不能自救")
    await session.send("您将救下刀口")
    WitchOp = 1

@bot.on_command('wkill', aliases = ['刀','杀'], permission=PRIVATE)
async def _(session):
    global WolfOp
    if status != Status.EVE:
        await session.send("操作不合法")
        return
    x = session.current_arg_text.strip()
    if not x.isdigit() or int(x) < 1 or int(x) > len(player_list):
        await session.send("操作不合法")
        return
    to = int(x)
    z = await get_by_qid(session.event.user_id)
    if z == -1 or z != wolf_team[0] or player_list[z-1].is_op or player_list[z-1].dead or player_list[to-1].dead:
        await session.send("操作不合法")
        return
    if player_list[to-1].role == 'ES':
        await session.send("恶灵不可自刀")
        return
    WolfOp = to
    for i in wolf_team:
        await bot.send_private_msg(user_id = player_list[i-1].qid,message = f"狼队将刀 {to} 号")

@bot.on_command('wpois', aliases = '毒', permission=PRIVATE)
async def _(session):
    global WitchOp
    if status != Status.EVE:
        await session.send("操作不合法")
        return
    x = session.current_arg_text.strip()
    if not x.isdigit() or int(x) < 1 or int(x) > len(player_list):
        await session.send("操作不合法")
        return
    to = int(x)
    z = await get_by_qid(session.event.user_id)
    if z == -1 or player_list[z-1].role != 'Wi' or player_list[z-1].is_op or player_list[z-1].dead or PoitPot == 1 or player_list[to-1].dead:
        await session.send("操作不合法")
        return
    WitchOp = -to
    await session.send(f"您将毒 {to} 号")

@bot.on_command('wguard', aliases = ['守','守卫'],permission=PRIVATE)
async def _(session):
    global GuardOp
    if status != Status.EVE:
        await session.send("现在不是晚上")
        return
    x = session.current_arg_text.strip()
    if not x.isdigit() or int(x) < 1 or int(x) > len(player_list):
        await session.send("操作不合法")
        return
    to = int(x)
    z = await get_by_qid(session.event.user_id)
    if z == -1:
        await session.send("操作不合法")
        return
    if player_list[z-1].role != 'Gu' or player_list[z-1].is_op or player_list[z-1].dead or player_list[to-1].dead or lstGO == to:
        await session.send("操作不合法")
        return
    GuardOp = to
    await session.send(f"您将守卫 {to} 号")

@bot.on_command('wcatch', aliases = ['摄','摄梦'],permission=PRIVATE)
async def _(session):
    global DCOp
    if status != Status.EVE:
        await session.send("现在不是晚上")
        return
    x = session.current_arg_text.strip()
    if not x.isdigit() or int(x) < 1 or int(x) > len(player_list):
        await session.send("操作不合法")
        return
    to = int(x)
    z = await get_by_qid(session.event.user_id)
    if z == -1:
        await session.send("操作不合法")
        return
    if player_list[z-1].role != 'DC' or player_list[z-1].is_op or player_list[z-1].dead or player_list[to-1].dead or z == to:
        await session.send("操作不合法")
        return
    DCOp = to
    await session.send(f"您将摄梦 {to} 号")

@bot.on_command('wgun',aliases = '枪',permission = PRIVATE)
async def _(session):
    global guned_list, player_list, die_list, game_log, GunOp
    if status != Status.DAY_PRE and status != Status.VOT_END and status != Status.CUT:
        await session.send("现在不是枪的时机")
        return
    q = await get_by_qid(session.event.user_id)
    if not q in guned_list:
        await session.send("您不可枪人")
        return
    x = session.current_arg_text.strip()
    if x == '0':
        guned_list.remove(q)
        await session.send("您选择空枪")
        return
    if not x.isdigit() or int(x) < 1 or int(x) > len(player_list):
        await session.send("操作不合法")
        return
    to = int(x)
    if player_list[to-1].dead:
        await session.send("操作不合法")
        return
    await session.send(f"您选择枪 {to} 号")
    game_log.append(f"{q} 枪了 {to}")
    GunOp += f"{q} 枪了 {to}\n"
    await die(to, from_gun = q)
    guned_list.remove(q)
    if player_list[to-1].role == 'DC' and status == Status.DAY_PRE and DCOp and not player_list[DCOp-1].dead:
        if player_list[DCOp-1].role == 'ES':
            game_log.append(f"摄梦人 {to} 连带恶灵 {DCOp} 无效")
        else:
            game_log.append(f"摄梦人 {to} 连带 {DCOp}")
            await die(DCOp, can_op = False)
    if status != Status.DAY_PRE and status != Status.VOT_END and status != Status.CUT:
        return
    if len(guned_list) == 0:
        if status == Status.CUT:
            await bot.send_group_msg(message = "最终死亡："+','.join(map(str,die_list)))
            die_list = []
            await night_move()
        else:
            await last_word()

@bot.on_command('wpass',aliases = ['过','锅','发起语音通话','润','没吃吃'], permission = GROUP)
async def _(session):
    global die_list, pk_list, cur_id
    if session.event.group_id != bot.group_id:
        return
    x = await get_by_qid(session.event.user_id)
    if x == -1:
        return
    if status == Status.DAY_LW:
        if x != die_list[0]:
            await session.send("还未到您的回合",at_sender = True)
            return
        die_list.pop(0)
        await ban(qid = session.event.user_id)
        if not die_list:
            await discuss()
            return
        await session.send(('请 ' + MessageSegment.at(player_list[die_list[0]-1].qid) + '发表遗言'))
        await ban(qid = player_list[die_list[0]-1].qid, time = 0)
    elif status == Status.DAY_DIS:
        if x != cur_id:
            await session.send("还未到您的回合",at_sender = True)
            return
        xx = find_next_player(cur_id)
        await ban(qid = session.event.user_id)
        if xx == dis_start:
            await day_vote()
            return
        else:
            cur_id = xx
            await session.send(('请 ' + MessageSegment.at(player_list[cur_id-1].qid) + '发言'))
            await ban(qid = player_list[cur_id-1].qid, time = 0)
    elif status == Status.VOT_END:
        if x != die_list[0]:
            await session.send("还未到您的回合",at_sender = True)
            return
        die_list.pop(0)
        await ban(qid = session.event.user_id)
        if not die_list:
            await bot.send_group_msg(message = '遗言结束，进入黑夜')
            await night_move()
            return
        await session.send(('请 ' + MessageSegment.at(player_list[die_list[0]-1].qid) + '发表遗言'))
        await ban(qid = player_list[die_list[0]-1].qid, time = 0)
    elif status == Status.DAY_VOT_END:
        if x != pk_list[0]:
            await session.send("还未到您的回合",at_sender = True)
            return
        pk_list.pop(0)
        await ban(qid = session.event.user_id)
        if not pk_list:
            if can_vote_cnt == 0:
                await bot.send_group_msg(message = '无人擂下投票，进入黑夜')
                await night_move()
            else:
                await bot.send_group_msg(message = '上擂发言结束，开始投票')
                await day_vote()
            return
        await session.send(('请 ' + MessageSegment.at(player_list[pk_list[0]-1].qid) + '发言'))
        await ban(qid = player_list[pk_list[0]-1].qid, time = 0)

async def day_vote():
    global status, vote_list, vote_for, can_vote_cnt
    if status == Status.DAY_VOT_END:
        status = Status.DAY_VOT_UP
    else:
        status = Status.DAY_VOT
    if status == Status.DAY_VOT:
        vote_list = dict()
        for i in player_list:
            if not i.dead and (not is_idiot_dead or i.role != 'Id'):
                vote_list[i.id]=[]
        vote_for = [0]
        can_vote_cnt = 0
        for i in player_list:
            if not i.dead and (not is_idiot_dead or i.role != 'Id'):
                can_vote_cnt += 1
                vote_for.append(-1)
            else:
                vote_for.append(-2)
    await bot.send_group_msg(message = '进入投票阶段，私信 wvote [id] 投票。id=0 视为弃票。')

@bot.on_command('wcut', aliases = ['爆','自爆'],permission = PRIVATE)
async def _(session):
    global player_list, status, cur_id, KnOp
    id = await get_by_qid(session.event.user_id)
    if id == -1:
        return
    if (not id in wolf_team and player_list[id-1].role != 'Kn') or player_list[id-1].dead:
        return
    if player_list[id-1].role == 'Kn' and KnOp == 1:
        await session.send("骑士只能进行一次决斗")
        return
    if player_list[id-1].role == 'ES':
        await session.send("恶灵不可自爆")
        return
    xx = session.current_arg_text.strip()
    if not(status == Status.DAY_DIS or status == Status.DAY_VOT_END):
        await bot.send_private_msg(user_id = session.event.user_id, message = '现在不能 wcut！')
        return
    if player_list[id-1].role == 'Kn' and status == Status.DAY_VOT_END:
        await session.send("")
    if (not xx or player_list[id-1].role != 'WW') and player_list[id-1].role != 'Kn':
        await bot.send_group_msg(message = f'狼队 {id} 号自爆，白天阶段终止')
        game_log.append(f'狼队 {id} 号自爆，白天阶段终止')
        await die(id)
        if status == Status.DAY_DIS:
            await ban(qid = player_list[cur_id-1].qid)
        elif status == Status.DAY_VOT_END:
            await ban(qid = player_list[pk_list[0]-1].qid)
        if status.startswith(Status.DAY):
            await night_move()
    elif xx.isdigit():
        x = int(xx)
        if x < 0 or x > len(player_list) or x == id or player_list[x-1].dead:
            await bot.send_private_msg(user_id = session.event.user_id, message = 'id 参数不合法！')
            return
        if player_list[id-1].role == 'Kn':
            if x == 0 or player_list[x-1].dead:
                await session.send('id 参数不合法！')
                return
            else:
                await bot.send_group_msg(message = f'！！骑士 {id} 与 {x} 进行决斗！！')
                if x in wolf_team:
                    await bot.send_group_msg(message = f'决斗成功，{x} 号死亡，白天终止')
                    game_log.append(f'骑士 {id} 与 {x} 进行决斗，决斗成功，{x} 号死亡，白天终止')
                    KnOp = 1
                    if status == Status.DAY_DIS:
                        await ban(qid = player_list[cur_id-1].qid)
                    elif status == Status.DAY_VOT_END:
                        await ban(qid = player_list[pk_list[0]-1].qid)
                    await die(x)
                    if not status.startswith(Status.DAY):
                        return
                    if not guned_list:
                        if not show_id:
                            await asyncio.sleep(random.randint(3,10))
                        await night_move()
                        return
                    status = Status.CUT
                else:
                    await bot.send_group_msg(message = f'骑士死亡，发言继续')
                    game_log.append(f'骑士 {id} 与 {x} 进行决斗，骑士死亡')
                    await die(id)
                    if not status.startswith(Status.DAY):
                        return
                    if status == Status.DAY_DIS and cur_id == id:
                        xx = await find_next_player(cur_id)
                        await ban(qid = session.event.user_id)
                        if xx == dis_start:
                            await day_vote()
                            return
                        else:
                            cur_id = xx
                            await session.send(('请 ' + MessageSegment.at(player_list[cur_id-1].qid) + '发言'))
                            await ban(qid = player_list[cur_id-1].qid, time = 0)
                    elif status == Status.DAY_VOT_END and pk_list[0] == id:
                        pk_list.pop(0)
                        await ban(qid = session.event.user_id)
                        if not pk_list:
                            if can_vote_cnt == 0:
                                await bot.send_group_msg(message = '无人擂下投票，进入黑夜')
                                await night_move()
                            else:
                                await bot.send_group_msg(message = '上擂发言结束，开始投票')
                                await day_vote()
                            return
                        await session.send(('请 ' + MessageSegment.at(player_list[pk_list[0]-1].qid) + '发言'))
                        await ban(qid = player_list[pk_list[0]-1].qid, time = 0)
            return
        if x == 0 or player_list[x-1].dead:
            await bot.send_group_msg(message = f'狼队 {id} 号自爆，白天阶段终止')
            game_log.append(f'狼队 {id} 号自爆，白天阶段终止')
            if status == Status.DAY_DIS:
                await ban(qid = player_list[cur_id-1].qid)
            elif status == Status.DAY_VOT_END:
                await ban(qid = player_list[pk_list[0]-1].qid)
            await die(id)
            if status.startswith(Status.DAY):
                await night_move()
        else:
            await bot.send_group_msg(message = f'白狼 {id} 号自爆带走 {x}，白天阶段终止')
            game_log.append(f'白狼 {id} 号自爆带走 {x}，白天阶段终止')
            if status == Status.DAY_DIS:
                await ban(qid = player_list[cur_id-1].qid)
            elif status == Status.DAY_VOT_END:
                await ban(qid = player_list[pk_list[0]-1].qid)
            await die(id)
            if status.startswith(Status.DAY):
                await die(x)
            else:
                return
            if status.startswith(Status.DAY) and not guned_list:
                if not show_id:
                    await asyncio.sleep(random.randint(10,15))
                await night_move()
            else:
                if status == Status.PRE:
                    return
                status = Status.CUT

@bot.on_command('wvote', aliases = ['投','票','投票'],permission = PRIVATE)
async def _(session):
    global vote_for, vote_list, can_vote_cnt
    id = await get_by_qid(session.event.user_id)
    if status != Status.DAY_VOT and status != Status.DAY_VOT_UP:
        await session.send('还未到投票阶段')
        return
    if id == -1 or player_list[id-1].dead or vote_for[id] == -2:
        return
    xx = session.current_arg_text.strip()
    if xx.isdigit():
        x = int(xx)
        if x < 0 or x > len(player_list):
            await session.send("参数不合法")
            return
    else:
        await session.send("参数不合法")
        return
    x = int(xx)
    if x == 0:
        if vote_for[id] != -1:
            if vote_for[id] != 0:
                vote_list[vote_for[id]].remove(id)
        else:
            can_vote_cnt -= 1
        vote_for[id] = 0
        await session.send("您将弃票")
    else:
        if vote_list.get(x) == None:
            await session.send(f"不能投 {x} 号")
            return
        f = 0
        if vote_for[id] != -1:
            if vote_for[id] != 0:
                vote_list[vote_for[id]].remove(id)
        else:
            can_vote_cnt -= 1
            f = 1
        vote_for[id] = x
        vote_list[x].append(id)
        await session.send(f"您将投 {x} 号")
    if can_vote_cnt == 0:
        await vote_end()

async def vote_end():
    global vote_list, vote_for, can_vote_cnt, status, pk_list, die_list, is_idiot_dead, game_log
    msg = '投票结果：\n'
    mxcnt = 0
    voteto = []
    for item in vote_list.items():
        if len(item[1]):
            msg += f'{item[0]} <- '
            msg += ','.join(map(str,item[1]))
            msg += '\n'
            if len(item[1]) > mxcnt:
               voteto = [item[0]]
               mxcnt = len(item[1])
            elif len(item[1]) == mxcnt:
                voteto.append(item[0]) 
    if mxcnt == 0:
        msg += '全员弃票'
    else:
        msg += '最多票得者为：' + ','.join(map(str,voteto))
    if mxcnt == 0:
        await bot.send_group_msg(message = msg)
        await night_move()
        return
    game_log.append(msg)
    if len(voteto) == 1:
        if status != Status.DAY_VOT and status != Status.DAY_VOT_UP:
            return
        status = Status.VOT_END
        await bot.send_group_msg(message = msg)
        await bot.send_group_msg(message = f'{voteto[0]} 号被票出')
        game_log.append(f'{voteto[0]} 号被票出')
        if player_list[voteto[0]-1].role == 'Id':
            await bot.send_group_msg(message = f'{voteto[0]} 号翻牌是白痴，取消放逐')
            game_log.append(f'{voteto[0]} 号翻牌是白痴，取消放逐')
            is_idiot_dead = True
            die_list.append(voteto[0])
            await bot.send_group_msg(message = f"请 {voteto[0]} 发表遗言")
            return
        die_list = []
        await die(voteto[0])
        if not guned_list:
            await last_word()
        return
    if status == Status.DAY_VOT_UP:
        await bot.send_group_msg(message = msg)
        await bot.send_group_msg(message = '上擂平票，投票结束，进入黑夜')
        game_log.append('上擂平票，投票结束，进入黑夜')
        await night_move()
    else:
        pk_list = voteto
        status = Status.DAY_VOT_END
        await bot.send_group_msg(message = msg)
        vote_list = {}
        vote_for = [0]
        can_vote_cnt = 0
        for ii in voteto:
            vote_list[ii]=[]
        for i in range(1,len(player_list)+1):
            if i in voteto or player_list[i-1].dead or (is_idiot_dead and player_list[i-1].role == 'Id'):
                vote_for.append(-2)
            else:
                vote_for.append(-1)
                can_vote_cnt += 1
        await bot.send_group_msg(message = ','.join(map(str,voteto)) + '上擂，请按此顺序发言')
        await bot.send_group_msg(message = MessageSegment.at(player_list[voteto[0]-1].qid) + '请发言。')
        game_log.append(','.join(map(str,voteto)) + '上擂')
        await ban(qid = player_list[voteto[0]-1].qid, time = 0)