from dataclasses import dataclass

import discord
import discord.ext
import configparser
import os
import random

from discord import app_commands
from discord.app_commands import Choice, Range
from PIL import Image
from datetime import datetime
from math import ceil, sqrt


def setup_config():
    if not os.path.exists('config.properties'):
        generate_default_config()

    if not os.path.exists('./out'):
        os.makedirs('./out')

    config = configparser.ConfigParser()
    config.read('config.properties')
    return config['BOT']['TOKEN'], config['BOT']['SDXL_SOURCE']


def generate_default_config():
    config = configparser.ConfigParser()
    config['DISCORD'] = {
        'TOKEN': 'YOUR_DEFAULT_DISCORD_BOT_TOKEN'
    }
    config['LOCAL'] = {
        'SERVER_ADDRESS': 'YOUR_COMFYUI_URL'
    }
    with open('config.properties', 'w') as configfile:
        config.write(configfile)


def should_filter(positive_prompt: str, negative_prompt: str) -> bool:
    if (positive_prompt == None):
        positive_prompt = ""

    if (negative_prompt == None):
        negative_prompt = ""

    config = configparser.ConfigParser()
    config.read('config.properties')
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
    collage = Image.new('RGB', (collage_width, collage_height))
    collage.n_frames = images[0].n_frames

    for idx, image in enumerate(images):
        row = idx // num_cols
        col = idx % num_cols
        x_offset = col * image.width
        y_offset = row * image.height
        collage.paste(image, (x_offset, y_offset))

    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    collage_path = f"./out/images_{timestamp}.gif"
    images[0].save(collage_path, save_all=True, append_images=images[1:], duration=125, loop=0)

    return collage_path


def create_collage(images):
    if (len(images) == 0):
        print("Error: No images to make collage")
        return None

    if (images[0].format == 'GIF'):
        return create_gif_collage(images)

    num_images = len(images)
    num_cols = ceil(sqrt(num_images))
    num_rows = ceil(num_images / num_cols)
    collage_width = max(image.width for image in images) * num_cols
    collage_height = max(image.height for image in images) * num_rows
    collage = Image.new('RGB', (collage_width, collage_height))

    for idx, image in enumerate(images):
        row = idx // num_cols
        col = idx % num_cols
        x_offset = col * image.width
        y_offset = row * image.height
        collage.paste(image, (x_offset, y_offset))

    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    collage_path = f"./out/images_{timestamp}.png"
    collage.save(collage_path)

    return collage_path


# setting up the bot
TOKEN, IMAGE_SOURCE = setup_config()
intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)

if IMAGE_SOURCE == "LOCAL":
    from imageGen import generate_images, upscale_image, generate_alternatives, get_models, get_loras

models = get_models()
loras = get_loras()


# sync the slash command to your server
@client.event
async def on_ready():
    await tree.sync()
    print(f'Logged in as {client.user.name} ({client.user.id})')


@dataclass
class PromptParams:
    prompt: str = None
    negative_prompt: str = None


@dataclass
class ModelParams:
    model: str = None
    lora: Choice[str] = None
    lora_strength: float = 1.0
    lora2: Choice[str] = None
    lora_strength2: float = 1.0
    lora3: Choice[str] = None
    lora_strength3: float = 1.0


@dataclass
class ImageParams:
    aspect_ratio: str = None


@dataclass
class SamplerParams:
    num_steps: Range[int, 1, 20] = None
    cfg_scale: Range[float, 1.0, 10.0] = None
    seed: int = None


@dataclass
class WorkflowParams:
    config: str = None


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


@tree.command(name="refresh", description="Refresh the list of models and loras")
async def slash_command(interaction: discord.Interaction):
    global models
    global loras
    models = get_models()
    loras = get_loras()
    await interaction.response.send_message("Refreshed models and loras", ephemeral=True)


