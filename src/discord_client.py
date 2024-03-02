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
    from src.comfyscript_utils import server_is_started
    while not await server_is_started():
        print("waiting for comfy server to start")
        await asyncio.sleep(1)

    await asyncio.sleep(1)
    print("server start")
    from src.image_gen.commands.ImageGenCommands import ImageGenCommands, SDXLCommand
    commands = []
    commands.append(ImageGenCommands(tree))
    commands.append(SDXLCommand(tree, "sdxl"))
    commands.append(SDXLCommand(tree, "imagine"))

    for command in commands:
        command.add_commands()

    if c := read_config():
        if c["BOT"]["MUSIC_ENABLED"].lower() == "true":
            from src.audio_gen.commands.audio_bot import MusicGenCommand

            music_gen = MusicGenCommand(tree)
            music_gen.add_commands()

        if c["BOT"]["SPEECH_ENABLED"].lower() == "true":
            from src.audio_gen.commands.audio_bot import SpeechGenCommand

            speech_gen = SpeechGenCommand(tree)
            speech_gen.add_commands()

    logger.info("ComfyUI is ready. Initialized commands.")
    logger.info("Syncing commands...")
    cmds = await tree.sync()
    logger.info("synced %d commands: %s.", len(cmds), ", ".join(c.name for c in cmds))

def start_bot():
    client.run(TOKEN, log_handler=None)
