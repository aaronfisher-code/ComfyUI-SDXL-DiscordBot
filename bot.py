import discord
import discord.ext
from discord import app_commands
import configparser
import os
from PIL import Image
from copy import deepcopy
from datetime import datetime
from math import ceil, sqrt
import random

from discord.app_commands import Choice, Range


def setup_config():
    if not os.path.exists("config.properties"):
        generate_default_config()

    if not os.path.exists("./out"):
        os.makedirs("./out")

    config = configparser.ConfigParser()
    config.read("config.properties")
    return config["BOT"]["TOKEN"], config["BOT"]["SDXL_SOURCE"]


def generate_default_config():
    config = configparser.ConfigParser()
    config["DISCORD"] = {"TOKEN": "YOUR_DEFAULT_DISCORD_BOT_TOKEN"}
    config["LOCAL"] = {"SERVER_ADDRESS": "YOUR_COMFYUI_URL"}
    config["API"] = {
        "API_KEY": "STABILITY_AI_API_KEY",
        "API_HOST": "https://api.stability.ai",
        "API_IMAGE_ENGINE": "STABILITY_AI_IMAGE_GEN_MODEL",
    }
    with open("config.properties", "w") as configfile:
        config.write(configfile)


def should_filter(positive_prompt: str, negative_prompt: str) -> bool:
    positive_prompt = positive_prompt or ""
    negative_prompt = negative_prompt or ""

    config = configparser.ConfigParser()
    config.read("config.properties")
    word_list = config["BLOCKED_WORDS"]["WORDS"].split(",")
    if word_list is None:
        print("No blocked words found in config.properties")
        return False
    for word in word_list:
        if word.lower() in positive_prompt.lower() or word in negative_prompt.lower():
            return True
    return False


def create_gif_collage(images):
    num_images = len(images)
    num_cols = ceil(sqrt(num_images))
    num_rows = ceil(num_images / num_cols)
    collage_width = max(image.width for image in images) * num_cols
    collage_height = max(image.height for image in images) * num_rows
    collage = Image.new("RGB", (collage_width, collage_height))
    collage.n_frames = images[0].n_frames

    for idx, image in enumerate(images):
        row = idx // num_cols
        col = idx % num_cols
        x_offset = col * image.width
        y_offset = row * image.height
        collage.paste(image, (x_offset, y_offset))

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    collage_path = f"./out/images_{timestamp}.gif"
    images[0].save(collage_path, save_all=True, append_images=images[1:], duration=125, loop=0)

    return collage_path


def create_collage(images):
    if len(images) == 0:
        print("Error: No images to make collage")
        return None

    if images[0].format == "GIF":
        return create_gif_collage(images)

    num_images = len(images)
    num_cols = ceil(sqrt(num_images))
    num_rows = ceil(num_images / num_cols)
    collage_width = max(image.width for image in images) * num_cols
    collage_height = max(image.height for image in images) * num_rows
    collage = Image.new("RGB", (collage_width, collage_height))

    for idx, image in enumerate(images):
        row = idx // num_cols
        col = idx % num_cols
        x_offset = col * image.width
        y_offset = row * image.height
        collage.paste(image, (x_offset, y_offset))

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    collage_path = f"./out/images_{timestamp}.png"
    collage.save(collage_path)

    return collage_path


# setting up the bot
TOKEN, IMAGE_SOURCE = setup_config()
intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)


if IMAGE_SOURCE == "LOCAL":
    from imageGen import (
        PromptParams,
        generate_alternatives,
        generate_images,
        get_models,
        get_loras,
        upscale_image,
    )
elif IMAGE_SOURCE == "API":
    from apiImageGen import generate_images, upscale_image, generate_alternatives


models = get_models()
loras = get_loras()


SD15_WORKFLOW = "LOCAL_TXT2IMG"
SD15_LLM_WORKFLOW = "LOCAL_TXT2IMG_LLM"
SD15_ALTS_WORKFLOW = "LOCAL_IMG2IMG"
SD15_DETAIL_WORKFLOW = "LOCAL_IMG2IMG"
UPSCALE_WORKFLOW = "LOCAL_UPSCALE"

SDXL_WORKFLOW = "LOCAL_TXT2IMG_SDXL"
SDXL_LLM_WORKFLOW = "LOCAL_TXT2IMG_LLM_SDXL"
SDXL_ALTS_WORKFLOW = "LOCAL_IMG2IMG_SDXL"
SDXL_DETAIL_WORKFLOW = "LOCAL_DETAIL_SDXL"
SDXL_UPSCALE_WORKFLOW = "LOCAL_UPSCALE_SDXL"

