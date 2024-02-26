import asyncio
import logging
import discord
from src.util import setup_config, read_config

discord.utils.setup_logging()
logger = logging.getLogger("bot")

# setting up the bot
TOKEN = setup_config()
intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)

@client.event
async def on_ready():
    # from src.comfy_api import refresh_models, clear_history
    # await refresh_models()
    # clear_history()
    cmds = await tree.sync()
    logger.info("synced %d commands: %s.", len(cmds), ", ".join(c.name for c in cmds))

def start_bot():
    from src.image_gen.commands.ImageGenCommands import ImageGenCommands
    if c := read_config():
        if c["BOT"]["MUSIC_ENABLED"].lower() == "true":
            from src.audio_gen.commands.audio_bot import MusicGenCommand

            music_gen = MusicGenCommand(tree)
            music_gen.add_commands()

        if c["BOT"]["SPEECH_ENABLED"].lower() == "true":
            from src.audio_gen.commands.audio_bot import SpeechGenCommand

            speech_gen = SpeechGenCommand(tree)
            speech_gen.add_commands()

    command_test = ImageGenCommands(tree)
    command_test.add_commands()
    # run the bot
    client.run(TOKEN, log_handler=None)
