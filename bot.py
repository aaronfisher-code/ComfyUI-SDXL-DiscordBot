import discord
import discord.ext
from discord import app_commands
import configparser
import os
from PIL import Image
from datetime import datetime
from math import ceil, sqrt
from typing import List

from discord.app_commands import Choice


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
    config['API'] = {
        'API_KEY': 'STABILITY_AI_API_KEY',
        'API_HOST': 'https://api.stability.ai',
        'API_IMAGE_ENGINE': 'STABILITY_AI_IMAGE_GEN_MODEL'
    }
    with open('config.properties', 'w') as configfile:
        config.write(configfile)

def should_filter(positive_prompt : str, negative_prompt : str) -> bool:
    if(positive_prompt == None):
        positive_prompt = ""

    if(negative_prompt == None):
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
    if(images[0].format == 'GIF'):
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
    from imageGen import generate_images, upscale_image, generate_alternatives, generate_video, get_models, get_loras
elif IMAGE_SOURCE == "API":
    from apiImageGen import generate_images, upscale_image, generate_alternatives

models = get_models()
loras = get_loras()

# sync the slash command to your server
@client.event
async def on_ready():
    await tree.sync()
    print(f'Logged in as {client.user.name} ({client.user.id})')

class ImageButton(discord.ui.Button):
    def __init__(self, label, emoji, row, callback):
        super().__init__(label=label, style=discord.ButtonStyle.grey, emoji=emoji, row=row)
        self._callback = callback

    async def callback(self, interaction: discord.Interaction):
        await self._callback(interaction, self)


class Buttons(discord.ui.View):
    def __init__(self, prompt, negative_prompt, model, lora, enhance, images, config=None, *, timeout=180):
        super().__init__(timeout=timeout)
        self.prompt = prompt
        self.negative_prompt = negative_prompt
        self.model = model
        self.lora = lora
        self.enhance = enhance
        self.images = images
        self.config = config

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
            row = (idx + len(images) + 1) // 5 + reroll_row  # Determine row based on index, number of alternative buttons, and re-roll row
            btn = ImageButton(f"U{idx + 1}", "⬆️", row, self.upscale_and_send)
            self.add_item(btn)

        self.timeout = None

    async def generate_alternatives_and_send(self, interaction, button):
        index = int(button.label[1:]) - 1  # Extract index from label
        await interaction.response.send_message("Creating some alternatives, this shouldn't take too long...")
        images = await generate_alternatives(self.images[index], self.prompt, self.negative_prompt, self.model, self.lora, self.config)
        collage_path = create_collage(images)
        final_message = f"{interaction.user.mention} here are your alternative images"
        # if a gif, set filename as gif, otherwise png
        if(images[0].format == 'GIF'):
            await interaction.channel.send(content=final_message, file=discord.File(fp=collage_path, filename='collage' + '.gif'), view=Buttons(self.prompt, self.negative_prompt, self.model, self.lora, self.enhance, images, self.config))
        else:
            await interaction.channel.send(content=final_message, file=discord.File(fp=collage_path, filename='collage.png'), view=Buttons(self.prompt, self.negative_prompt, self.model, self.lora, self.enhance, images, self.config))

    async def upscale_and_send(self, interaction, button):
        index = int(button.label[1:]) - 1  # Extract index from label
        await interaction.response.send_message("Upscaling the image, this shouldn't take too long...")
        upscaled_image = await upscale_image(self.images[index], self.prompt, self.negative_prompt, self.model, self.lora)
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        upscaled_image_path = f"./out/upscaledImage_{timestamp}.png"
        upscaled_image.save(upscaled_image_path)
        final_message = f"{interaction.user.mention} here is your upscaled image"
        await interaction.channel.send(content=final_message, file=discord.File(fp=upscaled_image_path, filename='upscaled_image.png'))

    @discord.ui.button(label="Re-roll", style=discord.ButtonStyle.green, emoji="🎲", row=0)
    async def reroll_image(self, interaction, btn):
        await interaction.response.send_message(f"{interaction.user.mention} asked me to re-imagine \"{self.prompt}\", this shouldn't take too long...")
        btn.disabled = True
        await interaction.message.edit(view=self)
        # Generate a new image with the same prompt
        images = await generate_images(self.prompt,self.negative_prompt, self.model, self.lora, self.enhance)

        # Construct the final message with user mention
        final_message = f"{interaction.user.mention} asked me to re-imagine \"{self.prompt}\", here is what I imagined for them."
        await interaction.channel.send(content=final_message, file=discord.File(fp=create_collage(images), filename='collage.png'), view = Buttons(self.prompt,self.negative_prompt, self.model, self.lora, self.enhance, images))