VIDEO_WORKFLOW = "LOCAL_TXT2VID"

# These aspect ratio resolution values correspond to the SDXL Empty Latent Image node.
# A latent modification node in the workflow converts it to the equivalent SD 1.5 resolution values.
ASPECT_RATIO_CHOICES = [
    Choice(name="1:1", value="1024 x 1024  (square)"),
    Choice(name="7:9 portrait", value=" 896 x 1152  (portrait)"),
    Choice(name="4:7 portrait", value=" 768 x 1344  (portrait)"),
    Choice(name="9:7 landscape", value="1152 x 896   (landscape)"),
    Choice(name="7:4 landscape", value="1344 x 768   (landscape)"),
]
SD15_MODEL_CHOICES = [Choice(name=m, value=m) for m in models[0] if "xl" not in m.lower()][:25]
SD15_LORA_CHOICES = [Choice(name=l, value=l) for l in loras[0] if "xl" not in l.lower()][:25]
SDXL_MODEL_CHOICES = [Choice(name=m, value=m) for m in models[0] if "xl" in m.lower() and "refiner" not in m.lower()][:25]
SDXL_LORA_CHOICES = [Choice(name=l, value=l) for l in loras[0] if "xl" in l.lower()][:25]


# sync the slash command to your server
@client.event
async def on_ready():
    await tree.sync()
    print(f"Logged in as {client.user.name} ({client.user.id})")


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

        # removed until the upscale flow is fixed
        # Add upscale with added detail buttons
        # for idx, _ in enumerate(images):
        #    row = (idx + (len(images) * 2) + 2) // 5 + reroll_row
        #    btn = ImageButton(f"U{idx + 1}", "🔎", row, self.upscale_and_send_with_detail)
        #    self.add_item(btn)

    async def generate_alternatives_and_send(self, interaction, button):
        index = int(button.label[1:]) - 1  # Extract index from label
        await interaction.response.send_message("Creating some alternatives, this shouldn't take too long...")

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
        await interaction.response.send_message("Upscaling the image, this shouldn't take too long...")

        params = deepcopy(self.params)
        params.workflow_name = UPSCALE_WORKFLOW
        upscaled_image = await upscale_image(self.images[index])
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        upscaled_image_path = f"./out/upscaledImage_{timestamp}.png"
        upscaled_image.save(upscaled_image_path)
        final_message = f"{interaction.user.mention} here is your upscaled image"
        buttons = AddDetailButtons(params, upscaled_image, is_sdxl=self.is_sdxl)
        await interaction.channel.send(
            content=final_message, file=discord.File(fp=upscaled_image_path, filename="upscaled_image.png"), view=buttons
        )

    async def upscale_and_send_with_detail(self, interaction, button):
        index = int(button.label[1:]) - 1
        await interaction.response.send_message("Upscaling and increasing detail in the image, this shouldn't take too long...")

        upscaled_image = await upscale_image(self.images[index])
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        upscaled_image_path = f"./out/upscaledImage_{timestamp}.png"
        upscaled_image.save(upscaled_image_path)
        final_message = f"{interaction.user.mention} here is your upscaled image"
        await interaction.channel.send(
            content=final_message, file=discord.File(fp=upscaled_image_path, filename="upscaled_image.png")
        )

    @discord.ui.button(label="Re-roll", style=discord.ButtonStyle.green, emoji="🎲", row=0)
    async def reroll_image(self, interaction, btn):
        await interaction.response.send_message(
            f'{interaction.user.mention} asked me to re-imagine "{self.params.prompt}", this shouldn\'t take too long...'
        )
        btn.disabled = True
        await interaction.message.edit(view=self)

        params = deepcopy(self.params)
        params.workflow_name = SDXL_WORKFLOW if self.is_sdxl else SD15_WORKFLOW
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
        params.denoise_strength = 0.45
        params.seed = random.randint(0, 999999999999999)

        images = await generate_alternatives(params, self.images)
        collage_path = create_collage(images)
        final_message = f"{interaction.user.mention} here is your image with more detail"

        await interaction.channel.send(content=final_message, file=discord.File(fp=collage_path, filename="collage.png"))


