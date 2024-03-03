import logging
from io import BytesIO

import discord
from discord.app_commands import Range

from src.audio_gen.audio_gen import *
from src.audio_gen.ui.audio_buttons import AudioButtons
from src.consts import *

logger = logging.getLogger("bot")

# tortoise_voices = get_tortoise_voices()
# TORTOISE_VOICE_CHOICES = [Choice(name=v, value=v) for v in sorted(tortoise_voices[0])][-25:]

class SoundCommand():
    async def _do_request(
            self,
            interaction: discord.Interaction,
            intro_message,
            completion_message,
            command_name,
            params,
    ):
        await interaction.response.send_message(intro_message)

        if params.seed is None:
            params.seed = random.randint(0, 999999999999999)

        if command_name == "music":
            data = await generate_audio(params)
        elif command_name == "sing":
            data = await generate_music_with_tts(params)
        else:
            data = await generate_tts(params)

        videos, _, sound_fnames = data

        final_message = f"{completion_message}\n Seed: {params.seed}"
        buttons = AudioButtons(params, sound_fnames, command=command_name)
        files = [discord.File(BytesIO(vid), filename=f"sound_{i}.webm") for i, vid in enumerate(videos)]
        await interaction.channel.send(content=final_message, files=files, view=buttons)

class MusicGenCommand(SoundCommand):
    def __init__(self, tree: discord.app_commands.CommandTree):
        self.tree = tree

    def add_commands(self):
        @self.tree.command(name="music", description="Generate music from text using Musicgen.")
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
            await self._do_request(
                interaction,
                f'{interaction.user.mention} asked me to make music that sounds like "{prompt}", this shouldn\'t take too long...',
                f'{interaction.user.mention} asked me to make music that sounds like "{prompt}", here is what I made for them.',
                "music",
                params,
            )


class SpeechGenCommand(SoundCommand):
    def __init__(self, tree: discord.app_commands.CommandTree):
        self.tree = tree

    def add_commands(self):
        @self.tree.command(name="speech", description="Generate speech from text using TorToiSe.")
        # @app_commands.choices(voice=TORTOISE_VOICE_CHOICES)
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
            await self._do_request(
                interaction,
                f'{interaction.user.mention} wants to speak, this shouldn\'t take too long...',
                f'{interaction.user.mention} said "{prompt}".',
                "speech",
                params
            )

        @self.tree.command(name="sing", description="Sing!")
        async def sing_command(
                interaction: discord.Interaction,
                music_prompt: str,
                lyrics: str,
                voice: str = None,
                top_k: Range[int, 0, 1000] = None,
                top_p: Range[float, 0.0, 1.0] = None,
                temperature: Range[float, 1e-3, 10.0] = None,
                seed: int = None,
        ):
            params = AudioWorkflow(
                TORTOISE_WORKFLOW,
                lyrics,
                voice=voice or TORTOISE_DEFAULTS.voice,
                top_p=top_p or MUSICGEN_DEFAULTS.top_p,
                top_k=top_k or MUSICGEN_DEFAULTS.top_k,
                temperature=temperature or MUSICGEN_DEFAULTS.temperature,
                seed=seed,
                secondary_prompt=music_prompt,
            )
            await self._do_request(
                interaction,
                f'🎙️{interaction.user.mention} wants to sing, this shouldn\'t take too long...🎙️',
                f'🎙️{interaction.user.mention} sung "{lyrics}".🎙️',
                "sing",
                params
            )
