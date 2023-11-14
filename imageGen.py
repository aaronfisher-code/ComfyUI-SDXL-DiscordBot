import websockets
import uuid
import json
import random
import urllib.request
import urllib.parse
from PIL import Image
from io import BytesIO
import configparser
import os
import tempfile
import requests

# Read the configuration
config = configparser.ConfigParser()
config.read('config.properties')
server_address = config['LOCAL']['SERVER_ADDRESS']

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
    
def upload_image(filepath, subfolder=None, folder_type=None, overwrite=False):
    url = f"http://{server_address}/upload/image"
    files = {'image': open(filepath, 'rb')}
    data = {
        'overwrite': str(overwrite).lower()
    }
    if subfolder:
        data['subfolder'] = subfolder
    if folder_type:
        data['type'] = folder_type
    response = requests.post(url, files=files, data=data)
    return response.json()

def get_models():
    with urllib.request.urlopen("http://{}/object_info".format(server_address)) as response:
        object_info = json.loads(response.read())
        return object_info['CheckpointLoaderSimple']['input']['required']['ckpt_name']

def get_loras():
    with urllib.request.urlopen("http://{}/object_info".format(server_address)) as response:
        object_info = json.loads(response.read())
        return object_info['LoraLoader']['input']['required']['lora_name']

class ImageGenerator:
    def __init__(self):
        self.client_id = str(uuid.uuid4())
        self.uri = f"ws://{server_address}/ws?clientId={self.client_id}"
        self.ws = None

    async def connect(self):
        self.ws = await websockets.connect(self.uri)

    async def get_images(self, prompt):
        if not self.ws:
            await self.connect()
    
        prompt_id = queue_prompt(prompt, self.client_id)['prompt_id']
        currently_Executing_Prompt = None
        output_images = []
        full_prompt = None
        async for out in self.ws:
            try:
                message = json.loads(out)
                if message['type'] == 'execution_start':
                    currently_Executing_Prompt = message['data']['prompt_id']
                if message['type'] == 'executing' and prompt_id == currently_Executing_Prompt:
                    data = message['data']
                    if data['node'] is None and data['prompt_id'] == prompt_id:
                        break
            except ValueError as e:
                print("Incompatible response from ComfyUI");
                
        history = get_history(prompt_id)[prompt_id]

        for node_id in history['outputs']:
            node_output = history['outputs'][node_id]
            if("text" in node_output):
                for prompt in node_output["text"]:
                    full_prompt = prompt
            if 'images' in node_output:
                for image in node_output['images']:
                    image_data = get_image(image['filename'], image['subfolder'], image['type'])
                    if 'final_output' in image['filename']:
                        pil_image = Image.open(BytesIO(image_data))
                        output_images.append(pil_image)

        for node_id in history['outputs']:
            node_output = history['outputs'][node_id]
            if 'gifs' in node_output:
                for gif in node_output['gifs']:
                    image_data = get_image(gif['filename'], gif['subfolder'], gif['type'])
                    if 'final_output' in gif['filename']:
                        pil_image = Image.open(BytesIO(image_data))
                        output_images.append(pil_image)

        return output_images, full_prompt

    async def close(self):
        if self.ws:
            await self.ws.close()

