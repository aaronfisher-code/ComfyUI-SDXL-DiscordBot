import logging
import random
from io import BytesIO

import discord
from discord import app_commands
from discord.app_commands import Choice, Range

from audio_buttons import AudioButtons
from comfy_api import get_tortoise_voices
from consts import *
from audio_gen import (
    generate_audio,
    AudioWorkflow,
    MUSICGEN_DEFAULTS,
    TORTOISE_DEFAULTS,
)

logger = logging.getLogger("bot")


tortoise_voices = get_tortoise_voices()
TORTOISE_VOICE_CHOICES = [Choice(name=v, value=v) for v in sorted(tortoise_voices[0])][-25:]


@app_commands.command(name="music", description="Generate music from text using Musicgen.")
async def music_command(
    interaction: discord.Interaction,
    prompt: str,
    duration: Range[float, 5.0, 10.0] = None,
    cfg: Range[float, 0.0, 100.0] = None,
    top_k: Range[int, 0, 1000] = None,
    top_p: Range[float, 0.0, 1.0] = None,
    temperature: Range[float, 1e-3, 10.0] = None,
    seed: int = None,
):
    params = AudioWorkflow(
        MUSIC_WORKFLOW,
        prompt,
        duration=duration or MUSICGEN_DEFAULTS.duration,
        cfg=cfg or MUSICGEN_DEFAULTS.cfg,
        top_k=top_k or MUSICGEN_DEFAULTS.top_k,
        top_p=top_p or MUSICGEN_DEFAULTS.top_p,
        temperature=temperature or MUSICGEN_DEFAULTS.temperature,
        seed=seed,
    )
    await do_request(
        interaction,
        f'{interaction.user.mention} asked me to make music that sounds like "{prompt}", this shouldn\'t take too long...',
        f'{interaction.user.mention} asked me to make music that sounds like "{prompt}", here is what I made for them.',
        "music",
        params,
    )


@app_commands.command(name="speech", description="Generate speech from text using TorToiSe.")
@app_commands.choices(voice=TORTOISE_VOICE_CHOICES)
async def speech_command(
    interaction: discord.Interaction,
    prompt: str,
    voice: str = None,
    top_p: Range[float, 0.0, 1.0] = None,
    temperature: Range[float, 1e-3, 10.0] = None,
    seed: int = None,
):
    params = AudioWorkflow(
        TORTOISE_WORKFLOW,
        prompt,
        voice=voice or TORTOISE_DEFAULTS.voice,
        top_p=top_p or TORTOISE_DEFAULTS.top_p,
        temperature=temperature or TORTOISE_DEFAULTS.temperature,
        seed=seed,
    )
    await do_request(
        interaction,
        "speech",
        params,
        f'{interaction.user.mention} wants to speak, this shouldn\'t take too long...',
        f'{interaction.user.mention} said "{prompt}".'
    )

async def do_request(
    interaction: discord.Interaction,
    intro_message,
    completion_message,
    command_name,
    params,
):
    await interaction.response.send_message(intro_message)

    if params.seed is None:
        params.seed = random.randint(0, 999999999999999)

    data, _ = await generate_audio(params)
    _, videos, sound_fnames = data

    final_message = f"{completion_message}\n Seed: {params.seed}"
    buttons = AudioButtons(params, sound_fnames, command=command_name)
    files = [discord.File(BytesIO(vid), filename=f"sound_{i}.webm") for i, vid in enumerate(videos)]
    await interaction.channel.send(content=final_message, files=files, view=buttons)
