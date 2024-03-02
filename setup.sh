#!/bin/bash

TORCH_CUDA_INDEX_URL=https://download.pytorch.org/whl/cu121  # for cuda 12.1
CUDA_VER=12.1

if [ ! -d venv ]; then
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

ROOT_DIR=$(pwd)
EMBEDDED_COMFY_LOCATION="$ROOT_DIR/embedded_comfy"

mkdir -p input out

if [ ! -d "$EMBEDDED_COMFY_LOCATION" ]; then
    git clone https://github.com/comfyanonymous/ComfyUI.git "$EMBEDDED_COMFY_LOCATION"
    echo "created embedded comfy directory"
fi

cd "$EMBEDDED_COMFY_LOCATION"
pip install -r requirements.txt -U --extra-index-url https://download.pytorch.org/whl/cu121

cd "$EMBEDDED_COMFY_LOCATION/custom_nodes"
if [ ! -d ComfyScript ]; then
    git clone https://github.com/Chaoses-Ib/ComfyScript.git
    echo "cloned ComfyScript"
fi
cd ComfyScript
pip install -e ".[default]"


cd "$EMBEDDED_COMFY_LOCATION/custom_nodes"
if [ ! -d ComfyUI_Ib_CustomNodes ]; then
    git clone https://github.com/Chaoses-Ib/ComfyUI_Ib_CustomNodes.git
    echo "cloned ComfyUI_Ib_CustomNodes"
fi
cd ComfyUI_Ib_CustomNodes
pip install -r requirements.txt -U

cd "$EMBEDDED_COMFY_LOCATION/custom_nodes"
if [ ! -d was-node-suite-comfyui ]; then
    git clone https://github.com/WASasquatch/was-node-suite-comfyui.git
    echo "cloned was node suite"
fi
cd was-node-suite-comfyui
pip install -r requirements.txt -U

cd "$EMBEDDED_COMFY_LOCATION/custom_nodes"
if [ ! -d ComfyUI_Comfyroll_CustomNodes ]; then
    git clone https://github.com/Suzie1/ComfyUI_Comfyroll_CustomNodes.git
    echo "cloned ComfyUI_Comfyroll_CustomNodes"
fi

if [ ! -d ComfyUI-AnimateDiff-Evolved ]; then
  git clone https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved.git
  echo "cloned ComfyUI-AnimateDiff-Evolved"
fi

if [ ! -d ComfyUI-VideoHelperSuite ]; then
  git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git
  echo "cloned ComfyUI-VideoHelperSuite"
fi
cd ComfyUI-VideoHelperSuite
pip install -r requirements.txt -U --extra-index-url %TORCH_CUDA_INDEX_URL%

if [ ! -d ComfyUI-audio ]; then
  git clone https://github.com/eigenpunk/ComfyUI-audio.git
  echo "cloned ComfyUI-audio"
fi
cd ComfyUI-audio
pip install -r requirements.txt -U --extra-index-url %TORCH_CUDA_INDEX_URL%

cd "$EMBEDDED_COMFY_LOCATION/ComfyUI-VideoHelperSuite"
pip install -r requirements.txt -U

cd "$EMBEDDED_COMFY_LOCATION/models/checkpoints"
mkdir -p xl 15 cascade

cd "$EMBEDDED_COMFY_LOCATION/models/loras"
mkdir -p xl 15 cascade

cd "$EMBEDDED_COMFY_LOCATION/models/controlnet"
mkdir -p xl 15 cascade

cd "$EMBEDDED_COMFY_LOCATION"
python main.py --quick-test-for-ci
