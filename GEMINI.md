# Project Context & Gemini Instructions

## Architecture & Environment
- **Framework:** Django v6
- **Production Environment:** Docker Swarm Stack spanning 2 AWS EC2 `t3.micro` instances:
  - Node 1: Traefik + Web Application
  - Node 2: PgBouncer + PostgreSQL v18
- **Storage:** Static and Media files are hosted on Amazon S3.
- **Resource Constraints:** Production instances have very limited resources (t3.micro). All development and architectural choices must prioritize low memory usage and efficient execution.
- **Development Environment:** `uv` for dependency management and Python environments, combined with Docker.

## Testing & Validation
- **Test Command:** Use `uv run pytest --ds=burcu_photo.test_settings` or `uv run python manage.py test --settings=burcu_photo.test_settings`.
- **Test Settings:** Always use `burcu_photo.test_settings` for testing to avoid production database and cache dependencies.
- **Coverage:** Any new code or modifications MUST be included in the test coverage. 
- **Validation:** When development is complete, the full test suite must be run to verify structural and behavioral integrity. Tests run locally on powerful machines, so test performance is less critical than production performance.

## Workflows & Version Control
- **Commits:** Upon completing a task, summarize the changes and propose a commit message. Do NOT create a Pull Request or commit the changes automatically.

## AI Agent Guidelines
- Be mindful of the `AppRegistryNotReady` and `ImproperlyConfigured` Django errors. Ensure that `DJANGO_SETTINGS_MODULE` is correctly pointing to the test settings.
- Do not run tests against the default `burcu_photo.settings` as it expects PgBouncer and Postgres which may not be available locally without Docker.
- Always report findings and ask for user direction before applying large fixes.