@tree.command(name="imagine", description="Generate an image based on input text")
@app_commands.describe(
    prompt="Prompt for the image being generated",
    negative_prompt="Prompt for what you want to steer the AI away from",
    model="Model checkpoint to use",
    lora="LoRA to apply",
    lora_strength="Strength of LoRA",
    num_steps="Number of sampling steps; range [1, 30]",
    cfg_scale="Degree to which AI should follow prompt; range [1.0, 10.0]",
    # enhance='Enhance the image using a language model',
    aspect_ratio="Aspect ratio of the generated image",
)
@app_commands.choices(
    model=SD15_MODEL_CHOICES,
    lora=SD15_LORA_CHOICES,
    lora2=SD15_LORA_CHOICES,
    lora3=SD15_LORA_CHOICES,
    aspect_ratio=ASPECT_RATIO_CHOICES,
)
async def slash_command(
    interaction: discord.Interaction,
    prompt: str,
    negative_prompt: str = None,
    model: str = None,
    lora: Choice[str] = None,
    lora_strength: float = 1.0,
    lora2: Choice[str] = None,
    lora_strength2: float = 1.0,
    lora3: Choice[str] = None,
    lora_strength3: float = 1.0,
    # enhance: bool = False,
    aspect_ratio: str = None,
    num_steps: Range[int, 1, 30] = None,
    cfg_scale: Range[float, 1.0, 10.0] = None,
    seed: int = None
):
    if should_filter(prompt, negative_prompt):
        print(
            f"Prompt or negative prompt contains a blocked word, not generating image. "
            f"Prompt: {prompt}, Negative Prompt: {negative_prompt}"
        )
        await interaction.response.send_message(
            f"The prompt {prompt} or negative prompt {negative_prompt} contains a blocked word, not generating image.",
            ephemeral=True,
        )
        return

    # Send an initial message
    await interaction.response.send_message(
        f'{interaction.user.mention} asked me to imagine "{prompt}", this shouldn\'t take too long...'
    )

    lora_list = [
        lora != None and lora.value or None,
        lora2 != None and lora2.value or None,
        lora3 != None and lora3.value or None,
    ]

    lora_strengths = [lora_strength, lora_strength2, lora_strength3]

    if seed is None:
        seed = random.randint(0, 999999999999999)

    params = PromptParams(
        # SD15_LLM_WORKFLOW if enhance else SD15_WORKFLOW,
        SD15_WORKFLOW,
        prompt,
        negative_prompt,
        model,
        lora_list,
        lora_strengths,
        aspect_ratio,
        num_steps,
        cfg_scale,
        seed=seed,
    )

    # Generate the image and get progress updates
    images, enhanced_prompt = await generate_images(params)

    # Construct the final message with user mention
    if enhanced_prompt is None:
        final_message = f'{interaction.user.mention} asked me to imagine "{prompt}", here is what I imagined for them. Seed: {seed}'
    else:
        final_message = (
            f'{interaction.user.mention} asked me to imagine "{prompt}", here is what I imagined for them.\n'
            f'(Prompt enhanced with _"{enhanced_prompt}"_ Seed: {seed})'
        )
        params.prompt = enhanced_prompt

    buttons = Buttons(params, images, interaction.user, command="imagine")
    # send as gif or png
    await interaction.channel.send(
        content=final_message, file=discord.File(fp=create_collage(images), filename="collage.png"), view=buttons
    )


