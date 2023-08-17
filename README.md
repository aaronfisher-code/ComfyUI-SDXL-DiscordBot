# SDXL-DiscordBot

<p float="center">
  <img src="https://github.com/s3840619/ComfyUI-SDXL-DiscordBot/assets/79825913/4d9f60f5-6937-4c73-b5a2-0ff665ac2360" height="300px" align="top" />
  <img src="https://github.com/s3840619/ComfyUI-SDXL-DiscordBot/assets/79825913/d4c4f26e-b6de-4874-87f9-49d5f5a5ab2a" height="300px" align="top" /> 
  <img src="https://github.com/s3840619/ComfyUI-SDXL-DiscordBot/assets/79825913/8e0134df-77b2-4e0e-8018-7015090f3a20" height="300px" align="top" />
</p>




## Quick Start

### 1. **Download & Extract**
- [Download the latest executable](https://github.com/s3840619/ComfyUI-SDXL-DiscordBot/releases) suitable for your OS.
- Extract the zip file to your desired location.

### 2. **Configuration**
- Open `config.properties` using a text editor.
- Set your Discord bot token: Find `[BOT][TOKEN]` and replace the placeholder with your token.

### 3. **Choose Your Source**

#### Option A: **The Stability AI API**
- Set your API key: Replace the placeholder in `[API][API_KEY]` with your StabilityAI API key.
- Update the source: Change `[BOT][SDXL_SOURCE]` to 'API'.

#### Option B: **Local System via ComfyUI**
- Set your ComfyUI URL: Replace the placeholder in `[LOCAL][SERVER_ADDRESS]` with your ComfyUI URL (default is `127.0.0.1:8188`).
- Update the source: Change `[BOT][SDXL_SOURCE]` to 'LOCAL'.
- Download and add models to ComfyUI:
  - [SDXL 1.0 Base model](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors) → `checkpoints` folder
  - [SDXL 1.0 Refiner model](https://huggingface.co/stabilityai/stable-diffusion-xl-refiner-1.0/resolve/main/sd_xl_refiner_1.0.safetensors) → `checkpoints` folder
  - [ESRGAN 2x Upscaler model](https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth) → `upscale_models` folder

### 4. **Run the App**
- Double-click on `SDXL-Bot.exe` to launch.
- **Note for Windows users:** If Windows Defender warns about an "unknown publisher", you can safely ignore it. You might also need to whitelist this app in your antivirus software.
