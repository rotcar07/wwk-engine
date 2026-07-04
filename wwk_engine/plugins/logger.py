from .platform import bot

class GameLog:
    def __init__(self, msg = None):
        self.game_log = [msg]
    def append(self, msg):
        self.game_log.append(msg)
    async def replay(self):
        logger = []
        for i in self.game_log:
            logger.append({
                    "type": "node",
                    "data": {
                        "name": "bot",
                        "uin": str(bot.bot_qid),
                        "content": i
                    }
                })
        await bot.send_group_forward_msg(messages = logger)