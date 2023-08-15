import websockets
import uuid
import json
import random
import urllib.request
import urllib.parse
from PIL import Image
import io
import configparser

# Read the configuration
config = configparser.ConfigParser()
config.read('config.properties')
server_address = config['DEFAULT']['SERVER_ADDRESS']

def queue_prompt(prompt, client_id):
    p = {"prompt": prompt, "client_id": client_id}
    data = json.dumps(p).encode('utf-8')
    req =  urllib.request.Request("http://{}/prompt".format(server_address), data=data)
    return json.loads(urllib.request.urlopen(req).read())

def get_image(filename, subfolder, folder_type):
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    with urllib.request.urlopen("http://{}/view?{}".format(server_address, url_values)) as response:
        return response.read()

def get_history(prompt_id):
    with urllib.request.urlopen("http://{}/history/{}".format(server_address, prompt_id)) as response:
        return json.loads(response.read())

prompt_text = """
{
  "4": {
    "inputs": {
      "ckpt_name": "sd_xl_base_1.0.safetensors"
    },
    "class_type": "CheckpointLoaderSimple"
  },
  "6": {
    "inputs": {
      "text": "",
      "clip": [
        "4",
        1
      ]
    },
    "class_type": "CLIPTextEncode"
  },
  "7": {
    "inputs": {
      "text": "",
      "clip": [
        "4",
        1
      ]
    },
    "class_type": "CLIPTextEncode"
  },
  "8": {
    "inputs": {
      "samples": [
        "17",
        0
      ],
      "vae": [
        "4",
        2
      ]
    },
    "class_type": "VAEDecode"
  },
  "9": {
    "inputs": {
      "filename_prefix": "base_output",
      "images": [
        "8",
        0
      ]
    },
    "class_type": "SaveImage"
  },
  "11": {
    "inputs": {
      "ckpt_name": "sd_xl_refiner_1.0.safetensors"
    },
    "class_type": "CheckpointLoaderSimple"
  },
  "12": {
    "inputs": {
      "text": "",
      "clip": [
        "11",
        1
      ]
    },
    "class_type": "CLIPTextEncode"
  },
  "13": {
    "inputs": {
      "text": "",
      "clip": [
        "11",
        1
      ]
    },
    "class_type": "CLIPTextEncode"
  },
  "17": {
    "inputs": {
      "seed": 1002925642440624,
      "steps": 20,
      "cfg": 6,
      "sampler_name": "dpmpp_2s_ancestral",
      "scheduler": "normal",
      "denoise": 1,
      "model": [
        "4",
        0
      ],
      "positive": [
        "6",
        0
      ],
      "negative": [
        "7",
        0
      ],
      "latent_image": [
        "21",
        0
      ]
    },
    "class_type": "KSampler"
  },
  "18": {
    "inputs": {
      "samples": [
        "20",
        0
      ],
      "vae": [
        "11",
        2
      ]
    },
    "class_type": "VAEDecode"
  },
  "19": {
    "inputs": {
      "filename_prefix": "refiner_output",
      "images": [
        "18",
        0
      ]
    },
    "class_type": "SaveImage"
  },
  "20": {
    "inputs": {
      "seed": 84204593769148,
      "steps": 15,
      "cfg": 8,
      "sampler_name": "dpmpp_2m",
      "scheduler": "normal",
      "denoise": 0.25,
      "model": [
        "11",
        0
      ],
      "positive": [
        "12",
        0
      ],
      "negative": [
        "13",
        0
      ],
      "latent_image": [
        "17",
        0
      ]
    },
    "class_type": "KSampler"
  },
  "21": {
    "inputs": {
      "width": 1080,
      "height": 1080,
      "batch_size": 1
    },
    "class_type": "EmptyLatentImage"
  }
}
"""

prompt = json.loads(prompt_text)

async def update_progress(interaction, progress,stage):
    msg = await interaction.original_response()
    await msg.edit(content=f"Generating Image: {stage} - {progress}% Complete")

class ImageGenerator:
    def __init__(self):
        self.client_id = str(uuid.uuid4())
        self.uri = f"ws://{server_address}/ws?clientId={self.client_id}"
        self.ws = None

    async def connect(self):
        self.ws = await websockets.connect(self.uri)

    async def get_images(self, interaction, prompt):
        if not self.ws:
            await self.connect()
    
        prompt_id = queue_prompt(prompt, self.client_id)['prompt_id']
        currently_Executing_Prompt = None  # Local variable
        output_images = {}
        async for out in self.ws:
            message = json.loads(out)
            if message['type'] == 'execution_start':
                currently_Executing_Prompt = message['data']['prompt_id']

            if (message['type'] == 'executing' or message['type'] == 'progress') and prompt_id == currently_Executing_Prompt:
                if message['type'] == 'executing':
                    data = message['data']
                    if data['node'] is None and data['prompt_id'] == prompt_id:
                        msg = await interaction.original_response()
                        await msg.edit(content=f"Image generation complete!")
                        break #Execution is done
                elif message['type'] == 'progress':
                    current_value = message['data']['value']
                    max_value = message['data']['max']
                    progress = int((current_value / max_value) * 100)  # Calculate progress percentage
                    stage =  '(Step 1/2: Creating base)' if (max_value==20) else "(Step 2/2: Refining)"
                    if interaction:
                        await update_progress(interaction, progress, stage)

            if message['type'] == 'status' and prompt_id != currently_Executing_Prompt:
                queue_remaining = message['data']['status']['exec_info']['queue_remaining']
                # Inform the user about their position in the queue
                msg = await interaction.original_response()
                await msg.edit(content=f"There are currently {queue_remaining-1} requests in the queue, Thankyou for your patience")
                

        history = get_history(prompt_id)[prompt_id]
        base_images_output = []
        refined_images_output = []

        for node_id in history['outputs']:
            node_output = history['outputs'][node_id]
            if 'images' in node_output:
                for image in node_output['images']:
                    image_data = get_image(image['filename'], image['subfolder'], image['type'])
                    if 'refiner_output' in image['filename']:
                        refined_images_output.append(image_data)
                    else:
                        base_images_output.append(image_data)

        output_images = {
            'base': base_images_output,
            'refined': refined_images_output
        }

        return output_images

    async def close(self):
        if self.ws:
            await self.ws.close()

async def generate_image(text: str, interaction):
    generator = ImageGenerator()
    await generator.connect()
    prompt["6"]["inputs"]["text"] = text
    prompt["12"]["inputs"]["text"] = text
    prompt["17"]["inputs"]["seed"] = random.randint(-1, 99999999999999)
    prompt["20"]["inputs"]["seed"] = random.randint(-1, 99999999999999)

    images = await generator.get_images(interaction, prompt)

    await generator.close()

    # Extract base and refined images
    base_image_data = images['base'][0] if 'base' in images and images['base'] else None
    refined_image_data = images['refined'][0] if 'refined' in images and images['refined'] else None

    bImg = None
    rImg = None

    # Convert and send base image
    if base_image_data:
        base_image = Image.open(io.BytesIO(base_image_data))
        base_image_binary = io.BytesIO()
        base_image.save(base_image_binary, 'PNG')
        base_image_binary.seek(0)
        bImg = base_image_binary

    # Convert and send refined image
    if refined_image_data:
        refined_image = Image.open(io.BytesIO(refined_image_data))
        refined_image_binary = io.BytesIO()
        refined_image.save(refined_image_binary, 'PNG')
        refined_image_binary.seek(0)
        rImg = refined_image_binary

    return bImg, rImg
    