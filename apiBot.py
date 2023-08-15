# imports
import discord
import discord.ext
from discord import app_commands
import configparser
import os
from PIL import Image
from datetime import datetime
from apiImageGen import generate_images, generate_alternatives, upscale_image

def generate_default_config():
    config = configparser.ConfigParser()
    config['DEFAULT'] = {
        'TOKEN': 'YOUR_DEFAULT_DISCORD_BOT_TOKEN',
        'SERVER_ADDRESS': 'YOUR_COMFYUI_URL',
        'GUILD_ID': 'PREFERRED GUILD ID'
    }
    
    with open('config.properties', 'w') as configfile:
        config.write(configfile)

# Check if the config file exists, if not, generate it
if not os.path.exists('config.properties'):
    generate_default_config()

if not os.path.exists('./out'):
    os.makedirs('./out')

# Read the configuration
config = configparser.ConfigParser()
config.read('config.properties')

TOKEN = config['DEFAULT']['TOKEN']

# setting up the bot
intents = discord.Intents.default() 
# if you don't want all intents you can do discord.Intents.default()
client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)

# sync the slash command to your server
@client.event
async def on_ready():
    await tree.sync()
    # print "ready" in the console when the bot is ready to work
    print(f'Logged in as {client.user.name} ({client.user.id})')

