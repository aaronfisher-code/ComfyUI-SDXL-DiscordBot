from dataclasses import dataclass

import discord
import discord.ext
import configparser
import os
import random

from discord import app_commands
from discord.app_commands import Choice, Range

from buttons import Buttons
from imageGen import generate_images, get_models, get_loras
from collage_utils import create_collage, create_gif_collage


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


# setting up the bot
TOKEN, IMAGE_SOURCE = setup_config()
intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)

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
