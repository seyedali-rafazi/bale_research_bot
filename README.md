# Bale Research Bot

A Telegram bot for academic research tools, now migrated to PostgreSQL and Redis for production-ready scalability.

## Features
- User management with VIP subscriptions
- Article search, PDF download, citations, summaries, translations, and BibTeX generation
- PostgreSQL-backed persistence
- Redis-backed session state and caching
- Designed for high concurrency and 10k+ users

## Setup
1. Copy `.env.example` to `.env` and fill values.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Start local services with Docker:
   ```bash
   docker-compose up -d
   ```
4. Run the bot:
   ```bash
   python main.py
   ```

## Environment Variables
- `BALE_TOKEN`: Telegram bot token
- `DATABASE_URL`: PostgreSQL URL
- `REDIS_URL`: Redis connection URL
- `ADMIN_ID`: Admin Telegram ID
- `PROVIDER_TOKEN`: Payment provider token
- `PAYMENT_VALUE`: Payment amount in IRR
- `USER_LIMIT_VALUE`: Free-user daily limit
- `VIP_LIMIT_VALUE`: VIP daily limit
- `SESSION_NAME`, `API_ID`, `API_HASH`: Telethon session variables

## Production Notes
- Use `docker-compose` to run Postgres and Redis in production-like environments.
- Tune `DB_MIN_POOL` and `DB_MAX_POOL` through env vars if needed.
- Redis persists user state and enables fast rate-limit checks.