class Buttons(discord.ui.View):
    def __init__(self,prompt,images, *, timeout=180):
        super().__init__(timeout=timeout)
        self.prompt = prompt
        self.images = images

    
    @discord.ui.button(label="V1", style=discord.ButtonStyle.grey, emoji="♻️" , row=0)
    async def alternatives_imageOne(self, interaction, btn):
        await interaction.response.send_message("Creating some alternatives, this shouldn't take too long...")

        # Generate a new image with the same prompt
        images = await generate_alternatives(self.images[0], self.prompt)
        # Create a 2x2 collage
        collage_width = max(image.width for image in images) * 2
        collage_height = max(image.height for image in images) * 2
        collage = Image.new('RGB', (collage_width, collage_height))

        collage.paste(images[0], (0, 0))
        collage.paste(images[1], (images[0].width, 0))
        collage.paste(images[2], (0, images[0].height))
        collage.paste(images[3], (images[0].width, images[0].height))

        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        collage_path = f"./out/collage_{timestamp}.png"
        collage.save(collage_path)

        # Construct the final message with user mention
        final_message = f"{interaction.user.mention} here are your alternative images"
        await interaction.followup.send(content=final_message, file=discord.File(fp=collage_path, filename='collage.png'), view = Buttons(self.prompt, images))

    @discord.ui.button(label="V2", style=discord.ButtonStyle.grey, emoji="♻️", row=0)
    async def alternatives_imageTwo(self, interaction, btn):
        await interaction.response.send_message("Creating some alternatives, this shouldn't take too long...")

        # Generate a new image with the same prompt
        images = await generate_alternatives(self.images[1], self.prompt)
        # Create a 2x2 collage
        collage_width = max(image.width for image in images) * 2
        collage_height = max(image.height for image in images) * 2
        collage = Image.new('RGB', (collage_width, collage_height))

        collage.paste(images[0], (0, 0))
        collage.paste(images[1], (images[0].width, 0))
        collage.paste(images[2], (0, images[0].height))
        collage.paste(images[3], (images[0].width, images[0].height))

        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        collage_path = f"./out/collage_{timestamp}.png"
        collage.save(collage_path)

        # Construct the final message with user mention
        final_message = f"{interaction.user.mention} here are your alternative images"
        await interaction.followup.send(content=final_message, file=discord.File(fp=collage_path, filename='collage.png'), view = Buttons(self.prompt, images))
    
    @discord.ui.button(label="V3", style=discord.ButtonStyle.grey, emoji="♻️", row=0)
    async def alternatives_imageThree(self, interaction, btn):
        await interaction.response.send_message("Creating some alternatives, this shouldn't take too long...")

        # Generate a new image with the same prompt
        images = await generate_alternatives(self.images[2], self.prompt)
        # Create a 2x2 collage
        collage_width = max(image.width for image in images) * 2
        collage_height = max(image.height for image in images) * 2
        collage = Image.new('RGB', (collage_width, collage_height))

        collage.paste(images[0], (0, 0))
        collage.paste(images[1], (images[0].width, 0))
        collage.paste(images[2], (0, images[0].height))
        collage.paste(images[3], (images[0].width, images[0].height))

        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        collage_path = f"./out/collage_{timestamp}.png"
        collage.save(collage_path)

        # Construct the final message with user mention
        final_message = f"{interaction.user.mention} here are your alternative images"
        await interaction.followup.send(content=final_message, file=discord.File(fp=collage_path, filename='collage.png'), view = Buttons(self.prompt, images))

    @discord.ui.button(label="V4", style=discord.ButtonStyle.grey, emoji="♻️", row=0)
    async def alternatives_imageFour(self, interaction, btn):
        await interaction.response.send_message("Creating some alternatives, this shouldn't take too long...")

        # Generate a new image with the same prompt
        images = await generate_alternatives(self.images[3], self.prompt)
        # Create a 2x2 collage
        collage_width = max(image.width for image in images) * 2
        collage_height = max(image.height for image in images) * 2
        collage = Image.new('RGB', (collage_width, collage_height))

        collage.paste(images[0], (0, 0))
        collage.paste(images[1], (images[0].width, 0))
        collage.paste(images[2], (0, images[0].height))
        collage.paste(images[3], (images[0].width, images[0].height))

        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        collage_path = f"./out/collage_{timestamp}.png"
        collage.save(collage_path)

        # Construct the final message with user mention
        final_message = f"{interaction.user.mention} here are your alternative images"
        await interaction.followup.send(content=final_message, file=discord.File(fp=collage_path, filename='collage.png'), view = Buttons(self.prompt, images))

    @discord.ui.button(label="U1", style=discord.ButtonStyle.grey, emoji="⬆️", row=1)
    async def upscale_imageOne(self, interaction, btn):
        await interaction.response.send_message("Upscaling the image, this shouldn't take too long...")

        # Upscale the image
        upscaled_image = await upscale_image(self.images[0])

        # Save the upscaled image
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')    
        upscaled_image_path = f"./out/upscaledImage_{timestamp}.png"
        upscaled_image.save(upscaled_image_path)

        # Construct the final message with user mention
        final_message = f"{interaction.user.mention} here is your upscaled image"
        await interaction.followup.send(content=final_message, file=discord.File(fp=upscaled_image_path, filename='upscaled_image.png'))

    @discord.ui.button(label="U2", style=discord.ButtonStyle.grey, emoji="⬆️", row=1)
    async def upscale_imageTwo(self, interaction, btn):
        await interaction.response.send_message("Upscaling the image, this shouldn't take too long...")

        # Upscale the image
        upscaled_image = await upscale_image(self.images[1])

        # Save the upscaled image
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')    
        upscaled_image_path = f"./out/upscaledImage_{timestamp}.png"
        upscaled_image.save(upscaled_image_path)

        # Construct the final message with user mention
        final_message = f"{interaction.user.mention} here is your upscaled image"
        await interaction.followup.send(content=final_message, file=discord.File(fp=upscaled_image_path, filename='upscaled_image.png'))

    @discord.ui.button(label="U3", style=discord.ButtonStyle.grey, emoji="⬆️", row=1)
    async def upscale_imageThree(self, interaction, btn):
        await interaction.response.send_message("Upscaling the image, this shouldn't take too long...")

        # Upscale the image
        upscaled_image = await upscale_image(self.images[2])

        # Save the upscaled image
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')    
        upscaled_image_path = f"./out/upscaledImage_{timestamp}.png"
        upscaled_image.save(upscaled_image_path)

        # Construct the final message with user mention
        final_message = f"{interaction.user.mention} here is your upscaled image"
        await interaction.followup.send(content=final_message, file=discord.File(fp=upscaled_image_path, filename='upscaled_image.png'))

    @discord.ui.button(label="U4", style=discord.ButtonStyle.grey, emoji="⬆️", row=1)
    async def upscale_imageFour(self, interaction, btn):
        await interaction.response.send_message("Upscaling the image, this shouldn't take too long...")

        # Upscale the image
        upscaled_image = await upscale_image(self.images[3])

        # Save the upscaled image
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')    
        upscaled_image_path = f"./out/upscaledImage_{timestamp}.png"
        upscaled_image.save(upscaled_image_path)

        # Construct the final message with user mention
        final_message = f"{interaction.user.mention} here is your upscaled image"
        await interaction.followup.send(content=final_message, file=discord.File(fp=upscaled_image_path, filename='upscaled_image.png'))

    @discord.ui.button(label="Re-roll", style=discord.ButtonStyle.green, emoji="🎲", row=0)
    async def reroll_image(self, interaction, btn):
        await interaction.response.send_message(f"{interaction.user.mention} asked me to re-imagine \"{self.prompt}\", this shouldn't take too long...")
        btn.disabled = True
        await interaction.message.edit(view=self)
        # Generate a new image with the same prompt
        images = await generate_images(self.prompt, interaction)
        # Create a 2x2 collage
        collage_width = max(image.width for image in images) * 2
        collage_height = max(image.height for image in images) * 2
        collage = Image.new('RGB', (collage_width, collage_height))

        collage.paste(images[0], (0, 0))
        collage.paste(images[1], (images[0].width, 0))
        collage.paste(images[2], (0, images[0].height))
        collage.paste(images[3], (images[0].width, images[0].height))

        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        collage_path = f"./out/collage_{timestamp}.png"
        collage.save(collage_path)

        # Construct the final message with user mention
        final_message = f"{interaction.user.mention} asked me to re-imagine \"{self.prompt}\", here is what I imagined for them."
        await interaction.followup.send(content=final_message, file=discord.File(fp=collage_path, filename='collage.png'), view = Buttons(self.prompt, images))

@tree.command(name="imagine", description="Generate an image based on input text")
@app_commands.describe(prompt='Prompt for the image being generated')
async def slash_command(interaction: discord.Interaction, prompt: str):
    # Send an initial message
    await interaction.response.send_message(f"{interaction.user.mention} asked me to imagine \"{prompt}\", this shouldn't take too long...")

    # Generate the image and get progress updates
    images = await generate_images(prompt, interaction)
    # Create a 2x2 collage
    collage_width = max(image.width for image in images) * 2
    collage_height = max(image.height for image in images) * 2
    collage = Image.new('RGB', (collage_width, collage_height))

    collage.paste(images[0], (0, 0))
    collage.paste(images[1], (images[0].width, 0))
    collage.paste(images[2], (0, images[0].height))
    collage.paste(images[3], (images[0].width, images[0].height))

    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    collage_path = f"./out/collage_{timestamp}.png"
    collage.save(collage_path)

    # Construct the final message with user mention
    final_message = f"{interaction.user.mention} asked me to imagine \"{prompt}\", here is what I imagined for them."
    await interaction.followup.send(content=final_message, file=discord.File(fp=collage_path, filename='collage.png'), view=Buttons(prompt,images))

# run the bot
client.run(TOKEN)