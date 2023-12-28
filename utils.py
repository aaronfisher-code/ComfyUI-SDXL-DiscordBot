from discord import Interaction

from imageGen import ImageWorkflow


def get_filename(interaction: Interaction, params: ImageWorkflow):
    return f"{interaction.user.name}_{params.prompt[:10]}_{params.seed}"
