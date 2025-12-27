# learnLang Server

The backend server to support expo go app [learnLang](https://github.com/ajeecai/learnLang).

## Configuration

Before running the project, you must set up the environment variables:

1. Copy the example configuration: `cp .env_example .env`
2. Edit `.env` with your actual values (API keys, passwords, paths, etc.).

## script

`scripts/download_models.py`： Download TTS model or STT model from huggingface (or defined by ModelManager). Docker will mount them inside

`scripts/generate_sql.py`: use to build databse in Makefile

## how to build

`make download && make build`

Use `make test` to test the API enpoints

## how to run

`docker compose up -d`
For development, `docker compose up --watch`
