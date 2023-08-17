# SDXL-DiscordBot

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