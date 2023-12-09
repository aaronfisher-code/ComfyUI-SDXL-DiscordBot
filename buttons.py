import discord
import discord.ext
import random

from datetime import datetime
from imageGen import generate_images, upscale_image, generate_alternatives
from utils import create_collage, create_gif_collage


class ImageButton(discord.ui.Button):
    def __init__(self, label, emoji, row, callback):
        super().__init__(label=label, style=discord.ButtonStyle.grey, emoji=emoji, row=row)
        self._callback = callback

    async def callback(self, interaction: discord.Interaction):
        await self._callback(interaction, self)


class Buttons(discord.ui.View):
    def __init__(
            self,
            prompt,
            negative_prompt,
            model,
            lora_list,
            lora_strengths,
            enhance,
            images,
            author,
            config=None,
            *,
            aspect_ratio=None,
            num_steps=None,
            cfg_scale=None,
            timeout=None,
            command=None,
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
        self.aspect_ratio = aspect_ratio
        self.num_steps = num_steps
        self.cfg_scale = cfg_scale
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

        # TODO: should alternatives use num_steps and cfg_scale from original?
        # Buttons should probably still receive these params for rerolls
        images = await generate_alternatives(self.images[index], self.prompt, self.negative_prompt, self.model,
                                             self.lora_list, self.lora_strengths, sdxl_config, seed=seed
                                             )
        collage_path = create_collage(images)
        final_message = f"{interaction.user.mention} here are your alternative images"
        buttons = Buttons(self.prompt,
                          self.negative_prompt,
                          self.model,
                          self.lora_list,
                          self.lora_strengths,
                          self.enhance,
                          images,
                          self.author,
                          self.config,
                          num_steps=self.num_steps,
                          cfg_scale=self.cfg_scale,
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

    @discord.ui.button(label="Re-roll", style=discord.ButtonStyle.green, emoji="🎲", row=0)
    async def reroll_image(self, interaction, btn):
        await interaction.response.send_message(
            f"{interaction.user.mention} asked me to re-imagine \"{self.prompt}\", this shouldn't take too long..."
        )
        btn.disabled = True
        await interaction.message.edit(view=self)

        seed = random.randint(0, 999999999999999)

        # Generate a new image with the same prompt
        images, enhanced_prompt = await generate_images(
            self.prompt,
            self.negative_prompt,
            self.model,
            self.lora_list,
            self.lora_strengths,
            self.aspect_ratio,
            self.num_steps,
            self.cfg_scale,
            seed,
            self.config,
        )

        # Construct the final message with user mention
        final_message = f"{interaction.user.mention} asked me to re-imagine \"{self.prompt}\", here is what I imagined for them. Seed: {seed}"
        buttons = Buttons(self.prompt, self.negative_prompt, self.model, self.lora_list, self.lora_strengths,
                          self.enhance, images, self.author, self.config, aspect_ratio=self.aspect_ratio,
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
