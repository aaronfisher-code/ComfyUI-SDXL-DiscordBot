import logging
import random

import discord
from discord import app_commands, Attachment
from discord.app_commands import Range

from src.command_descriptions import *
from src.consts import *
from src.image_gen.collage_utils import create_collage
from src.image_gen.ui.buttons import Buttons
from src.util import process_attachment, unpack_choices, should_filter, get_filename

logger = logging.getLogger("bot")

class ImageGenCommands:
    def __init__(self, tree: discord.app_commands.CommandTree):
        self.tree = tree

    def add_commands(self):
        @self.tree.command(name="legacy", description="Generate an image based on input text")
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
            aspect_ratio: str = None,
            sampler: str = None,
            num_steps: Range[int, 1, MAX_STEPS] = None,
            cfg_scale: Range[float, 1.0, MAX_CFG] = None,
            seed: int = None,
            input_file: Attachment = None,
            denoise_strength: Range[float, 0.01, 1.0] = None,
            inpainting_prompt: str = None,
            inpainting_detection_threshold: Range[int, 0, 255] = None,
            clip_skip: Range[int, -2, -1] = None,
        ):
            if input_file is not None:
                fp = await process_attachment(input_file, interaction)
                if fp is None:
                    return

            dimensions = sd_aspect_ratios[aspect_ratio] if aspect_ratio else sd_aspect_ratios[SD15_GENERATION_DEFAULTS.dimensions]
            dimensions = (dimensions[0] / 2, dimensions[1] / 2)

            params = ImageWorkflow(
                ModelType.SD15,
                WorkflowType.txt2img if input_file is None else WorkflowType.img2img,
                prompt,
                negative_prompt,
                model or SD15_GENERATION_DEFAULTS.model,
                unpack_choices(lora, lora2),
                [lora_strength, lora_strength2],
                dimensions,
                sampler or SD15_GENERATION_DEFAULTS.sampler,
                num_steps or SD15_GENERATION_DEFAULTS.num_steps,
                cfg_scale or SD15_GENERATION_DEFAULTS.cfg_scale,
                seed=seed,
                slash_command="imagine",
                filename=fp if input_file is not None else None,
                denoise_strength=denoise_strength or SD15_GENERATION_DEFAULTS.denoise_strength if input_file is not None else 1.0,
                batch_size=SD15_GENERATION_DEFAULTS.batch_size,
                inpainting_prompt=inpainting_prompt,
                inpainting_detection_threshold=inpainting_detection_threshold or SD15_GENERATION_DEFAULTS.inpainting_detection_threshold,
                clip_skip=clip_skip or SD15_GENERATION_DEFAULTS.clip_skip,
            )
            await self._do_request(
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
            clip_skip: Range[int, -2, -1] = None,
        ):
            params = ImageWorkflow(
                ModelType.VIDEO,
                WorkflowType.video,
                prompt,
                negative_prompt,
                model or VIDEO_GENERATION_DEFAULTS.model,
                unpack_choices(lora, lora2),
                [lora_strength, lora_strength2],
                (512, 512),
                sampler=sampler or VIDEO_GENERATION_DEFAULTS.sampler,
                num_steps=num_steps or VIDEO_GENERATION_DEFAULTS.num_steps,
                cfg_scale=cfg_scale or VIDEO_GENERATION_DEFAULTS.cfg_scale,
                seed=seed,
                slash_command="video",
                clip_skip=clip_skip or VIDEO_GENERATION_DEFAULTS.clip_skip,
            )
            await self._do_request(
                interaction,
                f'🎥{interaction.user.mention} asked me to create the video "{prompt}"! {random.choice(generation_messages)} 🎥',
                f'{interaction.user.mention} asked me to create the video "{prompt}"! {random.choice(completion_messages)} 🎥',
                "video",
                params,
            )

        @self.tree.command(name="cascade", description="Use Stable Cascade to generate an image")
        @app_commands.describe(**CASCADE_ARG_DESCS)
        @app_commands.choices(**CASCADE_ARG_CHOICES)
        async def slash_command(
                interaction: discord.Interaction,
                prompt: str,
                negative_prompt: str = None,
                aspect_ratio: str = None,
                num_steps: Range[int, 1, MAX_STEPS] = None,
                cfg_scale: Range[float, 1.0, MAX_CFG] = None,
                seed: int = None,
                input_file: Attachment = None,
                input_file2: Attachment = None,
                denoise_strength: Range[float, 0.01, 1.0] = None,
                inpainting_prompt: str = None,
                inpainting_detection_threshold: Range[int, 0, 255] = None,
                clip_skip: Range[int, -2, -1] = None,
        ):
            if input_file is not None:
                fp = await process_attachment(input_file, interaction)
                if fp is None:
                    return

            if input_file2 is not None:
                fp2 = await process_attachment(input_file2, interaction)
                if fp2 is None:
                    return

            params = ImageWorkflow(
                ModelType.CASCADE,
                WorkflowType.txt2img if input_file is None else WorkflowType.image_mashup if input_file is not None and input_file2 is not None else WorkflowType.img2img,
                prompt,
                negative_prompt,
                CASCADE_GENERATION_DEFAULTS.model,
                dimensions=sd_aspect_ratios[aspect_ratio] if aspect_ratio else sd_aspect_ratios[CASCADE_GENERATION_DEFAULTS.dimensions],
                sampler=CASCADE_GENERATION_DEFAULTS.sampler,
                num_steps=num_steps or CASCADE_GENERATION_DEFAULTS.num_steps,
                cfg_scale=cfg_scale or CASCADE_GENERATION_DEFAULTS.cfg_scale,
                denoise_strength=denoise_strength or CASCADE_GENERATION_DEFAULTS.denoise_strength,
                batch_size=CASCADE_GENERATION_DEFAULTS.batch_size,
                seed=seed,
                filename=fp if input_file is not None else None,
                filename2=fp2 if input_file2 is not None else None,
                inpainting_prompt=inpainting_prompt,
                inpainting_detection_threshold=inpainting_detection_threshold or CASCADE_GENERATION_DEFAULTS.inpainting_detection_threshold,
                clip_skip=clip_skip or CASCADE_GENERATION_DEFAULTS.clip_skip,
            )

            await self._do_request(
                interaction,
                f'🤖️ {interaction.user.mention} asked me to imagine "{prompt}" using Stable Cascade! {random.choice(generation_messages)} 🤖️',
                f'🤖️ {interaction.user.mention} asked me to imagine "{prompt}" using Stable Cascade! {random.choice(completion_messages)} 🤖️',
                "cascade",
                params,
            )


    async def _do_request(
        self,
        interaction: discord.Interaction,
        intro_message: str,
        completion_message: str,
        command_name: str,
        params: ImageWorkflow,
    ):
        try:
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

            await interaction.response.send_message(intro_message)

            if params.seed is None:
                params.seed = random.randint(0, 999999999999999)

            from src.comfy_workflows import do_workflow
            images = await do_workflow(params)

            final_message = f"{completion_message}\n Seed: {params.seed}"
            buttons = Buttons(params, images, interaction.user, command=command_name)

            file_name = get_filename(interaction, params)

            fname = f"{file_name}.gif" if "GIF" in images[0].format else f"{file_name}.png"
            await interaction.channel.send(content=final_message, file=discord.File(fp=create_collage(images), filename=fname), view=buttons)
        except Exception as e:
            logger.exception("Error generating image: %s for command %s with params %s", e, command_name, params)
            await interaction.channel.send(f"{interaction.user.mention} `Error generating image: {e} for command {command_name}`")


