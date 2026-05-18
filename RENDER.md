# Render Deployment

This project is ready to deploy as a native Python web service on Render.

## Files

- `render.yaml`: Render Blueprint definition
- `requirements.txt`: Python dependencies
- `alembic/`: database migrations run at startup

## Deploy With Blueprint

1. Push the repository to GitHub.
2. In Render, choose `New +` -> `Blueprint`.
3. Select this repository.
4. Render will read `render.yaml` and create the web service.
5. Fill in the secret environment variables when prompted.

## Required Secret Environment Variables

- `DATABASE_URL`: Neon connection string using `postgresql+asyncpg://...`
- `OPENROUTER_API_KEY`
- `CLOUDINARY_CLOUD_NAME`
- `CLOUDINARY_API_KEY`
- `CLOUDINARY_API_SECRET`
- `TELEGRAM_BOT_TOKEN`

`SECRET_KEY` is generated automatically by Render from `render.yaml`.

## Default Non-Secret Environment Variables

These are already defined in `render.yaml`:

- `APP_ENV=production`
- `FREE_TRIAL_DOCUMENTS=3`
- `MAX_FILE_SIZE_MB=10`
- `MAX_PAGES_PER_DOC=50`
- `MAX_PDF_PAGES=50`
- `MAX_PPTX_SLIDES=50`
- `MAX_DOCX_WORDS=12000`
- `MAX_CHUNKS=20`
- `MAX_CHARS_PER_CHUNK=1800`
- `FACTS_PER_CHUNK=8`
- `MCQ_INTERVAL=4`
- `AI_TIMEOUT_SECONDS=60`
- `MAX_RETRIES=3`
- `OPENROUTER_MODEL=~moonshotai/kimi-latest`
- `OPENROUTER_FALLBACK_MODELS=google/gemma-4-31b-it:free`
- `OPENROUTER_MAX_429_WAIT_SECONDS=30`
- `OPENROUTER_SITE_URL=https://your-app.example.com`
- `OPENROUTER_APP_NAME=Microlearn AI`
- `TELEGRAM_INITDATA_MAX_AGE_SECONDS=300`

## Start Command

Render runs:

```bash
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

That means every deploy:

1. applies database migrations
2. starts the FastAPI app on Render's assigned port

## Neon Notes

Use the async connection string format expected by SQLAlchemy in this app:

```bash
postgresql+asyncpg://USER:PASSWORD@HOST/DBNAME?ssl=require
```

Neon usually requires SSL. Keep `ssl=require` in the connection string.

## Telegram Mini App Notes

The frontend must send `window.Telegram.WebApp.initData` to:

```text
POST /auth/telegram
```

The backend verifies the payload with `TELEGRAM_BOT_TOKEN` and returns a JWT.

## Health Check

`render.yaml` uses:

```text
/docs
```

Because the app keeps Swagger enabled and returns `200` there.

## After Deployment

Verify:

1. `GET /docs` loads
2. `POST /auth/telegram` returns a token for valid Telegram init data
3. document upload works
4. processing completes with OpenRouter
5. lessons can be fetched from the generated document
