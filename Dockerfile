FROM ubuntu:rolling

ARG DEBIAN_FRONTEND=noninteractive
ARG TZ=UTC

RUN apt-get update
RUN apt install -y python3 python3-pip python3-virtualenv git

RUN useradd -m -s /bin/bash bot
RUN mkdir -p /workspace/comfyUI-workflows && chown -R bot:bot /workspace

COPY --chown=bot:bot *.py config.properties requirements.txt /workspace/
COPY --chown=bot:bot comfyUI-workflows/*.json /workspace/comfyUI-workflows/

USER bot
WORKDIR /workspace

RUN python3 -m virtualenv venv
ENV PATH="/workspace/venv/bin:$PATH"

RUN python3 -m pip install -r requirements.txt

CMD ["python3", "bot.py"]
