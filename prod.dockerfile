FROM nvidia/cuda:12.3.2-cudnn9-runtime-ubuntu22.04 AS builder
WORKDIR /app

ENV PATH="/root/.local/bin:$PATH"
ENV VENV_PATH=/app/.venv
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        curl \
        build-essential \
        python3.10 \
        python3-dev \
        python3-pip \
        libgl1 \
        libglib2.0-0 libsm6 libxrender1 libxext6 \
    && curl -sSL https://install.python-poetry.org | python3 - \
    && poetry --version \
    && rm -rf /var/lib/apt/lists/*

ADD pyproject.toml poetry.lock /app/
RUN poetry config virtualenvs.in-project true &&\
     poetry config virtualenvs.options.always-copy true &&\
     poetry install  --no-interaction --no-ansi -vvv &&\
     rm -rf /root/.cache/pip/* &&\
     rm -rf /root/.cache/pypoetry/*

# ---
FROM nvidia/cuda:12.3.2-base-ubuntu22.04 AS runner
ENV TZ=Asia/Seoul
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN  apt-get update &&\
        apt-get install --no-install-recommends -y python3.10 &&\
        rm -rf /var/lib/apt/lists/* 

WORKDIR /app
COPY --from=builder /usr/lib/x86_64-linux-gnu/ /usr/lib/x86_64-linux-gnu/
COPY --from=builder /app/.venv /app/.venv
COPY ./ai_api_server /app/ai_api_server
COPY ./frames /app/frames
COPY ./.env /app
COPY ./cloud-storage-credentials.json /app
COPY ./*_preset.png /app

EXPOSE 9001

CMD  ["/app/.venv/bin/python","ai_api_server/app.py"]