@tree.command(name="imagine", description="Generate an image based on input text")
@app_commands.describe(prompt='Prompt for the image being generated')
@app_commands.describe(negative_prompt='Prompt for what you want to steer the AI away from')
@app_commands.describe(model='Model checkpoint to use')
@app_commands.describe(lora='LoRA to apply')
@app_commands.describe(lora_strength='Strength of LoRA')
@app_commands.describe(enhance='Enhance the image using a language model')
@app_commands.choices(model=[app_commands.Choice(name=m, value=m) for m in models[0]][0:25], lora=[app_commands.Choice(name=l, value=l) for l in loras[0]][0:25])
async def slash_command(interaction: discord.Interaction, prompt: str, negative_prompt: str = None, model: str = None, lora: Choice[str] = None, lora_strength: float = 1.0, enhance: bool = True):
    if should_filter(prompt, negative_prompt):
        print(f"Prompt or negative prompt contains a blocked word, not generating image. Prompt: {prompt}, Negative Prompt: {negative_prompt}")
        await interaction.response.send_message(f"The prompt {prompt} or negative prompt {negative_prompt} contains a blocked word, not generating image.",ephemeral=True)
        return

    if enhance:
        config = "ENHANCE_TEXT2IMG_CONFIG"
    else:
        config = None

    # Send an initial message
    await interaction.response.send_message(f"{interaction.user.mention} asked me to imagine \"{prompt}\", this shouldn't take too long...")

    # Generate the image and get progress updates
    images = await generate_images(prompt,negative_prompt, model, lora, lora_strength, config)

    # Construct the final message with user mention
    final_message = f"{interaction.user.mention} asked me to imagine \"{prompt}\", here is what I imagined for them."
    # send as gif or png
    await interaction.channel.send(content=final_message, file=discord.File(fp=create_collage(images), filename='collage.png'), view=Buttons(prompt,negative_prompt,model,lora,enhance,images, config))

@tree.command(name="video", description="Generate a video based on input text")
@app_commands.describe(prompt='Prompt for the video being generated')
@app_commands.describe(negative_prompt='Prompt for what you want to steer the AI away from')
@app_commands.describe(model='Model checkpoint to use')
@app_commands.describe(lora='LoRA to apply')
@app_commands.describe(lora_strength='Strength of LoRA')
@app_commands.choices(model=[app_commands.Choice(name=m, value=m) for m in models[0]][0:25], lora=[app_commands.Choice(name=l, value=l) for l in loras[0]][0:25])
async def slash_command(interaction: discord.Interaction, prompt: str, negative_prompt: str = None, model: str = None, lora: Choice[str] = None, lora_strength: float = 1.0):
    if should_filter(prompt, negative_prompt):
        print(f"Prompt or negative prompt contains a blocked word, not generating image. Prompt: {prompt}, Negative Prompt: {negative_prompt}")
        await interaction.response.send_message(f"The prompt {prompt} or negative prompt {negative_prompt} contains a blocked word, not generating image.", ephemeral=True)
        return

    # Send an initial message
    await interaction.response.send_message(f"{interaction.user.mention} asked me to create the video \"{prompt}\", this shouldn't take too long...")

    # Generate the video and get progress updates
    video = await generate_video(prompt,negative_prompt, model, lora, lora_strength)

    # Construct the final message with user mention
    final_message = f"{interaction.user.mention} asked me to create the video \"{prompt}\", here is what I created for them."

    await interaction.channel.send(content=final_message, file=discord.File(fp=create_gif_collage(video), filename='collage.gif'))#, view=Buttons(prompt, negative_prompt, images))

@tree.command(name="sdxl", description="Generate an image using SDXL")
@app_commands.describe(prompt='Prompt for the image being generated')
@app_commands.describe(negative_prompt='Prompt for what you want to steer the AI away from')
@app_commands.describe(model='Model checkpoint to use')
@app_commands.describe(lora='LoRA to apply')
@app_commands.describe(lora_strength='Strength of LoRA')
@app_commands.choices(model=[app_commands.Choice(name=m, value=m) for m in models[0] if "xl" in m.lower()][0:25], lora=[app_commands.Choice(name=l, value=l) for l in loras[0] if "xl" in l.lower()][0:25])
async def slash_command(interaction: discord.Interaction, prompt: str, negative_prompt: str = None, model: str = None, lora: Choice[str] = None, lora_strength: float = 1.0, enhance : bool = True):
    if should_filter(prompt, negative_prompt):
        print(f"Prompt or negative prompt contains a blocked word, not generating image. Prompt: {prompt}, Negative Prompt: {negative_prompt}")
        await interaction.response.send_message(f"The prompt {prompt} or negative prompt {negative_prompt} contains a blocked word, not generating image.", ephemeral=True)
        return

    if enhance:
        config = "ENHANCE_TEXT2IMG_SDXL_CONFIG"
    else:
        config = None

    # Send an initial message
    await interaction.response.send_message(f"{interaction.user.mention} asked me to imagine \"{prompt}\", this shouldn't take too long...")

    # Generate the image and get progress updates
    images = await generate_images(prompt,negative_prompt, model, lora, lora_strength, config)

    # Construct the final message with user mention
    final_message = f"{interaction.user.mention} asked me to imagine \"{prompt}\", here is what I imagined for them."
    # send as gif or png
    await interaction.channel.send(content=final_message, file=discord.File(fp=create_collage(images), filename='collage.png'), view=Buttons(prompt,negative_prompt,model,lora,enhance,images, config))

# run the bot
client.run(TOKEN)