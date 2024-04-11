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
    # && mv /root/.poetry $POETRY_PATH \
    && poetry --version \
    # && python -m venv $VENV_PATH \
    # && poetry config settings.virtualenvs.create false \
    && rm -rf /var/lib/apt/lists/*

ADD pyproject.toml poetry.lock /app/
RUN poetry config virtualenvs.in-project true &&\
     poetry config virtualenvs.options.always-copy true &&\
     poetry install  --no-interaction --no-ansi -vvv &&\
     rm -rf /root/.cache/pip/* &&\
     rm -rf /root/.cache/pypoetry/*

# ---

ENV TZ=Asia/Seoul
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

ADD . /app

RUN useradd -m user1 && chown -R user1:user1 /app
USER user1

EXPOSE 9001

CMD  ["/app/.venv/bin/python","ai_api_server/app.py"]