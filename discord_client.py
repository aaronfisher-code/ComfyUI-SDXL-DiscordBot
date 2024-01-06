import logging

import discord

from comfy_api import refresh_models, clear_history
from image_gen.image_gen_commands import ImageGenCommands
from util import setup_config, read_config

discord.utils.setup_logging()
logger = logging.getLogger("bot")

# setting up the bot
TOKEN = setup_config()
intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)

@client.event
async def on_ready():
    await refresh_models()
    clear_history()
    cmds = await tree.sync()
    logger.info("synced %d commands: %s.", len(cmds), ", ".join(c.name for c in cmds))


def start_bot():
    if c := read_config():
        if c["BOT"]["MUSIC_ENABLED"].lower() == "true":
            from commands.audio_bot import music_command

            tree.add_command(music_command)

        if c["BOT"]["SPEECH_ENABLED"].lower() == "true":
            from commands.audio_bot import speech_command

            tree.add_command(speech_command)

    command_test = ImageGenCommands(client, tree)
    command_test.add_commands()
    # run the bot
    client.run(TOKEN, log_handler=None)
