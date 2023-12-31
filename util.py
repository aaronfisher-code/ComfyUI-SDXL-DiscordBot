import configparser
import os


def read_config():
    config = configparser.ConfigParser()
    config.read("config.properties")
    return config


def generate_default_config():
    config = configparser.ConfigParser()
    config["BOT"] = {"TOKEN": "YOUR_DEFAULT_DISCORD_BOT_TOKEN"}
    config["LOCAL"] = {"SERVER_ADDRESS": "YOUR_COMFYUI_URL"}
    with open("config.properties", "w") as configfile:
        config.write(configfile)


def setup_config():
    if not os.path.exists("config.properties"):
        generate_default_config()

    if not os.path.exists("./out"):
        os.makedirs("./out")

    config = read_config()
    token = (
        os.environ["DISCORD_APP_TOKEN"]
        if "DISCORD_APP_TOKEN" in os.environ
        else config["BOT"]["TOKEN"]
    )
    return token


def should_filter(positive_prompt: str, negative_prompt: str) -> bool:
    positive_prompt = positive_prompt or ""
    negative_prompt = negative_prompt or ""

    config = read_config()
    word_list = config["BLOCKED_WORDS"]["WORDS"].split(",")
    if word_list is None:
        return False
    for word in word_list:
        if word.lower() in positive_prompt.lower() or word in negative_prompt.lower():
            return True
    return False


def unpack_choices(*args):
    return [x is not None and x.value or None for x in args]
