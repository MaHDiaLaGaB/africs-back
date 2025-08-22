DB_HOST ?= localhost
DB_PORT ?= 5432
DB_SUPERUSER ?= $(shell whoami)
DB_SUPERPASS ?= postgres
DB_NAME ?= wasata_db

export PGPASSWORD := $(DB_SUPERPASS)

.PHONY: setup-db
setup-db:
	@echo "🛠  Creating roles and database..."
	psql -h $(DB_HOST) -p $(DB_PORT) -U $(DB_SUPERUSER) -d postgres -f app/scripts/init_db.sql 
	@echo "🔑 Setting privileges on $(DB_NAME)..."
	psql -h $(DB_HOST) -p $(DB_PORT) -U $(DB_SUPERUSER) -d $(DB_NAME) -f app/scripts/init_privileges.sql
	@echo "✅ Database and roles are ready."

.PHONY: clear-db
clear-db:
	@echo "🧹 Clearing all data from $(DB_NAME)..."
	psql -h $(DB_HOST) -p $(DB_PORT) -U $(DB_SUPERUSER) -d $(DB_NAME) -f app/scripts/clear.sql
	@echo "✅ All data cleared."

.PHONY: delete-data
delete-data:
	@echo "🧹 Clearing all data from $(DB_NAME)..."
	psql -h $(DB_HOST) -p $(DB_PORT) -U $(DB_SUPERUSER) -d $(DB_NAME) -f app/scripts/delete_data.sql
	@echo "✅ All data cleared."

.PHONY: migrate
migrate:
	@echo "📦 Running Alembic migrations..."
	poetry run alembic upgrade head

.PHONY: makemigrations
makemigrations:
	@read -p "Enter migration message: " msg; \
	echo "📝 Generating migration with message: $$msg"; \
	poetry run alembic revision --autogenerate -m "$$msg"

.PHONY: run
run:
	@echo "🚀 Starting FastAPI server..."
	poetry run uvicorn api.index:app --host=0.0.0.0 --port=8000 --reload --timeout-graceful-shutdown=5

.PHONY: create-admin
create-admin:
	PYTHONPATH=. poetry run python app/create_admin.py admin "System Admin" admin123
