import json
import logging
import random
import os
import discord

from discord import app_commands, Attachment
from discord.app_commands import Choice, Range

from buttons import Buttons
from comfy_api import (
    get_models,
    get_loras,
    get_samplers,
    clear_history,
)
from imageGen import (
    ImageWorkflow,
    generate_images,
    SD15_GENERATION_DEFAULTS,
    SDXL_GENERATION_DEFAULTS,
    VIDEO_GENERATION_DEFAULTS,
)
from collage_utils import create_collage
from consts import *
from util import (
    read_config,
    setup_config,
    should_filter,
    unpack_choices,
    get_filename,
    process_attachment,
)

discord.utils.setup_logging()
logger = logging.getLogger("bot")

# setting up the bot
TOKEN = setup_config()
intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)

models = get_models()
loras = get_loras()
samplers = get_samplers()

generation_messages = json.loads(open("generation_messages.json", "r").read())
completion_messages = json.loads(open("completion_messages.json", "r").read())

# These aspect ratio resolution values correspond to the SDXL Empty Latent Image node.
# A latent modification node in the workflow converts it to the equivalent SD 1.5 resolution values.
ASPECT_RATIO_CHOICES = [
    Choice(name="1:1", value="1024 x 1024  (square)"),
    Choice(name="7:9 portrait", value=" 896 x 1152  (portrait)"),
    Choice(name="4:7 portrait", value=" 768 x 1344  (portrait)"),
    Choice(name="9:7 landscape", value="1152 x 896   (landscape)"),
    Choice(name="7:4 landscape", value="1344 x 768   (landscape)"),
]
SD15_MODEL_CHOICES = [Choice(name=m.replace(".safetensors", ""), value=m) for m in models[0] if "xl" not in m.lower()][:25]
SD15_LORA_CHOICES = [Choice(name=l.replace(".safetensors", ""), value=l) for l in loras[0] if "xl" not in l.lower()][:25]
SDXL_MODEL_CHOICES = [Choice(name=m.replace(".safetensors", ""), value=m) for m in models[0] if "xl" in m.lower() and "refiner" not in m.lower()][
                     :25]
SDXL_LORA_CHOICES = [Choice(name=l.replace(".safetensors", ""), value=l) for l in loras[0] if "xl" in l.lower()][:25]
SAMPLER_CHOICES = [Choice(name=s, value=s) for s in samplers[0]]

BASE_ARG_DESCS = {
    "prompt": "Prompt for the image being generated",
    "negative_prompt": "Prompt for what you want to steer the AI away from",
    "model": "Model checkpoint to use",
    "lora": "LoRA to apply",
    "lora_strength": "Strength of LoRA",
    "aspect_ratio": "Aspect ratio of the generated image",
    "sampler": "Sampling algorithm to use",
    "num_steps": f"Number of sampling steps; range [1, {MAX_STEPS}]",
    "cfg_scale": f"Degree to which AI should follow prompt; range [1.0, {MAX_CFG}]",
}
IMAGINE_ARG_DESCS = {
    **BASE_ARG_DESCS,
    "num_steps": "Number of sampling steps; range [1, 30]",
    "input_file": "Image to use as input for img2img",
    "denoise_strength": f"Strength of denoising filter during img2img. Only works when input_file is set; range [0.01, 1.0], default {SD15_GENERATION_DEFAULTS.denoise_strength}"
}
SDXL_ARG_DESCS = {
    **BASE_ARG_DESCS,
    "input_file": "Image to use as input for img2img",
    "denoise_strength": f"Strength of denoising filter during img2img. Only works when input_file is set; range [0.01, 1.0], default {SDXL_GENERATION_DEFAULTS.denoise_strength}"
}
VIDEO_ARG_DESCS = {k: v for k, v in BASE_ARG_DESCS.items() if k != "aspect_ratio"}

