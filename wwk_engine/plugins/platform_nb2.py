import nonebot
from nonebot import init, get_bot, on_command, on_type
from nonebot.permission import SUPERUSER, Permission
from nonebot.adapters.onebot.v11 import (
    Bot,
    Event,
    FriendRequestEvent,
    GroupMessageEvent,
    GroupRequestEvent,
    MessageSegment,
    PrivateMessageEvent,
    MessageEvent,
)

class Context:
    def __init__(self, bot: Bot, event: MessageEvent, matcher):
        self.bot = bot
        self.event = event
        self.matcher = matcher
    @property
    def current_arg_text(self) -> str:
        text = self.event.get_plaintext().strip()
        arg_text = text.split(maxsplit=1)[1] if " " in text else ""
        return arg_text
    async def send(self, message, at_sender:bool = False):
        await self.matcher.send(message = message, at_sender = at_sender)

class FriendRequestContext:
    def __init__(self, bot, event):
        self.bot = bot
        self.event = event

    async def approve(self):
        await self.bot.set_friend_add_request(
            flag=self.event.flag,
            approve=True
        )

class NoneBotPlatform:
    def __init__(self, group_id: int, bot_qid: int):
        self.group_id = group_id
        self.bot_qid = bot_qid
    @property
    def bot(self):
        return get_bot()
    async def send_group_msg(self, message:str):
        await self.bot.send_group_msg(group_id = self.group_id, message = message)
    async def send_private_msg(self, user_id:int, message:str):
        await self.bot.send_private_msg(user_id = user_id, message = message)
    async def set_group_card(self, user_id:int, card:str):
        await self.bot.set_group_card(group_id = self.group_id, user_id = user_id, card = card)
    async def set_group_ban(self, user_id:int, duration:int):
        await self.bot.set_group_ban(group_id = self.group_id, user_id = user_id, duration = duration)
    async def get_group_member_list(self):
        return await self.bot.get_group_member_list(group_id = self.group_id)
    async def get_group_member_info(self, user_id:int):
        return await self.bot.get_group_member_info(group_id = self.group_id, user_id = user_id)
    async def send_group_forward_msg(self, messages:list):
        await self.bot.send_group_forward_msg(group_id = self.group_id, messages = messages)
    async def approve_friend_request(self, user_id:int):
        await self.bot.approve_friend_request(user_id = user_id)
    def on_command(
        self,
        name: str,
        aliases: Collection[str] | None = None, # pyright: ignore[reportGeneralTypeIssues]
        permission = None
    ):
        def decorator(func):
            matcher = on_command(
                name,
                aliases = set(aliases) if aliases else None,
                permission = permission 
            )
            @matcher.handle()
            async def _(bot: Bot, event: MessageEvent):
                ctx = Context(bot, event, matcher)
                await func(ctx)

            return func

        return decorator
    def on_friend_request(self):
        def decorator(func):
            matcher = on_type(FriendRequestEvent)

            @matcher.handle()
            async def _(bot: Bot, event: FriendRequestEvent):
                ctx = FriendRequestContext(bot, event)
                await func(ctx)
            return func
        return decorator

config = nonebot.get_driver().config
bot = NoneBotPlatform(group_id=config.groupid, bot_qid=config.botqid)

async def is_group(event: Event) -> bool:
    return isinstance(event, GroupMessageEvent) and event.group_id == platform.group_id
async def is_private(event: Event) -> bool:
    return isinstance(event, PrivateMessageEvent)
async def group_and_superuser(event: Event) -> bool:
    return await is_group(event) and str(event.user_id) in config.superusers

GROUP_SUPERUSER = Permission(group_and_superuser)
GROUP = Permission(is_group)
PRIVATE = Permission(is_private)