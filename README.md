# SDXL-DiscordBot


<p float="left" align="center">
  <img src="https://github.com/dab-bot/ComfyUI-SDXL-DiscordBot/assets/79825913/b206c020-d56f-4a09-b990-21ffc8b94296" height="300px" align="top" />
  <img src="https://github.com/dab-bot/ComfyUI-SDXL-DiscordBot/assets/79825913/a1581e4c-9dbf-44d8-9891-3499c4f8cb6b" height="300px" align="top" /> 
  <img src="https://github.com/dab-bot/ComfyUI-SDXL-DiscordBot/assets/79825913/3a046c12-be79-4323-a081-b22c0bfdc5f2" height="300px" align="top" />
</p>

**SDXL-DiscordBot** is a Discord bot designed specifically for image generation using the renowned SDXL 1.0 model. It's inspired by the features of the Midjourney Discord bot, offering capabilities like text-to-image generation, variations in outputs, and the ability to upscale these outputs for enhanced clarity.

<div align="center">
  
[![Support my work](https://i.imgur.com/NOoWZ8G.png)](https://ko-fi.com/dab_bot)

</div>


## Key Features:

1. **Text-to-Image Generation**: Convert your ideas into visuals. Just type in a positive+negative prompt, and the bot will generate an image that matches your text.

2. **Variations on Outputs**: Not satisfied with the first image? The bot can produce multiple variations, giving you the freedom to choose the one that fits best.

3. **Upscale Outputs**: Enhance the clarity of generated images by upscaling them. Perfect for when you need higher resolution visuals.

4. **Integration Flexibility**: 
   - **Public Stability AI API**: For those who prefer a hassle-free setup, the bot can integrate seamlessly with the public Stability AI API. All you need is your API key.
   - **Local ComfyUI System**: For users who prioritize data privacy or want to work offline, the bot can run locally using the ComfyUI system.

5. **Custom Workflows with ComfyUI**: The bot comes with default configurations that cater to most users. However, if you have specific needs, it supports custom ComfyUI workflows, allowing you to tailor the bot's operations to your exact requirements.

## Quick Start

### 1. **Download & Extract**
- [Download the latest executable](https://github.com/dab-bot/ComfyUI-SDXL-DiscordBot/releases) suitable for your OS.
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
- Ensure that ComfyUI is running while the bot is running

### 4. **Run the App**
- Double-click on `SDXL-Bot.exe` to launch.
- **Note for Windows users:** If Windows Defender warns about an "unknown publisher", you can safely ignore it. You might also need to whitelist this app in your antivirus software.

## Advanced setup
For more advanced configuration and custom workflows visit the [wiki](https://github.com/dab-bot/ComfyUI-SDXL-DiscordBot/wiki/Advanced-config)
