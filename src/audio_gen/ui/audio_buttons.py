import random
from copy import deepcopy
from io import BytesIO

import discord
from discord import ui

from src.audio_gen.audio_gen import generate_audio, AudioWorkflow, extend_audio, MUSICGEN_DEFAULTS
from src.consts import MUSIC_CONTINUE_WORKFLOW, TORTOISE_WORKFLOW
from src.image_gen.ui.buttons import ImageButton


class AudioButtons(discord.ui.View):
    def __init__(self, params, sound_fnames, *, timeout=None, command=None):
        super().__init__(timeout=timeout)
        self.params = params
        self.sound_fnames = sound_fnames
        self.command = command

        if command == "speak":
            return

        for i in range(len(sound_fnames)):
            self.add_item(ImageButton(f"E{i + 1}", "⏩", 1, self.extend))

    @discord.ui.button(label="Re-roll", style=discord.ButtonStyle.green, emoji="🎲", row=0)
    async def reroll(self, interaction, btn):
        await interaction.response.send_message(f'{interaction.user.mention} asked me to re-imagine "{self.params.prompt}", this shouldn\'t take too long...')
        btn.disabled = True
        await interaction.message.edit(view=self)

        params = deepcopy(self.params)
        params.seed = random.randint(0, 999999999999999)

        (videos, _, sound_fnames) = await generate_audio(params)

        final_message = f"{interaction.user.mention} here is your re-imagined audio"
        buttons = AudioButtons(params, sound_fnames, command=self.command)

        files = [discord.File(fp=BytesIO(v), filename=f"sound_{i}.webm") for i, v in enumerate(videos)]
        await interaction.channel.send(content=final_message, files=files, view=buttons)

    @discord.ui.button(label="Edit", style=discord.ButtonStyle.blurple, emoji="📝", row=0)
    async def edit(self, interaction, button):
        params: AudioWorkflow = deepcopy(self.params)
        # params.workflow_name = MUSIC_WORKFLOW
        params.snd_filename = None  # params.snd_filename[index]
        params.vid_filename = None

        modal = AudioEditModal(params, "edit")
        await interaction.response.send_modal(modal)

    async def extend(self, interaction, button):
        index = int(button.label[-1:]) - 1

        params: AudioWorkflow = deepcopy(self.params)

        if params.workflow_name is TORTOISE_WORKFLOW:
            params.cfg = MUSICGEN_DEFAULTS.cfg
            params.top_k = MUSICGEN_DEFAULTS.top_k
            params.top_p = MUSICGEN_DEFAULTS.top_p
            params.temperature = MUSICGEN_DEFAULTS.temperature

        params.workflow_name = MUSIC_CONTINUE_WORKFLOW
        params.duration = None
        params.snd_filename = self.sound_fnames[index]
        params.vid_filename = None

        modal = AudioEditModal(params, "extend")
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Info", style=discord.ButtonStyle.blurple, emoji="ℹ️", row=0)
    async def info(self, interaction, button):
        params = self.params
        # info_str = (
        #     f"prompt: {params.prompt}\n"
        #     f"cfg: {params.cfg or 'default'}\n"
        #     f"seed: {params.seed}\n"
        # )
        info_str = str(self.params)
        await interaction.response.send_message(info_str, ephemeral=True)


class AudioEditModal(ui.Modal, title="Edit/Extend Sound"):
    def __init__(self, params: AudioWorkflow, command: str):
        super().__init__(timeout=120)
        self.params = params
        self.command = command

        self.prompt = ui.TextInput(label="Prompt", placeholder="Enter a prompt", max_length=256, required=False, default=self.params.prompt or "")
        self.cfg = ui.TextInput(label="Guidance Scale", placeholder="Controls audio's conformance to text prompt; default 3.0", default=str(self.params.cfg))
        self.temperature = ui.TextInput(
            label="Temperature", placeholder="Controls randomness during prediction; default 1.0", default=str(self.params.temperature)
        )
        self.top_p = ui.TextInput(label="Top p", placeholder="", default=str(self.params.top_p))
        self.top_k = ui.TextInput(label="Top k", placeholder="Number of tokens to ", default=str(self.params.top_k))

        self.add_item(self.prompt)
        self.add_item(self.cfg)
        self.add_item(self.temperature)
        self.add_item(self.top_p)
        self.add_item(self.top_k)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("Generating audio with new parameters, this shouldn't take too long...")

        params = deepcopy(self.params)
        try:
            params.prompt = self.prompt.value
            params.cfg = float(self.cfg.value)
            params.temperature = float(self.temperature.value)
            params.top_p = float(self.top_p.value)
            params.top_k = int(self.top_k.value)
        except ValueError:
            interaction.response.send_message(
                "An error occurred while parsing a value you entered. Please check your inputs and try your request again.",
                ephemeral=True,
            )

        if params.seed is None:
            params.seed = random.randint(0, 999999999999999)

        (videos, _, sound_fnames) = await extend_audio(params)

        verbed = "extended" if self.command == "extend" else "remixed"
        final_message = f"{interaction.user.mention} here is your {verbed} audio"
        buttons = AudioButtons(params, sound_fnames, command=self.command)

        files = [discord.File(fp=BytesIO(v), filename=f"sound_{i}.webm") for i, v in enumerate(videos)]
        await interaction.channel.send(content=final_message, files=files, view=buttons)
