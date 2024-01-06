import random

import discord
from discord import app_commands, Attachment
from discord.app_commands import Range

from src.comfy_api import refresh_models, logger
from src.command_descriptions import *
from src.consts import *
from src.image_gen.collage_utils import create_collage
from src.image_gen.image_gen import generate_images
from src.image_gen.ui.buttons import Buttons
from util import process_attachment, unpack_choices, should_filter, get_filename


class ImageGenCommands():
    def __init__(self, tree: discord.app_commands.CommandTree):
        self.tree = tree

    def add_commands(self):
        @self.tree.command(name="refresh", description="Refresh the list of models and loras")
        async def slash_command(interaction: discord.Interaction):
            await refresh_models()
            await interaction.response.send_message("Refreshed models and loras", ephemeral=True)

        @self.tree.command(name="imagine", description="Generate an image based on input text")
        @app_commands.describe(**IMAGINE_ARG_DESCS)
        @app_commands.choices(**IMAGINE_ARG_CHOICES)
        async def slash_command(
                interaction: discord.Interaction,
                prompt: str,
                negative_prompt: str = None,
                model: str = None,
                lora: Choice[str] = None,
                lora_strength: float = 1.0,
                lora2: Choice[str] = None,
                lora_strength2: float = 1.0,
                # enhance: bool = False,
                aspect_ratio: str = None,
                sampler: str = None,
                num_steps: Range[int, 1, MAX_STEPS] = None,
                cfg_scale: Range[float, 1.0, MAX_CFG] = None,
                seed: int = None,
                input_file: Attachment = None,
                denoise_strength: Range[float, 0.01, 1.0] = None,
                inpainting_prompt: str = None,
                inpainting_detection_threshold: Range[int, 0, 255] = None,
        ):
            if input_file is not None:
                fp = await process_attachment(input_file, interaction)
                if fp is None:
                    return

            params = ImageWorkflow(
                SD15_INPAINT_WORKFLOW if inpainting_prompt is not None and input_file is not None else SD15_ALTS_WORKFLOW if input_file is not None else SD15_WORKFLOW,
                prompt,
                negative_prompt,
                model or SD15_GENERATION_DEFAULTS.model,
                unpack_choices(lora, lora2),
                [lora_strength, lora_strength2],
                aspect_ratio or SD15_GENERATION_DEFAULTS.aspect_ratio,
                sampler or SD15_GENERATION_DEFAULTS.sampler,
                num_steps or SD15_GENERATION_DEFAULTS.num_steps,
                cfg_scale or SD15_GENERATION_DEFAULTS.cfg_scale,
                seed=seed,
                slash_command="imagine",
                filename=fp if input_file is not None else None,
                denoise_strength=denoise_strength or SD15_GENERATION_DEFAULTS.denoise_strength if input_file is not None else 1.0,
                inpainting_prompt=inpainting_prompt,
                inpainting_detection_threshold=inpainting_detection_threshold or SD15_GENERATION_DEFAULTS.inpainting_detection_threshold
            )
            await self.__do_request(
                interaction,
                f'🖼️ {interaction.user.mention} asked me to imagine "{prompt}"! {random.choice(generation_messages)} 🖼️',
                f'{interaction.user.mention} asked me to imagine "{prompt}"! {random.choice(completion_messages)}',
                "imagine",
                params,
            )

        @self.tree.command(name="video", description="Generate a video based on input text")
        @app_commands.describe(**VIDEO_ARG_DESCS)
        @app_commands.choices(**VIDEO_ARG_CHOICES)
        async def slash_command(
                interaction: discord.Interaction,
                prompt: str,
                negative_prompt: str = None,
                model: str = None,
                lora: Choice[str] = None,
                lora_strength: float = 1.0,
                lora2: Choice[str] = None,
                lora_strength2: float = 1.0,
                sampler: str = None,
                num_steps: Range[int, 1, MAX_STEPS] = None,
                cfg_scale: Range[float, 1.0, MAX_CFG] = None,
                seed: int = None,
        ):
            params = ImageWorkflow(
                VIDEO_WORKFLOW,
                prompt,
                negative_prompt,
                model or VIDEO_GENERATION_DEFAULTS.model,
                unpack_choices(lora, lora2),
                [lora_strength, lora_strength2],
                None,
                sampler=sampler or VIDEO_GENERATION_DEFAULTS.sampler,
                num_steps=num_steps or VIDEO_GENERATION_DEFAULTS.num_steps,
                cfg_scale=cfg_scale or VIDEO_GENERATION_DEFAULTS.cfg_scale,
                seed=seed,
                slash_command="video",
            )
            await self.__do_request(
                interaction,
                f'🎥{interaction.user.mention} asked me to create the video "{prompt}"! {random.choice(generation_messages)} 🎥',
                f'{interaction.user.mention} asked me to create the video "{prompt}"! {random.choice(completion_messages)} 🎥',
                "video",
                params,
            )

        @self.tree.command(name="sdxl", description="Generate an image using SDXL")
        @app_commands.describe(**SDXL_ARG_DESCS)
        @app_commands.choices(**SDXL_ARG_CHOICES)
        async def slash_command(
                interaction: discord.Interaction,
                prompt: str,
                negative_prompt: str = None,
                model: str = None,
                lora: Choice[str] = None,
                lora_strength: float = 1.0,
                lora2: Choice[str] = None,
                lora_strength2: float = 1.0,
                aspect_ratio: str = None,
                sampler: str = None,
                num_steps: Range[int, 1, MAX_STEPS] = None,
                cfg_scale: Range[float, 1.0, MAX_CFG] = None,
                seed: int = None,
                input_file: Attachment = None,
                denoise_strength: Range[float, 0.01, 1.0] = None,
                inpainting_prompt: str = None,
                inpainting_detection_threshold: Range[int, 0, 255] = None,
        ):
            if input_file is not None:
                fp = await process_attachment(input_file, interaction)
                if fp is None:
                    return

            params = ImageWorkflow(
                SDXL_INPAINT_WORKFLOW if inpainting_prompt is not None and input_file is not None else SDXL_ALTS_WORKFLOW if input_file is not None else SDXL_WORKFLOW,
                prompt,
                negative_prompt,
                model or SDXL_GENERATION_DEFAULTS.model,
                unpack_choices(lora, lora2),
                [lora_strength, lora_strength2],
                aspect_ratio or SDXL_GENERATION_DEFAULTS.aspect_ratio,
                sampler=sampler or SDXL_GENERATION_DEFAULTS.sampler,
                num_steps=num_steps or SDXL_GENERATION_DEFAULTS.num_steps,
                cfg_scale=cfg_scale or SDXL_GENERATION_DEFAULTS.cfg_scale,
                seed=seed,
                slash_command="sdxl",
                filename=fp if input_file is not None else None,
                denoise_strength=denoise_strength or SDXL_GENERATION_DEFAULTS.denoise_strength if input_file is not None else 1.0,
                inpainting_prompt=inpainting_prompt,
                inpainting_detection_threshold=inpainting_detection_threshold or SDXL_GENERATION_DEFAULTS.inpainting_detection_threshold
            )
            await self.__do_request(
                interaction,
                f'🖌️{interaction.user.mention} asked me to imagine "{prompt}" using SDXL! {random.choice(generation_messages)} 🖌️',
                f'🖌️ {interaction.user.mention} asked me to imagine "{prompt}" using SDXL! {random.choice(completion_messages)}. 🖌️',
                "sdxl",
                params,
            )

    async def __do_request(
            self,
            interaction: discord.Interaction,
            intro_message: str,
            completion_message: str,
            command_name: str,
            params: ImageWorkflow,
    ):
        if should_filter(params.prompt, params.negative_prompt):
            logger.info(
                "Prompt or negative prompt contains a blocked word, not generating image. Prompt: %s, Negative Prompt: %s",
                params.prompt,
                params.negative_prompt,
            )
            await interaction.response.send_message(
                f"The prompt {params.prompt} or negative prompt {params.negative_prompt} contains a blocked word, not generating image.",
                ephemeral=True,
            )
            return

        # Send an initial message
        await interaction.response.send_message(intro_message)

        if params.seed is None:
            params.seed = random.randint(0, 999999999999999)

        images, enhanced_prompt = await generate_images(params)

        final_message = f"{completion_message}\n Seed: {params.seed}"
        buttons = Buttons(params, images, interaction.user, command=command_name)

        file_name = get_filename(interaction, params)

        fname = f"{file_name}.gif" if "GIF" in images[0].format else f"{file_name}.png"
        await interaction.channel.send(
            content=final_message, file=discord.File(fp=create_collage(images), filename=fname), view=buttons
        )