BASE_ARG_CHOICES = {
    "aspect_ratio": ASPECT_RATIO_CHOICES,
    "sampler": SAMPLER_CHOICES,
}
IMAGINE_ARG_CHOICES = {
    "model": SD15_MODEL_CHOICES,
    "lora": SD15_LORA_CHOICES,
    "lora2": SD15_LORA_CHOICES,
    **BASE_ARG_CHOICES,
}
SDXL_ARG_CHOICES = {
    "model": SDXL_MODEL_CHOICES,
    "lora": SDXL_LORA_CHOICES,
    "lora2": SDXL_LORA_CHOICES,
    **BASE_ARG_CHOICES,
}
VIDEO_ARG_CHOICES = {
    k: v for k, v in IMAGINE_ARG_CHOICES.items() if k not in {"lora2", "lora3", "aspect_ratio"}
}


async def refresh_models():
    global models
    global loras
    models = get_models()
    loras = get_loras()
    logger.info("refreshed models.")


@tree.command(name="refresh", description="Refresh the list of models and loras")
async def slash_command(interaction: discord.Interaction):
    await refresh_models()
    await interaction.response.send_message("Refreshed models and loras", ephemeral=True)


@tree.command(name="imagine", description="Generate an image based on input text")
@app_commands.describe(**IMAGINE_ARG_DESCS)
@app_commands.choices(**IMAGINE_ARG_CHOICES)
async def slash_command(
        interaction: discord.Interaction,
        prompt: str,
        negative_prompt: str = None,
        model: str = None,
        lora: Choice[str] = None,
        lora_strength: float = 1.0,
        lora2: Choice[str] = None,
        lora_strength2: float = 1.0,
        # enhance: bool = False,
        aspect_ratio: str = None,
        sampler: str = None,
        num_steps: Range[int, 1, MAX_STEPS] = None,
        cfg_scale: Range[float, 1.0, MAX_CFG] = None,
        seed: int = None,
        input_file: Attachment = None,
        denoise_strength: Range[float, 0.01, 1.0] = None
):
    if input_file is not None:
        fp = await process_attachment(input_file, interaction)
        if fp is None:
            return

    params = ImageWorkflow(
        SD15_WORKFLOW if input_file is None else SD15_ALTS_WORKFLOW,
        prompt,
        negative_prompt,
        model or SD15_GENERATION_DEFAULTS.model,
        unpack_choices(lora, lora2),
        [lora_strength, lora_strength2],
        aspect_ratio or SD15_GENERATION_DEFAULTS.aspect_ratio,
        sampler or SD15_GENERATION_DEFAULTS.sampler,
        num_steps or SD15_GENERATION_DEFAULTS.num_steps,
        cfg_scale or SD15_GENERATION_DEFAULTS.cfg_scale,
        seed=seed,
        slash_command="imagine",
        filename=fp if input_file is not None else None,
        denoise_strength=denoise_strength or SD15_GENERATION_DEFAULTS.denoise_strength
    )
    await do_request(
        interaction,
        f'🖼️ {interaction.user.mention} asked me to imagine "{prompt}"! {random.choice(generation_messages)} 🖼️',
        f'{interaction.user.mention} asked me to imagine "{prompt}"! {random.choice(completion_messages)}',
        "imagine",
        params,
    )


@tree.command(name="video", description="Generate a video based on input text")
@app_commands.describe(**VIDEO_ARG_DESCS)
@app_commands.choices(**VIDEO_ARG_CHOICES)
async def slash_command(
        interaction: discord.Interaction,
        prompt: str,
        negative_prompt: str = None,
        model: str = None,
        lora: Choice[str] = None,
        lora_strength: float = 1.0,
        lora2: Choice[str] = None,
        lora_strength2: float = 1.0,
        sampler: str = None,
        num_steps: Range[int, 1, MAX_STEPS] = None,
        cfg_scale: Range[float, 1.0, MAX_CFG] = None,
        seed: int = None,
):
    params = ImageWorkflow(
        VIDEO_WORKFLOW,
        prompt,
        negative_prompt,
        model or VIDEO_GENERATION_DEFAULTS.model,
        unpack_choices(lora, lora2),
        [lora_strength, lora_strength2],
        None,
        sampler=sampler or VIDEO_GENERATION_DEFAULTS.sampler,
        num_steps=num_steps or VIDEO_GENERATION_DEFAULTS.num_steps,
        cfg_scale=cfg_scale or VIDEO_GENERATION_DEFAULTS.cfg_scale,
        seed=seed,
        slash_command="video",
    )
    await do_request(
        interaction,
        f'🎥{interaction.user.mention} asked me to create the video "{prompt}"! {random.choice(generation_messages)} 🎥',
        f'{interaction.user.mention} asked me to create the video "{prompt}"! {random.choice(completion_messages)} 🎥',
        "video",
        params,
    )


