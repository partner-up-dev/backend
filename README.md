# PartnerUp-BackendMain

## Tech Stacks

This branch maintains a version based on FastAPI + SQLModel.

## Development

### Infrastructure

- PostgreSQL
- Redis
- PostgREST: optional, frontend requires it.

You can config infrastructures for local development with given `docker-compose.yml` by: `docker compose up -d`

Before that, you should config `.env` properly (see `.env.example` for example)

## Deployment

### Setting / Configuration

1. Generate key from [Age](https://github.com/FiloSottile/age) use `age-keygen -o age.agekey`.

