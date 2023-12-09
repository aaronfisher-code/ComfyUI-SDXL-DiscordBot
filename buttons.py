import discord
import discord.ext
import random

from datetime import datetime
from discord import ui
from copy import deepcopy

from param_types import PromptParams, ModelParams, ImageParams, SamplerParams, WorkflowParams
from imageGen import generate_images, upscale_image, generate_alternatives
from collage_utils import create_collage, create_gif_collage


class ImageButton(discord.ui.Button):
    def __init__(self, label, emoji, row, callback):
        super().__init__(label=label, style=discord.ButtonStyle.grey, emoji=emoji, row=row)
        self._callback = callback

    async def callback(self, interaction: discord.Interaction):
        await self._callback(interaction, self)


class Buttons(discord.ui.View):
    def __init__(
            self,
            prompt_params: PromptParams,
            model_params: ModelParams,
            image_params: ImageParams,
            sampler_params: SamplerParams,
            workflow_params: WorkflowParams,
            images,
            author,
            timeout=None,
            command=None,
    ):
        super().__init__(timeout=timeout)
        self.prompt_params = deepcopy(prompt_params)
        self.model_params = deepcopy(model_params)
        self.image_params = deepcopy(image_params)
        self.sampler_params = deepcopy(sampler_params)
        self.workflow_params = deepcopy(workflow_params)
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
            row = (idx + len(
                images
            ) + 1) // 5 + reroll_row  # Determine row based on index, number of alternative buttons, and re-roll row
            btn = ImageButton(f"U{idx + 1}", "⬆️", row, self.upscale_and_send)
            self.add_item(btn)

        # removed until the upscale flow is fixed
        # Add upscale with added detail buttons
        # for idx, _ in enumerate(images):
        #    row = (idx + (len(images) * 2) + 2) // 5 + reroll_row
        #    btn = ImageButton(f"U{idx + 1}", "🔎", row, self.upscale_and_send_with_detail)
        #    self.add_item(btn)

    async def generate_alternatives_and_send(self, interaction, button):
        sdxl_config = "LOCAL_SDXL_IMG2IMG_CONFIG" if self.is_sdxl else "LOCAL_IMG2IMG"

        index = int(button.label[1:]) - 1  # Extract index from label
        await interaction.response.send_message("Creating some alternatives, this shouldn't take too long...")

        seed = random.randint(0, 999999999999999)
        self.sampler_params.seed = seed

        # TODO: should alternatives use num_steps and cfg_scale from original?
        # Buttons should probably still receive these params for rerolls
        images = await generate_alternatives(self.images[index],
                                             self.prompt,
                                             self.negative_prompt,
                                             self.model,
                                             self.lora_list,
                                             self.lora_strengths,
                                             sdxl_config,
                                             seed=self.sampler_params.seed
                                             )
        collage_path = create_collage(images)
        final_message = f"{interaction.user.mention} here are your alternative images"
        buttons = Buttons(
            self.prompt_params,
            self.model_params,
            self.image_params,
            self.sampler_params,
            self.workflow_params,
            images,
            self.author,
            self.workflow_params.config,
            command=self.command
        )

        # if a gif, set filename as gif, otherwise png
        fname = "collage.gif" if images[0].format == 'GIF' else "collage.png"
        await interaction.channel.send(content=final_message, file=discord.File(fp=collage_path, filename=fname),
                                       view=buttons
                                       )

    async def upscale_and_send(self, interaction, button):
        index = int(button.label[1:]) - 1  # Extract index from label
        await interaction.response.send_message("Upscaling the image, this shouldn't take too long...")
        upscaled_image = await upscale_image(self.images[index])
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        upscaled_image_path = f"./out/upscaledImage_{timestamp}.png"
        upscaled_image.save(upscaled_image_path)
        final_message = f"{interaction.user.mention} here is your upscaled image"
        buttons = AddDetailButtons(self.prompt, self.negative_prompt, self.model, self.lora_list, self.lora_strengths,
                                   self.enhance, upscaled_image, self.config, is_sdxl=self.is_sdxl
                                   )
        await interaction.channel.send(content=final_message,
                                       file=discord.File(fp=upscaled_image_path, filename='upscaled_image.png'),
                                       view=buttons
                                       )

    async def upscale_and_send_with_detail(self, interaction, button):
        # sdxl_config = "LOCAL_UPSCALE_SDXL" if self.is_sdxl else "LOCAL_UPSCALE"
        index = int(button.label[1:]) - 1
        await interaction.response.send_message(
            "Upscaling and increasing detail in the image, this shouldn't take too long..."
        )
        upscaled_image = await upscale_image(self.images[index])
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        upscaled_image_path = f"./out/upscaledImage_{timestamp}.png"
        upscaled_image.save(upscaled_image_path)
        final_message = f"{interaction.user.mention} here is your upscaled image"
        await interaction.channel.send(content=final_message,
                                       file=discord.File(fp=upscaled_image_path, filename='upscaled_image.png')
                                       )

    @discord.ui.button(label="Edit", style=discord.ButtonStyle.blurple, emoji="📝", row=0)
    async def edit_image(self, interaction, button):
        modal = EditModal(self.prompt_params,
                          self.model_params,
                          self.image_params,
                          self.sampler_params,
                          self.workflow_params,
                          self.command
                          )
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Re-roll", style=discord.ButtonStyle.green, emoji="🎲", row=0)
    async def reroll_image(self, interaction, btn):
        await interaction.response.send_message(
            f"{interaction.user.mention} asked me to re-imagine \"{self.prompt_params.prompt}\", this shouldn't take too long..."
        )
        btn.disabled = True
        await interaction.message.edit(view=self)

        seed = random.randint(0, 999999999999999)
        self.sampler_params.seed = seed

        lora_list = [self.model_params.lora, self.model_params.lora2, self.model_params.lora3]
        lora_strengths = [self.model_params.lora_strength, self.model_params.lora_strength2,
                          self.model_params.lora_strength3
                          ]

        # Generate a new image with the same prompt
        images, enhanced_prompt = await generate_images(
            self.prompt_params.prompt,
            self.prompt_params.negative_prompt,
            self.model_params.model,
            lora_list,
            lora_strengths,
            self.image_params.aspect_ratio,
            self.sampler_params.num_steps,
            self.sampler_params.cfg_scale,
            self.sampler_params.seed,
            self.workflow_params.config,
        )

        # Construct the final message with user mention
        final_message = f"{interaction.user.mention} asked me to re-imagine \"{self.prompt_params.prompt}\", here is what I imagined for them. Seed: {self.sampler_params.seed}"
        buttons = Buttons(
            self.prompt_params,
            self.model_params,
            self.image_params,
            self.sampler_params,
            self.workflow_params,
            images,
            self.author,
            command=self.command
        )

        if self.is_video:
            collage = create_gif_collage(images)
            fname = "collage.gif"
        else:
            collage = create_collage(images)
            fname = "collage.png"

        await interaction.channel.send(content=final_message, file=discord.File(fp=collage, filename=fname),
                                       view=buttons
                                       )

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.red, emoji="🗑️", row=0)
    async def delete_image_post(self, interaction, button):
        # make sure the user is the one who posted the image
        if interaction.user.id != self.author.id:
            return

        await interaction.message.delete()