class SDXLCommand(ImageGenCommands):
    def __init__(self, tree: discord.app_commands.CommandTree, command_name: str):
        super().__init__(tree)
        self.command_name = command_name

    def add_commands(self):
        @self.tree.command(name=self.command_name, description="Generate an image using SDXL")
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
                clip_skip: Range[int, -2, -1] = None,
                use_accelerator_lora: Optional[bool] = None,
        ):
            if input_file is not None:
                fp = await process_attachment(input_file, interaction)
                if fp is None:
                    return

            params = ImageWorkflow(
                ModelType.SDXL,
                WorkflowType.txt2img if input_file is None else WorkflowType.img2img,
                prompt,
                negative_prompt,
                model or SDXL_GENERATION_DEFAULTS.model,
                unpack_choices(lora, lora2),
                [lora_strength, lora_strength2],
                dimensions=sd_aspect_ratios[aspect_ratio] if aspect_ratio else sd_aspect_ratios[SDXL_GENERATION_DEFAULTS.dimensions],
                batch_size=SDXL_GENERATION_DEFAULTS.batch_size,
                sampler=sampler or SDXL_GENERATION_DEFAULTS.sampler,
                num_steps=num_steps or SDXL_GENERATION_DEFAULTS.num_steps,
                cfg_scale=cfg_scale or SDXL_GENERATION_DEFAULTS.cfg_scale,
                seed=seed,
                slash_command="sdxl",
                filename=fp if input_file is not None else None,
                denoise_strength=denoise_strength or SDXL_GENERATION_DEFAULTS.denoise_strength if input_file is not None else 1.0,
                inpainting_prompt=inpainting_prompt,
                inpainting_detection_threshold=inpainting_detection_threshold or SDXL_GENERATION_DEFAULTS.inpainting_detection_threshold,
                clip_skip=clip_skip or SDXL_GENERATION_DEFAULTS.clip_skip,
                use_accelerator_lora=use_accelerator_lora or SDXL_GENERATION_DEFAULTS.use_accelerator_lora,
                accelerator_lora_name=SDXL_GENERATION_DEFAULTS.accelerator_lora_name if use_accelerator_lora or SDXL_GENERATION_DEFAULTS.use_accelerator_lora else None,
                scheduler=SDXL_GENERATION_DEFAULTS.scheduler,
            )

            await self._do_request(
                interaction,
                f'🖌️{interaction.user.mention} asked me to imagine "{prompt}" using SDXL! {random.choice(generation_messages)} 🖌️',
                f'🖌️ {interaction.user.mention} asked me to imagine "{prompt}" using SDXL! {random.choice(completion_messages)}. 🖌️',
                "sdxl",
                params,
            )