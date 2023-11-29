import discord
import discord.ext
from discord import app_commands
import configparser
import os
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
    return config['BOT']['TOKEN'], config['BOT']['SDXL_SOURCE'], float(config['BOT']['MESSAGE_INTERACTION_TIMEOUT'])


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


def create_collage(images):
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
TOKEN, IMAGE_SOURCE, MESSAGE_INTERACTION_TIMEOUT = setup_config()
intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)

if IMAGE_SOURCE == "LOCAL":
    from imageGen import generate_images, upscale_image, generate_alternatives
elif IMAGE_SOURCE == "API":
    from apiImageGen import generate_images, upscale_image, generate_alternatives


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
    def __init__(self, prompt, negative_prompt, images, *, timeout=MESSAGE_INTERACTION_TIMEOUT):
        super().__init__(timeout=timeout)
        self.prompt = prompt
        self.negative_prompt = negative_prompt
        self.images = images
        self.message = None

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
                images) + 1) // 5 + reroll_row  # Determine row based on index, number of alternative buttons, and re-roll row
            btn = ImageButton(f"U{idx + 1}", "⬆️", row, self.upscale_and_send)
            self.add_item(btn)

    async def on_timeout(self):
        self.clear_items()
        await self.message.edit(view=self)

    async def generate_alternatives_and_send(self, interaction, button):
        index = int(button.label[1:]) - 1  # Extract index from label
        await interaction.response.send_message(
            f"{interaction.user.mention}Creating some alternatives, this shouldn't take too long...")
        images = await generate_alternatives(self.images[index], self.prompt, self.negative_prompt)
        collage_path = create_collage(images)
        final_message = f"{interaction.user.mention} here are your alternative images"
        alternatives_view = Buttons(self.prompt, self.negative_prompt, images)
        alternatives_view.message = await interaction.channel.send(content=final_message,
                                                                   file=discord.File(fp=collage_path,
                                                                                     filename='collage.png'),
                                                                   view=alternatives_view)

    async def upscale_and_send(self, interaction, button):
        index = int(button.label[1:]) - 1  # Extract index from label
        await interaction.response.send_message(
            f"{interaction.user.mention}Upscaling the image, this shouldn't take too long...")
        upscaled_image = await upscale_image(self.images[index], self.prompt, self.negative_prompt)
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        upscaled_image_path = f"./out/upscaledImage_{timestamp}.png"
        upscaled_image.save(upscaled_image_path)
        final_message = f"{interaction.user.mention} here is your upscaled image"
        await interaction.channel.send(content=final_message,
                                       file=discord.File(fp=upscaled_image_path, filename='upscaled_image.png'))

    @discord.ui.button(label="Re-roll", style=discord.ButtonStyle.green, emoji="🎲", row=0)
    async def reroll_image(self, interaction, btn):
        btn.disabled = True
        await interaction.message.edit(view=self)
        await interaction.response.send_message(
            f"{interaction.user.mention} asked me to re-imagine \"{self.prompt}\", this shouldn't take too long...")
        # Generate a new image with the same prompt
        images = await generate_images(self.prompt, self.negative_prompt)

        # Construct the final message with user mention
        final_message = f"{interaction.user.mention} asked me to re-imagine \"{self.prompt}\", here is what I imagined for them."
        reroll_view = Buttons(self.prompt, self.negative_prompt, images)
        reroll_view.message = await interaction.channel.send(content=final_message,
                                                             file=discord.File(fp=create_collage(images),
                                                                               filename='collage.png'),
                                                             view=reroll_view)


@tree.command(name="imagine", description="Generate an image based on input text")
@app_commands.describe(prompt='Prompt for the image being generated')
@app_commands.describe(negative_prompt='Prompt for what you want to steer the AI away from')
async def slash_command(interaction: discord.Interaction, prompt: str, negative_prompt: str = None):
    # Send an initial message
    await interaction.response.send_message(
        f"{interaction.user.mention} asked me to imagine \"{prompt}\", this shouldn't take too long...")

    # Generate the image and get progress updates
    images = await generate_images(prompt, negative_prompt)
    buttons_view = Buttons(prompt, negative_prompt, images)
    # Construct the final message with user mention
    final_message = f"{interaction.user.mention} asked me to imagine \"{prompt}\", here is what I imagined for them."
    buttons_view.message = await interaction.channel.send(content=final_message,
                                                          file=discord.File(fp=create_collage(images),
                                                                            filename='collage.png'), view=buttons_view)


# run the bot
client.run(TOKEN)