@tree.command(name="sdxl", description="Generate an image using SDXL")
@app_commands.describe(**BASE_ARG_DESCS)
@app_commands.choices(**SDXL_ARG_CHOICES)
async def slash_command(
        interaction: discord.Interaction,
        prompt: str,
        negative_prompt: str = None,
        model: str = None,
        lora: Choice[str] = None,
        lora_strength: float = 1.0,
        lora2: Choice[str] = None,
        lora_strength2: float = 1.0,
        aspect_ratio: str = None,
        sampler: str = None,
        num_steps: Range[int, 1, MAX_STEPS] = None,
        cfg_scale: Range[float, 1.0, MAX_CFG] = None,
        seed: int = None,
        input_file: Attachment = None,
        denoise_strength: Range[float, 0.01, 1.0] = None
):
    if input_file is not None:
        fp = await process_attachment(input_file, interaction)
        if fp is None:
            return

    params = ImageWorkflow(
        SDXL_WORKFLOW if input_file is None else SDXL_ALTS_WORKFLOW,
        prompt,
        negative_prompt,
        model or SDXL_GENERATION_DEFAULTS.model,
        unpack_choices(lora, lora2),
        [lora_strength, lora_strength2],
        aspect_ratio or SDXL_GENERATION_DEFAULTS.aspect_ratio,
        sampler=sampler or SDXL_GENERATION_DEFAULTS.sampler,
        num_steps=num_steps or SDXL_GENERATION_DEFAULTS.num_steps,
        cfg_scale=cfg_scale or SDXL_GENERATION_DEFAULTS.cfg_scale,
        seed=seed,
        slash_command="sdxl",
        filename=fp if input_file is not None else None,
        denoise_strength=denoise_strength or SDXL_GENERATION_DEFAULTS.denoise_strength
    )
    await do_request(
        interaction,
        f'🖌️{interaction.user.mention} asked me to imagine "{prompt}" using SDXL! {random.choice(generation_messages)} 🖌️',
        f'🖌️ {interaction.user.mention} asked me to imagine "{prompt}" using SDXL! {random.choice(completion_messages)}. 🖌️',
        "sdxl",
        params,
    )


async def do_request(
        interaction: discord.Interaction,
        intro_message: str,
        completion_message: str,
        command_name: str,
        params: ImageWorkflow,
):
    if should_filter(params.prompt, params.negative_prompt):
        logger.info(
            "Prompt or negative prompt contains a blocked word, not generating image. Prompt: %s, Negative Prompt: %s",
            params.prompt,
            params.negative_prompt,
        )
        await interaction.response.send_message(
            f"The prompt {params.prompt} or negative prompt {params.negative_prompt} contains a blocked word, not generating image.",
            ephemeral=True,
        )
        return

    # Send an initial message
    await interaction.response.send_message(intro_message)

    if params.seed is None:
        params.seed = random.randint(0, 999999999999999)

    images, enhanced_prompt = await generate_images(params)

    final_message = f"{completion_message}\n Seed: {params.seed}"
    buttons = Buttons(params, images, interaction.user, command=command_name)

    file_name = get_filename(interaction, params)

    fname = f"{file_name}.gif" if "GIF" in images[0].format else f"{file_name}.png"
    await interaction.channel.send(
        content=final_message, file=discord.File(fp=create_collage(images), filename=fname), view=buttons
    )


@client.event
async def on_ready():
    await refresh_models()
    clear_history()
    cmds = await tree.sync()
    logger.info("synced %d commands: %s.", len(cmds), ", ".join(c.name for c in cmds))


if c := read_config():
    if c["BOT"]["MUSIC_ENABLED"].lower() == "true":
        from audio_bot import music_command

        tree.add_command(music_command)

    if c["BOT"]["SPEECH_ENABLED"].lower() == "true":
        from audio_bot import speech_command

        tree.add_command(speech_command)

# run the bot
client.run(TOKEN, log_handler=None)
