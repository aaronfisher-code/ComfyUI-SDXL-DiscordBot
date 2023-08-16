import base64
import aiohttp
from aiohttp import FormData
from PIL import Image
import io
import configparser

# Read the configuration
config = configparser.ConfigParser()
config.read('config.properties')
api_key = config['API']['API_KEY']
engine_id = config['API']['API_IMAGE_ENGINE']
api_host = config['API']['API_HOST']

async def generate_images(text: str, interaction):
    if api_key is None:
        raise Exception("Missing Stability API key.")

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{api_host}/v1/generation/{engine_id}/text-to-image",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {api_key}"
            },
            json={
                "text_prompts": [
                    {
                        "text": f"\"{text}\""
                    }
                ],
                "cfg_scale": 8,
                "height": 1024,
                "width": 1024,
                "samples": 4,
                "sampler": "K_DPMPP_2S_ANCESTRAL",
                "steps": 70
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


async def generate_alternatives(image: Image.Image, prompt: str):
    if api_key is None:
        raise Exception("Missing Stability API key.")

    # Convert the PIL Image to bytes
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    image_bytes = buffered.getvalue()

    # Create FormData object
    data = FormData()
    data.add_field('init_image', image_bytes, filename='init_image.png', content_type='image/png')
    data.add_field('image_strength', '0.35')
    data.add_field('init_image_mode', 'IMAGE_STRENGTH')
    data.add_field('cfg_scale', '7')
    data.add_field('samples', '4')
    data.add_field('sampler', 'K_DPMPP_2S_ANCESTRAL')
    data.add_field('steps', '40')
    data.add_field('text_prompts[0][text]', prompt)

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{api_host}/v1/generation/{engine_id}/image-to-image",
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

async def upscale_image(image: Image.Image, width: int = 2048):
    if api_key is None:
        raise Exception("Missing Stability API key.")

    # Convert the PIL Image to bytes
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    image_bytes = buffered.getvalue()

    # Create FormData object
    data = FormData()
    data.add_field('image', image_bytes, filename='init_image.png', content_type='image/png')
    data.add_field('width', str(width))

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{api_host}/v1/generation/esrgan-v1-x2plus/image-to-image/upscale",
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