def setup_workflow(workflow, prompt: str, negative_prompt: str, model: str, lora: str, lora_strength : float, config_name: str, aspect_ratio: str, filename: str = None, denoise_strength: float = None):
    prompt_nodes = config.get(config_name, 'PROMPT_NODES').split(',')
    neg_prompt_nodes = config.get(config_name, 'NEG_PROMPT_NODES').split(',')
    rand_seed_nodes = config.get(config_name, 'RAND_SEED_NODES').split(',')
    model_node = config.get(config_name, 'MODEL_NODE').split(',')
    lora_node = config.get(config_name, 'LORA_NODE').split(',')
    empty_image_node = config.get(config_name, 'EMPTY_IMAGE_NODE').split(',')
    llm_model_node = None

    if (config.has_option(config_name, 'FILE_INPUT_NODES')):
        file_input_nodes = config.get(config_name, 'FILE_INPUT_NODES').split(',')

    if(config.has_option(config_name, 'LLM_MODEL_NODE')):
        llm_model_node = config.get(config_name, 'LLM_MODEL_NODE')

    # Modify the prompt dictionary
    if (prompt != None and prompt_nodes[0] != ''):
        for node in prompt_nodes:
            if ("text" in workflow[node]["inputs"]):
                workflow[node]["inputs"]["text"] = prompt
            elif ("prompt" in workflow[node]["inputs"]):
                workflow[node]["inputs"]["prompt"] = prompt
    if (negative_prompt != None and neg_prompt_nodes[0] != ''):
        for node in neg_prompt_nodes:
            workflow[node]["inputs"]["text"] = negative_prompt + ", (children, child, kids, kid:1.3)"
    if (filename != None):
        for node in file_input_nodes:
            workflow[node]["inputs"]["image"] = filename
    if (rand_seed_nodes[0] != ''):
        for node in rand_seed_nodes:
            workflow[node]["inputs"]["seed"] = random.randint(0, 999999999999999)
    if (model_node[0] != '' and model != None):
        for node in model_node:
            workflow[node]["inputs"]["ckpt_name"] = model
    if (lora_node[0] != '' and lora != None):
        for node in lora_node:
            workflow[node]["inputs"]["lora_01"] = lora.value
            workflow[node]["inputs"]["strength_01"] = lora_strength
    if (llm_model_node != None):
        workflow[llm_model_node]["inputs"]["model_dir"] = config["LOCAL"]["LLM_MODEL_LOCATION"]
    if(aspect_ratio != None and empty_image_node != None):
        workflow[node]["inputs"]["dimensions"] = aspect_ratio
    if (denoise_strength != None):
        denoise_node = config.get(config_name, 'DENOISE_NODE').split(',')
        for node in denoise_node:
            workflow[node]["inputs"]["denoise"] = denoise_strength
        if (config.has_option(config_name, 'LATENT_IMAGE_NODE')):
            latent_image_node = config.get(config_name, 'LATENT_IMAGE_NODE').split(',')
            for node in latent_image_node:
                workflow[node]["inputs"]["amount"] = 1

    return workflow

async def generate_images(prompt: str,negative_prompt: str, model: str = None, lora: str = None, lora_strength : float = 1.0, config_name: str = 'LOCAL_TEXT2IMG', aspect_ratio: str = None):
    with open(config[config_name]['CONFIG'], 'r') as file:
        workflow = json.load(file)

    generator = ImageGenerator()
    await generator.connect()

    setup_workflow(workflow, prompt, negative_prompt, model, lora, lora_strength, config_name, aspect_ratio)

    images, enhanced_prompt = await generator.get_images(workflow)
    await generator.close()

    return images, enhanced_prompt

async def generate_alternatives(image: Image.Image, prompt: str, negative_prompt: str, model: str = None, lora: str = None, lora_strength : float = 1.0, config_name: str = "LOCAL_IMG2IMG", denoise_strength: float = None):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
      image.save(temp_file, format="PNG")
      temp_filepath = temp_file.name

    # Upload the temporary file using the upload_image method
    response_data = upload_image(temp_filepath)
    filename = response_data['name']

    with open(config[config_name]['CONFIG'], 'r') as file:
        workflow = json.load(file)
      
    generator = ImageGenerator()
    await generator.connect()

    setup_workflow(workflow, prompt, negative_prompt, model, lora, lora_strength, config_name, filename, denoise_strength)

    images, enhanced_prompt = await generator.get_images(workflow)
    await generator.close()

    return images

async def upscale_image(image: Image.Image, prompt: str,negative_prompt: str, model: str = None, lora: str = None, lora_strength : float = 1.0, config_name: str = "LOCAL_UPSCALE", denoise_strength: float = None):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
      image.save(temp_file, format="PNG")
      temp_filepath = temp_file.name

    # Upload the temporary file using the upload_image method
    response_data = upload_image(temp_filepath)
    filename = response_data['name']
    with open(config[config_name]['CONFIG'], 'r') as file:
      workflow = json.load(file)

    generator = ImageGenerator()
    await generator.connect()

    setup_workflow(workflow, prompt, negative_prompt, model, lora, lora_strength, config_name, filename, denoise_strength)

    images, enhanced_prompt = await generator.get_images(workflow)
    await generator.close()

    return images[0]