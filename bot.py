# imports
import discord
import discord.ext
from discord import app_commands
import configparser
import os
from imageGen import generate_image

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
    def __init__(self, base_image,prompt, *, timeout=180):
        super().__init__(timeout=timeout)
        self.base_image = base_image
        self.prompt = prompt

    @discord.ui.button(label="Re-roll", style=discord.ButtonStyle.green, emoji="🎲")
    async def reroll_image(self, interaction, btn):
        await interaction.response.send_message("Starting image generation...")
        btn.disabled = True
        await interaction.message.edit(view=self)
        # Generate a new image with the same prompt
        base_image_binary, refined_image_binary = await generate_image(self.prompt, interaction)
        # Send the newly generated image
        final_message = f"{interaction.user.mention} asked me to re-imagine \"{self.prompt}\", here is what I imagined for them."
        await interaction.followup.send(content=final_message, file=discord.File(fp=refined_image_binary, filename='generated_image.png'), view=Buttons(base_image_binary,self.prompt))
        # Update the base image for the view
        self.base_image = base_image_binary


    @discord.ui.button(label="View Unrefined Image",style=discord.ButtonStyle.blurple)
    async def view_base_image(self, interaction, btn):
        await interaction.response.send_message(content=f"No worries {interaction.user.mention}, Heres the base image", file=discord.File(fp=self.base_image, filename='base_image.png'))
        btn.disabled = True
        await interaction.message.edit(view=self)

    def on_timeout(self):
        # Close the binaries when the view times out
        self.base_image.close()

@tree.command(name="imagine", description="Generate an image based on input text")
@app_commands.describe(prompt='Prompt for the image being generated')
async def slash_command(interaction: discord.Interaction, prompt: str):
    # Send an initial message
    await interaction.response.send_message("Starting image generation...")

    # Generate the image and get progress updates
    base_image_binary, refined_image_binary = await generate_image(prompt, interaction)

    # Construct the final message with user mention
    final_message = f"{interaction.user.mention} asked me to imagine \"{prompt}\", here is what I imagined for them."
    await interaction.followup.send(content=final_message, file=discord.File(fp=refined_image_binary, filename='generated_image.png'), view=Buttons(base_image_binary,prompt))

# run the bot
client.run(TOKEN)