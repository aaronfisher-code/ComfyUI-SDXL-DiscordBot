import random
from copy import deepcopy
from datetime import datetime

import discord
import discord.ext
from discord import ui

from imageGen import ImageWorkflow, generate_images, upscale_image, generate_alternatives
from collage_utils import create_collage, create_gif_collage
from consts import *
from util import should_filter, get_filename, build_command


class ImageButton(discord.ui.Button):
    def __init__(self, label, emoji, row, callback):
        super().__init__(label=label, style=discord.ButtonStyle.grey, emoji=emoji, row=row)
        self._callback = callback

    async def callback(self, interaction: discord.Interaction):
        await self._callback(interaction, self)


class Buttons(discord.ui.View):
    def __init__(
            self,
            params,
            images,
            author,
            *,
            timeout=None,
            command=None,
    ):
        super().__init__(timeout=timeout)
        self.params = params
        self.images = images
        self.author = author
        self.command = command

        self.is_sdxl = command == "sdxl"
        self.is_video = command == "video"

        # upscaling/alternative buttons not needed for video
        if self.is_video:
            return

        total_buttons = len(images) * 2 + 1  # For both alternative and upscale buttons + re-roll button
        if total_buttons > 25:  # Limit to 25 buttons
            images = images[:12]  # Adjust to only use the first 12 images

        # Determine if re-roll button should be on its own row
        reroll_row = 1 if total_buttons <= 21 else 0

        # Dynamically add alternative buttons
        for idx, _ in enumerate(images):
            row = (idx + 1) // 5 + reroll_row  # Determine row based on index and re-roll row
            btn = ImageButton(f"V{idx + 1}", "♻️", row, self.generate_alternatives_and_send)
            self.add_item(btn)

        # Dynamically add upscale buttons
        for idx, _ in enumerate(images):
            # Determine row based on index, number of alternative buttons, and re-roll row
            row = (idx + len(images) + 1) // 5 + reroll_row
            btn = ImageButton(f"U{idx + 1}", "⬆️", row, self.upscale_and_send)
            self.add_item(btn)

        # Dynamically add download buttons
        for idx, _ in enumerate(images):
            # Determine row based on index, number of alternative buttons, and re-roll row
            row = (idx + (len(images) * 2) + 2) // 5 + reroll_row
            btn = ImageButton(f"D{idx + 1}", "💾", row, self.download_image)
            self.add_item(btn)

        # removed until the upscale flow is fixed
        # Add upscale with added detail buttons
        # for idx, _ in enumerate(images):
        #    row = (idx + (len(images) * 2) + 2) // 5 + reroll_row
        #    btn = ImageButton(f"U{idx + 1}", "🔎", row, self.upscale_and_send_with_detail)
        #    self.add_item(btn)

    async def generate_alternatives_and_send(self, interaction, button):
        index = int(button.label[1:]) - 1  # Extract index from label
        await interaction.response.send_message(f"{interaction.user.mention} asked for some alternatives of image #{index + 1}, this shouldn't take too long...")

        params = deepcopy(self.params)
        params.workflow_name = SDXL_ALTS_WORKFLOW if self.is_sdxl else SD15_ALTS_WORKFLOW
        params.seed = random.randint(0, 999999999999999)

        # TODO: should alternatives use num_steps and cfg_scale from original?
        # Buttons should probably still receive these params for rerolls
        images = await generate_alternatives(params, self.images[index])
        collage_path = create_collage(images)
        final_message = f"{interaction.user.mention} here are your alternative images"

        buttons = Buttons(params, images, self.author, command=self.command)

        # if a gif, set filename as gif, otherwise png
        fname = "collage.gif" if images[0].format == "GIF" else "collage.png"
        await interaction.channel.send(
            content=final_message, file=discord.File(fp=collage_path, filename=fname), view=buttons
        )

    async def upscale_and_send(self, interaction, button):
        index = int(button.label[1:]) - 1  # Extract index from label
        await interaction.response.send_message(f"{interaction.user.mention} asked for an upscale of image #{index + 1}, this shouldn't take too long...")

        params = deepcopy(self.params)
        params.workflow_name = UPSCALE_WORKFLOW
        upscaled_image = await upscale_image(self.images[index])
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        upscaled_image_path = f"./out/upscaledImage_{timestamp}.png"
        upscaled_image.save(upscaled_image_path)
        final_message = f"{interaction.user.mention} here is your upscaled image"
        buttons = AddDetailButtons(params, upscaled_image, is_sdxl=self.is_sdxl)
        fp = f"{get_filename(interaction, self.params)}_{index}.png"
        await interaction.channel.send(
            content=final_message,
            file=discord.File(fp=upscaled_image_path, filename=fp),
            view=buttons
        )

    async def upscale_and_send_with_detail(self, interaction, button):
        index = int(button.label[1:]) - 1
        await interaction.response.send_message(
            "Upscaling and increasing detail in the image, this shouldn't take too long..."
        )

        upscaled_image = await upscale_image(self.images[index])
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        upscaled_image_path = f"./out/upscaledImage_{timestamp}.png"
        upscaled_image.save(upscaled_image_path)
        final_message = f"{interaction.user.mention} here is your upscaled image"
        await interaction.channel.send(
            content=final_message, file=discord.File(fp=upscaled_image_path, filename="upscaled_image.png")
        )

    @discord.ui.button(label="Edit", style=discord.ButtonStyle.blurple, emoji="📝", row=0)
    async def edit_image(self, interaction, button):
        modal = EditModal(self.params, self.command)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Re-roll", style=discord.ButtonStyle.green, emoji="🎲", row=0)
    async def reroll_image(self, interaction, btn):
        await interaction.response.send_message(
            f'{interaction.user.mention} asked me to re-imagine "{self.params.prompt}", this shouldn\'t take too long...'
        )
        btn.disabled = True
        await interaction.message.edit(view=self)

        params = deepcopy(self.params)
        if self.is_sdxl:
            params.workflow_name = SDXL_WORKFLOW
        elif self.is_video:
            params.workflow_name = VIDEO_WORKFLOW
        else:
            params.workflow_name = SD15_WORKFLOW
        params.filename = None
        params.seed = random.randint(0, 999999999999999)

        # Generate a new image with the same prompt
        images, enhanced_prompt = await generate_images(params)

        if self.is_video:
            collage = create_gif_collage(images)
            fname = "collage.gif"
        else:
            collage = create_collage(images)
            fname = "collage.png"

        # Construct the final message with user mention
        final_message = (
            f'{interaction.user.mention} asked me to re-imagine "{params.prompt}", here is what I imagined for them. '
            f"Seed: {params.seed}"
        )
        buttons = Buttons(params, images, self.author, command=self.command)

        await interaction.channel.send(
            content=final_message, file=discord.File(fp=collage, filename=fname), view=buttons
        )

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.red, emoji="🗑️", row=0)
    async def delete_image_post(self, interaction, button):
        # make sure the user is the one who posted the image
        if interaction.user.id != self.author.id:
            return

        await interaction.message.delete()

    @discord.ui.button(label="Info", style=discord.ButtonStyle.blurple, emoji="ℹ️", row=0)
    async def image_info(self, interaction, button):
        params = self.params
        info_str = (
            f"prompt: {params.prompt}\n"
            f"negative prompt: {params.negative_prompt}\n"
            f"model: {params.model or 'default'}\n"
            f"loras: {params.loras}\n"
            f"lora strengths: {params.lora_strengths}\n"
            f"aspect ratio: {params.aspect_ratio or 'default'}\n"
            f"sampler: {params.sampler or 'default'}\n"
            f"num steps: {params.num_steps or 'default'}\n"
            f"cfg scale: {params.cfg_scale or 'default'}\n"
            f"seed: {params.seed}\n"
            f"```{build_command(params)}```"
        )
        await interaction.response.send_message(info_str, ephemeral=True)

    async def download_image(self, interaction, button):
        index = int(button.label[1:]) - 1
        file_name = f"{get_filename(interaction, self.params)}_{index}.png"
        fp = f"./out/images_{file_name}"
        self.images[index].save(fp)
        await interaction.response.send_message(f"{interaction.user.mention}, here is your image!",
                                                file=discord.File(fp=fp, filename=file_name)
                                                )