@tree.command(name="video", description="Generate a video based on input text")
@app_commands.describe(
    prompt="Prompt for the video being generated",
    negative_prompt="Prompt for what you want to steer the AI away from",
    model="Model checkpoint to use",
    lora="LoRA to apply",
    lora_strength="Strength of LoRA",
    num_steps="Number of sampling steps; range [1, 20]",
    cfg_scale="Degree to which AI should follow prompt; range [1.0, 10.0]",
)
@app_commands.choices(model=SD15_MODEL_CHOICES, lora=SD15_LORA_CHOICES)
async def slash_command(
    interaction: discord.Interaction,
    prompt: str,
    negative_prompt: str = None,
    model: str = None,
    lora: Choice[str] = None,
    lora_strength: float = 1.0,
    lora2: Choice[str] = None,
    lora_strength2: float = 1.0,
    lora3: Choice[str] = None,
    lora_strength3: float = 1.0,
    num_steps: Range[int, 1, 20] = None,
    cfg_scale: Range[float, 1.0, 10.0] = None,
    seed: int = None,
):
    if should_filter(prompt, negative_prompt):
        print(
            f"Prompt or negative prompt contains a blocked word, not generating image. \n"
            f"Prompt: {prompt}, Negative Prompt: {negative_prompt}"
        )
        await interaction.response.send_message(
            f"The prompt {prompt} or negative prompt {negative_prompt} contains a blocked word, not generating image.",
            ephemeral=True,
        )
        return

    # Send an initial message
    await interaction.response.send_message(
        f'{interaction.user.mention} asked me to create the video "{prompt}", this shouldn\'t take too long...'
    )

    lora_list = [
        lora != None and lora.value or None,
        lora2 != None and lora2.value or None,
        lora3 != None and lora3.value or None,
    ]

    lora_strengths = [lora_strength, lora_strength2, lora_strength3]

    if seed is None:
        seed = random.randint(0, 999999999999999)

    params = PromptParams(
        VIDEO_WORKFLOW,
        prompt,
        negative_prompt,
        model,
        lora_list,
        lora_strengths,
        num_steps=num_steps,
        cfg_scale=cfg_scale,
        seed=seed,
    )

    # Generate the video and get progress updates
    video, enhanced_prompt = await generate_images(params)

    if enhanced_prompt is not None:
        params.prompt = enhanced_prompt

    # Construct the final message with user mention
    final_message = (
        f'{interaction.user.mention} asked me to create the video "{params.prompt}", here is what I created for them. '
        f"Seed: {seed}"
    )

    buttons = Buttons(params, video, interaction.user, command="video")
    await interaction.channel.send(
        content=final_message, file=discord.File(fp=create_gif_collage(video), filename="collage.gif"), view=buttons
    )


@tree.command(name="sdxl", description="Generate an image using SDXL")
@app_commands.describe(
    prompt="Prompt for the image being generated",
    negative_prompt="Prompt for what you want to steer the AI away from",
    model="Model checkpoint to use",
    lora="LoRA to apply",
    lora_strength="Strength of LoRA",
    aspect_ratio="Aspect ratio of the generated image",
    num_steps="Number of sampling steps; range [1, 20]",
    cfg_scale="Degree to which AI should follow prompt; range [1.0, 10.0]",
)
@app_commands.choices(
    model=SDXL_MODEL_CHOICES,
    lora=SDXL_LORA_CHOICES,
    lora2=SDXL_LORA_CHOICES,
    lora3=SDXL_LORA_CHOICES,
    aspect_ratio=ASPECT_RATIO_CHOICES,
)
async def slash_command(
    interaction: discord.Interaction,
    prompt: str,
    negative_prompt: str = None,
    model: str = None,
    lora: Choice[str] = None,
    lora_strength: float = 1.0,
    lora2: Choice[str] = None,
    lora_strength2: float = 1.0,
    lora3: Choice[str] = None,
    lora_strength3: float = 1.0,
    aspect_ratio: str = None,
    num_steps: Range[int, 1, 20] = None,
    cfg_scale: Range[float, 1.0, 10.0] = None,
    seed: int = None,
):
    if should_filter(prompt, negative_prompt):
        print(
            f"Prompt or negative prompt contains a blocked word, not generating image. \n"
            f"Prompt: {prompt}, Negative Prompt: {negative_prompt}"
        )
        await interaction.response.send_message(
            f"The prompt {prompt} or negative prompt {negative_prompt} contains a blocked word, not generating image.",
            ephemeral=True,
        )
        return

    # Send an initial message
    await interaction.response.send_message(
        f'{interaction.user.mention} asked me to imagine "{prompt}", this shouldn\'t take too long...'
    )

    lora_list = [
        lora != None and lora.value or None,
        lora2 != None and lora2.value or None,
        lora3 != None and lora3.value or None,
    ]

    lora_strengths = [lora_strength, lora_strength2, lora_strength3]

    if seed is None:
        seed = random.randint(0, 999999999999999)

    params = PromptParams(
        SDXL_WORKFLOW,
        prompt,
        negative_prompt,
        model,
        lora_list,
        lora_strengths,
        aspect_ratio,
        num_steps,
        cfg_scale,
        seed=seed,
    )

    # Generate the image and get progress updates
    images, enhanced_prompt = await generate_images(params)

    if enhanced_prompt != None:
        params.prompt = enhanced_prompt

    # Construct the final message with user mention
    final_message = f'{interaction.user.mention} asked me to imagine "{prompt}", here is what I imagined for them. Seed: {seed}'
    buttons = Buttons(params, images, interaction.user, command="sdxl")
    # send as gif or png
    await interaction.channel.send(
        content=final_message,
        file=discord.File(fp=create_collage(images), filename="collage.png"),
        view=buttons,
    )


# run the bot
client.run(TOKEN)
