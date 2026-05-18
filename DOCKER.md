# Docker Setup

This project now expects all managed services to be external.

The provided `docker-compose.yml` starts only the FastAPI app. The app connects to:

- Neon PostgreSQL
- Groq API
- Cloudinary
- Telegram Bot API credentials

## 1. Create the Docker env file

```bash
cp .env.example .env
```

Update `.env`:

- Set `APP_PORT` if you want to avoid conflicts with another running stack
- Set `SECRET_KEY` to a value with at least 32 characters
- Set `DATABASE_URL` to your external PostgreSQL instance
- Set your Groq credentials
- Set your Cloudinary credentials
- Set your Telegram bot token

Important:

- From inside the container, `localhost` means the container itself
- If PostgreSQL is running on your host machine, Linux users usually need to replace `host.docker.internal` with your host IP
- If PostgreSQL is running on another machine, use that hostname or IP directly

## 2. Start the stack

```bash
docker compose up --build -d
```

## 3. Pull the Ollama model

No local AI model or object storage container is needed anymore.

## 4. Access the services

- API: `http://localhost:${APP_PORT}`
- Swagger UI: `http://localhost:${APP_PORT}/docs`

Example alternate host ports:

```bash
APP_PORT=8010
```

## Notes

- The app container runs `alembic upgrade head` on startup before launching Uvicorn
- The app tolerates Groq or Cloudinary startup failures and logs warnings, so the API can still start before those services are usable