@tree.command(name="imagine", description="Generate an image based on input text")
@app_commands.describe(prompt='Prompt for the image being generated')
@app_commands.describe(negative_prompt='Prompt for what you want to steer the AI away from')
@app_commands.describe(model='Model checkpoint to use')
@app_commands.describe(lora='LoRA to apply')
@app_commands.describe(lora_strength='Strength of LoRA')
@app_commands.describe(num_steps='Number of sampling steps; range [1, 30]')
@app_commands.describe(cfg_scale='Degree to which AI should follow prompt; range [1.0, 10.0]')
@app_commands.describe(enhance='Enhance the image using a language model')
@app_commands.describe(aspect_ratio='Aspect ratio of the generated image')
@app_commands.choices(model=[app_commands.Choice(name=m, value=m) for m in models[0] if "xl" not in m.lower()][0:25],
                      lora=[app_commands.Choice(name=l, value=l) for l in loras[0] if "xl" not in l.lower()][0:25],
                      lora2=[app_commands.Choice(name=l, value=l) for l in loras[0] if "xl" not in l.lower()][0:25],
                      lora3=[app_commands.Choice(name=l, value=l) for l in loras[0] if "xl" not in l.lower()][0:25],
                      #   These aspect ratio resolution values correspond to the SDXL Empty Latent Image node. A latent modification node in the workflow converts it to the equivalent SD 1.5 resolution values.
                      aspect_ratio=[app_commands.Choice(name='1:1', value='1024 x 1024  (square)'),
                                    app_commands.Choice(name='7:9 portrait', value=' 896 x 1152  (portrait)'),
                                    app_commands.Choice(name='4:7 portrait', value=' 768 x 1344  (portrait)'),
                                    app_commands.Choice(name='9:7 landscape', value='1152 x 896   (landscape)'),
                                    app_commands.Choice(name='7:4 landscape', value='1344 x 768   (landscape)')]
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
        enhance: bool = False,
        aspect_ratio: str = None,
        num_steps: Range[int, 1, 30] = None,
        cfg_scale: Range[float, 1.0, 10.0] = None,
        seed: int = None
):
    prompt_params = PromptParams(prompt, negative_prompt)
    model_params = ModelParams(model, lora, lora_strength, lora2, lora_strength2, lora3, lora_strength3)
    image_params = ImageParams(aspect_ratio)
    sampler_params = SamplerParams(num_steps, cfg_scale, seed)
    workflow_params = WorkflowParams("LOCAL_TEXT2IMG")

    await do_request(interaction,
                     f"{interaction.user.mention} asked me to imagine \"{prompt}\", this shouldn't take too long...",
                     f"{interaction.user.mention} asked me to imagine \"{prompt}\", here is what I imagined for them.",
                     "imagine",
                     prompt_params,
                     model_params,
                     image_params,
                     sampler_params,
                     workflow_params
                     )


@tree.command(name="video", description="Generate a video based on input text")
@app_commands.describe(prompt='Prompt for the video being generated')
@app_commands.describe(negative_prompt='Prompt for what you want to steer the AI away from')
@app_commands.describe(model='Model checkpoint to use')
@app_commands.describe(lora='LoRA to apply')
@app_commands.describe(lora_strength='Strength of LoRA')
@app_commands.describe(num_steps='Number of sampling steps; range [1, 20]')
@app_commands.describe(cfg_scale='Degree to which AI should follow prompt; range [1.0, 10.0]')
@app_commands.choices(model=[app_commands.Choice(name=m, value=m) for m in models[0] if "xl" not in m.lower()][0:25],
                      lora=[app_commands.Choice(name=l, value=l) for l in loras[0] if "xl" not in l.lower()][0:25]
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
        num_steps: Range[int, 1, 20] = None,
        cfg_scale: Range[float, 1.0, 10.0] = None,
        seed: int = None,
):
    prompt_params = PromptParams(prompt, negative_prompt)
    model_params = ModelParams(model, lora, lora_strength, lora2, lora_strength2, lora3, lora_strength3)
    image_params = ImageParams()
    sampler_params = SamplerParams(num_steps, cfg_scale, seed)
    workflow_params = WorkflowParams("LOCAL_TEXT2VIDEO")

    await do_request(interaction,
                     f"{interaction.user.mention} asked me to create the video \"{prompt}\", this shouldn't take too long...",
                     f"{interaction.user.mention} asked me to create the video \"{prompt}\", here is what I created for them.",
                     "video",
                     prompt_params,
                     model_params,
                     image_params,
                     sampler_params,
                     workflow_params
                     )


