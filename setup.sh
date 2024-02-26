#!/bin/bash

if [ ! -e venv ]; then
    python3 -m venv --copies venv
    echo "created new virtualenv"
fi

source venv/bin/activate
pip install -r requirements.txt

if [ ! -f config.properties ]; then
    cp config.properties.example config.properties
    echo "copied example config to config.properties"
    echo "add your bot token and comfyui server address to this config"
else
    echo "found existing config.properties; not overwriting"
fi

# set install location variable
export EMBEDDED_COMFY_LOCATION="$(pwd)/embedded_comfy"
comfyui --cwd=EMBEDDED_COMFY_LOCATION --create_directories

cd EMBEDDED_COMFY_LOCATION/custom_nodes
git clone https://github.com/Chaoses-Ib/ComfyScript.git
cd ComfyScript
python -m pip install -e ".[default]"
