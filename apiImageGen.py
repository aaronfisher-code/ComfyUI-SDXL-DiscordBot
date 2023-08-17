import base64
import aiohttp
from aiohttp import FormData
from PIL import Image
import io
import json
import configparser

# Read the configuration
config = configparser.ConfigParser()
config.read('config.properties')
api_key = config['API']['API_KEY']
api_host = config['API']['API_HOST']

async def generate_images(prompt: str,negative_prompt: str,interaction):
    if api_key is None:
        raise Exception("Missing Stability API key.")
    
    text_prompts = [{"text": f"{prompt}","weight": 1.0,}]

    if negative_prompt != None:
        text_prompts.append({"text": f"{negative_prompt}","weight": -1.0,})

    async with aiohttp.ClientSession() as session:        
        async with session.post(
            f"{api_host}/v1/generation/{config['API_TEXT2IMG']['ENGINE']}/text-to-image",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {api_key}"
            },
            json={
                "text_prompts": text_prompts,
                "cfg_scale": float(config['API_TEXT2IMG']['CFG']),
                "height": int(config['API_TEXT2IMG']['HEIGHT']),
                "width": int(config['API_TEXT2IMG']['WIDTH']),
                "samples": int(config['API_TEXT2IMG']['SAMPLES']),
                "sampler": str(config['API_TEXT2IMG']['SAMPLER']),
                "steps": int(config['API_TEXT2IMG']['STEPS'])
            }
        ) as response:
            if response.status != 200:
                await interaction.followup.send(content="There was an error processing your request, please ensure you dont use any profanity in your prompt")
                raise Exception(f"Non-200 response: {await response.text()}")
            data = await response.json()

    images = []
    for i, image in enumerate(data["artifacts"]):
        img_data = base64.b64decode(image["base64"])
        img = Image.open(io.BytesIO(img_data))
        images.append(img)

    return images


async def generate_alternatives(image: Image.Image, prompt: str, negative_prompt: str):
    if api_key is None:
        raise Exception("Missing Stability API key.")

    # Convert the PIL Image to bytes
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    image_bytes = buffered.getvalue()

    # Create FormData object
    data = FormData()
    data.add_field('init_image', image_bytes, filename='init_image.png', content_type='image/png')
    data.add_field('image_strength', config['API_IMG2IMG']['IMAGE_STRENGTH'])
    data.add_field('init_image_mode', config['API_IMG2IMG']['INIT_IMAGE_MODE'])
    data.add_field('cfg_scale', config['API_IMG2IMG']['CFG'])
    data.add_field('samples', config['API_IMG2IMG']['SAMPLES'])
    data.add_field('sampler', config['API_IMG2IMG']['SAMPLER'])
    data.add_field('steps', config['API_IMG2IMG']['STEPS'])
    data.add_field('text_prompts[0][text]', prompt)
    data.add_field('text_prompts[0][weight]', str(1.0))

    if negative_prompt != None:
        data.add_field('text_prompts[1][text]', negative_prompt)
        data.add_field('text_prompts[1][weight]', str(-1.0))

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{api_host}/v1/generation/{config['API_IMG2IMG']['ENGINE']}/image-to-image",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {api_key}"
            },
            data=data
        ) as response:
            if response.status != 200:
                raise Exception(f"Non-200 response: {await response.text()}")
            data = await response.json()

    alternatives = []
    for i, image in enumerate(data["artifacts"]):
        img_data = base64.b64decode(image["base64"])
        img = Image.open(io.BytesIO(img_data))
        alternatives.append(img)

    return alternatives

async def upscale_image(image: Image.Image, prompt: str,negative_prompt: str):
    if api_key is None:
        raise Exception("Missing Stability API key.")

    # Convert the PIL Image to bytes
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    image_bytes = buffered.getvalue()

    # Create FormData object
    data = FormData()
    data.add_field('image', image_bytes, filename='init_image.png', content_type='image/png')
    data.add_field('width', config['API_UPSCALE']['WIDTH'])

    if config['API_UPSCALE']['ENGINE']!='esrgan-v1-x2plus':
        data.add_field('seed',config['API_UPSCALE']['SEED'])
        data.add_field('steps',config['API_UPSCALE']['STEPS'])
        data.add_field('cfg_scale',config['API_UPSCALE']['CFG'])
        data.add_field('text_prompts[0][text]', prompt)
        data.add_field('text_prompts[0][weight]', str(1.0))
        if negative_prompt != None:
            data.add_field('text_prompts[1][text]', negative_prompt)
            data.add_field('text_prompts[1][weight]', str(-1.0))

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{api_host}/v1/generation/{config['API_IMG2IMG']['ENGINE']}/image-to-image/upscale",
            headers={
                "Accept": "image/png",
                "Authorization": f"Bearer {api_key}"
            },
            data=data
        ) as response:
            if response.status != 200:
                raise Exception(f"Non-200 response: {await response.text()}")
            upscaled_image_bytes = await response.read()

    # Convert the bytes to a PIL Image
    upscaled_image = Image.open(io.BytesIO(upscaled_image_bytes))

    return upscaled_image