# Crypto Escrow Freelance Platform

FastAPI website + Telegram onboarding bot + PostgreSQL, ready for Railway.

## Railway deploy
1. Create Railway project.
2. Add PostgreSQL plugin.
3. Add variables from `.env.example`.
4. Use the PostgreSQL `DATABASE_URL`; make sure it starts with `postgresql+asyncpg://`.
5. Deploy with start command:
   `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

## Local run
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```