@tree.command(name="sdxl", description="Generate an image using SDXL")
@app_commands.describe(prompt='Prompt for the image being generated')
@app_commands.describe(negative_prompt='Prompt for what you want to steer the AI away from')
@app_commands.describe(model='Model checkpoint to use')
@app_commands.describe(lora='LoRA to apply')
@app_commands.describe(lora_strength='Strength of LoRA')
@app_commands.describe(aspect_ratio='Aspect ratio of the generated image')
@app_commands.describe(num_steps='Number of sampling steps; range [1, 20]')
@app_commands.describe(cfg_scale='Degree to which AI should follow prompt; range [1.0, 10.0]')
@app_commands.choices(
    model=[app_commands.Choice(name=m, value=m) for m in models[0] if "xl" in m.lower() and "refiner" not in m.lower()][
          0:25],
    lora=[app_commands.Choice(name=l, value=l) for l in loras[0] if "xl" in l.lower()][0:25],
    lora2=[app_commands.Choice(name=l, value=l) for l in loras[0] if "xl" in l.lower()][0:25],
    lora3=[app_commands.Choice(name=l, value=l) for l in loras[0] if "xl" in l.lower()][0:25],
    aspect_ratio=[app_commands.Choice(name='1:1', value='1024 x 1024  (square)'),
                  app_commands.Choice(name='7:9 portrait', value=' 896 x 1152  (portrait)'),
                  app_commands.Choice(name='4:7 portrait', value=' 768 x 1344  (portrait)'),
                  app_commands.Choice(name='9:7 landscape', value='1152 x 896   (landscape)'),
                  app_commands.Choice(name='7:4 landscape', value='1344 x 768   (landscape)')]
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
    prompt_params = PromptParams(prompt, negative_prompt)
    model_params = ModelParams(model, lora, lora_strength, lora2, lora_strength2, lora3, lora_strength3)
    image_params = ImageParams(aspect_ratio)
    sampler_params = SamplerParams(num_steps, cfg_scale, seed)
    workflow_params = WorkflowParams("LOCAL_SDXL_TXT2IMG_CONFIG")

    await do_request(interaction,
                     f"{interaction.user.mention} asked me to imagine \"{prompt}\", this shouldn't take too long...",
                     f"{interaction.user.mention} asked me to imagine \"{prompt}\", here is what I imagined for them.",
                     "sdxl",
                     prompt_params,
                     model_params,
                     image_params,
                     sampler_params,
                     workflow_params
                     )


async def do_request(
        interaction: discord.Interaction,
        intro_message: str,
        completion_message: str,
        command_name: str,
        prompt_params: PromptParams,
        model_params: ModelParams,
        image_params: ImageParams,
        sampler_params: SamplerParams,
        workflow_params: WorkflowParams
):
    if should_filter(prompt_params.prompt, prompt_params.negative_prompt):
        print(f"Prompt or negative prompt contains a blocked word, not generating image. Prompt: {prompt_params.prompt}, Negative Prompt: {prompt_params.negative_prompt}")
        await interaction.response.send_message(
            f"The prompt {prompt_params.prompt} or negative prompt {prompt_params.negative_prompt} contains a blocked word, not generating image.",
            ephemeral=True
        )
        return

    # Send an initial message
    await interaction.response.send_message(intro_message)

    lora_list = [model_params.lora != None and model_params.lora.value or None,
                 model_params.lora2 != None and model_params.lora2.value or None,
                 model_params.lora3 != None and model_params.lora3.value or None]

    lora_strengths = [model_params.lora_strength, model_params.lora_strength2, model_params.lora_strength3]

    if sampler_params.seed is None:
        sampler_params.seed = random.randint(0, 999999999999999)

    # Generate the image and get progress updates
    images, enhanced_prompt = await generate_images(
        prompt_params.prompt,
        prompt_params.negative_prompt,
        model_params.model,
        lora_list,
        lora_strengths,
        image_params.aspect_ratio,
        sampler_params.num_steps,
        sampler_params.cfg_scale,
        sampler_params.seed,
        workflow_params.config
    )

    if (enhanced_prompt != None):
        prompt_params.prompt = enhanced_prompt

    # Construct the final message with user mention
    final_message = f"{completion_message}\n Seed: {sampler_params.seed}"
    buttons = Buttons(
        prompt_params.prompt,
        prompt_params.negative_prompt,
        model_params.model,
        lora_list,
        lora_strengths,
        False,
        images,
        interaction.user,
        workflow_params.config,
        aspect_ratio=image_params.aspect_ratio,
        num_steps=sampler_params.num_steps,
        cfg_scale=sampler_params.cfg_scale,
        command=command_name
    )
    # send as gif or png

    if "GIF" in images[0].format:
        await interaction.channel.send(content=final_message,
                                       file=discord.File(fp=create_gif_collage(images), filename='collage.gif'),
                                       view=buttons
                                       )
    else:
        await interaction.channel.send(content=final_message,
                                       file=discord.File(fp=create_collage(images), filename='collage.png'),
                                       view=buttons
                                       )


# run the bot
client.run(TOKEN)