class EditModal(ui.Modal, title="Edit Image"):
    def __init__(self, prompt_params: PromptParams,
                 model_params: ModelParams,
                 image_params: ImageParams,
                 sampler_params: SamplerParams,
                 workflow_params: WorkflowParams,
                 command: str
                 ):
        super().__init__(timeout=120)
        self.prompt_params = deepcopy(prompt_params)
        self.model_params = deepcopy(model_params)
        self.image_params = deepcopy(image_params)
        self.sampler_params = deepcopy(sampler_params)
        self.workflow_params = deepcopy(workflow_params)
        self.command = command

        self.is_sdxl = command == "sdxl"
        self.is_video = command == "video"

        self.prompt = ui.TextInput(label="Prompt",
                                   placeholder="Enter a prompt",
                                   min_length=1,
                                   max_length=256,
                                   default=self.prompt_params.prompt
                                   )
        self.negative_prompt = ui.TextInput(label="Negative Prompt",
                                            placeholder="Enter a negative prompt",
                                            required=False,
                                            default=self.prompt_params.negative_prompt
                                            )
        self.num_steps = ui.TextInput(label="Number of Steps",
                                      placeholder="Enter a number of steps",
                                      default=str(self.sampler_params.num_steps)
                                      )
        self.cfg_scale = ui.TextInput(label="Guidance Scale",
                                      placeholder="Enter a CFG scale",
                                      default=str(self.sampler_params.cfg_scale)
                                      )
        self.seed = ui.TextInput(label="Seed",
                                 placeholder="Enter a seed",
                                 required=False,
                                 default=str(self.sampler_params.seed)
                                 )

        self.add_item(self.prompt)
        self.add_item(self.negative_prompt)
        self.add_item(self.num_steps)
        self.add_item(self.cfg_scale)
        self.add_item(self.seed)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("Generating image with new parameters, this shouldn't take too long...")

        self.prompt_params.prompt = self.prompt.value
        self.prompt_params.negative_prompt = self.negative_prompt.value
        self.sampler_params.num_steps = int(self.num_steps.value)
        self.sampler_params.cfg_scale = float(self.cfg_scale.value)
        self.sampler_params.seed = int(self.seed.value) if self.seed.value else None


        lora_list = [self.model_params.lora, self.model_params.lora2, self.model_params.lora3]
        lora_strengths = [self.model_params.lora_strength, self.model_params.lora_strength2,
                          self.model_params.lora_strength3
                          ]

        if self.sampler_params.seed is None:
            self.sampler_params.seed = random.randint(0, 999999999999999)

        images, enhanced_prompt = await generate_images(
            self.prompt_params.prompt,
            self.prompt_params.negative_prompt,
            self.model_params.model,
            lora_list,
            lora_strengths,
            self.image_params.aspect_ratio,
            self.sampler_params.num_steps,
            self.sampler_params.cfg_scale,
            self.sampler_params.seed,
            self.workflow_params.config,
        )

        # Construct the final message with user mention
        final_message = f"{interaction.user.mention} asked me to re-imagine \"{self.prompt}\", here is what I imagined for them. Seed: {self.sampler_params.seed}"
        buttons = Buttons(
            self.prompt_params,
            self.model_params,
            self.image_params,
            self.sampler_params,
            self.workflow_params,
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

        await interaction.channel.send(content=final_message, file=discord.File(fp=collage, filename=fname),
                                       view=buttons
                                       )


class AddDetailButtons(discord.ui.View):
    def __init__(self, prompt, negative_prompt, model, lora_list, lora_strengths, enhance, images, config=None, *,
                 timeout=None, is_sdxl=False
                 ):
        super().__init__(timeout=timeout)
        self.prompt = prompt
        self.negative_prompt = negative_prompt
        self.model = model
        self.lora_list = lora_list
        self.lora_strengths = lora_strengths
        self.enhance = enhance
        self.images = images
        self.config = config
        self.is_sdxl = is_sdxl

        self.add_item(ImageButton("Add Detail", "🔎", 0, self.add_detail))

    async def add_detail(self, interaction, button):
        # do img2img
        if self.is_sdxl:
            sdxl_config = "LOCAL_SDXL_ADD_DETAIL_CONFIG"
        else:
            sdxl_config = "LOCAL_IMG2IMG"

        await interaction.response.send_message("Increasing detail in the image, this shouldn't take too long...")

        seed = random.randint(0, 999999999999999)

        images = await generate_alternatives(
            self.images,
            self.prompt,
            self.negative_prompt,
            self.model,
            self.lora_list,
            self.lora_strengths,
            sdxl_config,
            denoise_strength=0.45,
            seed=seed,
        )
        collage_path = create_collage(images)
        final_message = f"{interaction.user.mention} here is your image with more detail"

        await interaction.channel.send(content=final_message,
                                       file=discord.File(fp=collage_path, filename='collage.png')
                                       )