class AddDetailButtons(discord.ui.View):
    def __init__(self, params, images, *, timeout=None, is_sdxl=False):
        super().__init__(timeout=timeout)
        self.params = params
        self.images = images
        self.is_sdxl = is_sdxl

        self.add_item(ImageButton("Add Detail", "🔎", 0, self.add_detail))

    async def add_detail(self, interaction, button):
        await interaction.response.send_message("Increasing detail in the image, this shouldn't take too long...")

        # do img2img
        params = deepcopy(self.params)
        params.workflow_name = SDXL_DETAIL_WORKFLOW if self.is_sdxl else SD15_DETAIL_WORKFLOW
        params.denoise_strength = None
        params.seed = random.randint(0, 999999999999999)
        params.batch_size = 1

        images = await generate_alternatives(params, self.images)
        collage_path = create_collage(images)
        final_message = f"{interaction.user.mention} here is your image with more detail"

        fp = f"{get_filename(interaction, self.params)}_detail.png"

        await interaction.channel.send(content=final_message,
                                       file=discord.File(fp=collage_path, filename=fp)
                                       )


class EditModal(ui.Modal, title="Edit Image"):
    def __init__(self, params: ImageWorkflow, command: str):
        super().__init__(timeout=120)
        self.params = params
        self.command = command

        self.is_sdxl = command == "sdxl"
        self.is_video = command == "video"

        self.prompt = ui.TextInput(label="Prompt",
                                   placeholder="Enter a prompt",
                                   min_length=1,
                                   max_length=2048,
                                   default=self.params.prompt
                                   )
        self.negative_prompt = ui.TextInput(label="Negative Prompt",
                                            placeholder="Enter a negative prompt",
                                            required=False,
                                            default=self.params.negative_prompt
                                            )
        self.num_steps = ui.TextInput(label="Number of Steps",
                                      placeholder="Enter a number of steps",
                                      default=str(self.params.num_steps)
                                      )
        self.cfg_scale = ui.TextInput(label="Guidance Scale",
                                      placeholder="Enter a CFG scale",
                                      default=str(self.params.cfg_scale)
                                      )
        self.seed = ui.TextInput(label="Seed",
                                 placeholder="Enter a seed",
                                 required=False,
                                 default=str(self.params.seed)
                                 )

        self.add_item(self.prompt)
        self.add_item(self.negative_prompt)
        self.add_item(self.num_steps)
        self.add_item(self.cfg_scale)
        self.add_item(self.seed)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("Generating image with new parameters, this shouldn't take too long...")

        params = deepcopy(self.params)
        params.prompt = self.prompt.value
        params.negative_prompt = self.negative_prompt.value
        params.num_steps = int(self.num_steps.value)
        params.cfg_scale = float(self.cfg_scale.value)
        params.seed = int(self.seed.value) if self.seed.value else None

        if params.seed is None:
            params.seed = random.randint(0, 999999999999999)

        images, enhanced_prompt = await generate_images(params)

        # Construct the final message with user mention
        final_message = f"{interaction.user.mention} asked me to re-imagine \"{self.prompt}\", here is what I imagined for them. Seed: {self.params.seed}"
        buttons = Buttons(
            params,
            images,
            interaction.user,
            command=self.command
        )

        if self.is_video:
            collage = create_gif_collage(images)
            fname = "collage.gif"
        else:
            collage = create_collage(images)
            fname = "collage.png"

        await interaction.channel.send(content=final_message,
                                       file=discord.File(fp=collage, filename=fname),
                                       view=buttons
                                       )

    async def interaction_check(self, interaction: discord.Interaction, /) -> bool:
        if self.num_steps.value.isnumeric() == False:
            await self.on_error(interaction, Exception("Number of steps must be an integer"))
            return False

        if self.cfg_scale.value.replace(".", "").isnumeric() == False:
            await self.on_error(interaction, Exception("CFG scale must be a float"))
            return False

        if int(self.num_steps.value) < 0 or int(self.num_steps.value) > MAX_STEPS:
            await self.on_error(interaction, Exception(f"Number of steps must be between 0 and {MAX_STEPS}"))
            return False

        if float(self.cfg_scale.value) < 1 or float(self.cfg_scale.value) > MAX_CFG:
            await self.on_error(interaction, Exception(f"CFG scale must be between 1 and {MAX_CFG}"))
            return False

        if self.seed.value != None and self.seed.value != "" and int(self.seed.value) > 1 << 50:
            await self.on_error(interaction, Exception("Seed must be less than 2^50"))
            return False

        return True
