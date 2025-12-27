# Makefile for managing Docker Compose services
include .env
export

# Variables
COMPOSE = docker compose


# Default target: show help
.PHONY: all
all: help

# Show help message
.PHONY: help
help:
	@echo "Usage:"
	@echo "  make <target>"
	@echo ""
	@echo "Targets:"
	@echo "  build    # Build services for the host architecture"
	@echo "  start    # Run services"
	@echo "  stop     # Stop and remove services"
	@echo "  ps       # Show container status"
	@echo "  test     # Test health checks and certificate update"
	@echo "  logs     # View logs for all services"
	@echo "  clean    # Clean up containers, images, and volumes"
	@echo "  clean_db # Clean up db volumes only"
	@echo "  restart  # Rebuild and restart services"
	@echo "  download # download llm model"
	@echo "  watch    # Run services with hot reload (Docker Compose Watch)"

# Build and start services in detached mode
build: stop
	@python3 scripts/generate_sql.py "$$MYSQL_DATABASE" "$$TEST_NAME" "$$TEST_PASSWORD" "$$MYSQL_PASSWORD"
	@COMPOSE_BAKE=true $(COMPOSE) build

# Run services
.PHONY: start 
start: 
	$(COMPOSE) up -d

# Run services with file watching enabled
.PHONY: watch
watch:
	$(COMPOSE) up --watch

# Test API endpoints
.PHONY: test
test:
	@if [ ! -f .env ]; then echo "Error: .env file not found"; exit 1; fi
	@DOMAIN_NAME=$$(grep '^DOMAIN_NAME=' .env | cut -d '=' -f 2); \
	USERNAME=$$(grep '^TEST_NAME=' .env | cut -d '=' -f 2); \
	PASSWORD=$$(grep '^TEST_PASSWORD=' .env | cut -d '=' -f 2 | python3 -c "import urllib.parse, sys; print(urllib.parse.quote(sys.stdin.read().strip()))"); \
	echo ""; \
	echo "====== API Testing Commands ======"; \
	echo ""; \
	echo "1. Login and get token:"; \
	echo "  export TOKEN=\$$(curl -s -k -X POST https://$$DOMAIN_NAME/login \\"; \
	echo "    -H \"Content-Type: application/x-www-form-urlencoded\" \\"; \
	echo "    -d \"username=$$USERNAME&password=$$PASSWORD\" \\"; \
	echo "    | tee /dev/tty | jq -r '.access_token')"; \
	echo ""; \
	echo "2. Transcribe audio:"; \
	echo "  curl -k -X POST https://$$DOMAIN_NAME/transcribe -H \"Authorization: Bearer \$$TOKEN\" -F \"file=@/path-to-file/test-audio.wav\""; \
	echo ""; \
	echo "3. Synthesize speech:"; \
	echo "  curl -k -X POST https://$$DOMAIN_NAME/synthesize -H \"Authorization: Bearer \$$TOKEN\" -F \"text=Hello, this is a test.\" -o ~/output.audio"; \
	echo ""; \
	echo "4. run batch test "; \
	echo "   ./parellel_test.sh https://127.0.0.1:9443 s|t parellel_num"; \
	echo "5. run wss test "; \
	echo "  python3 ./test_websocket_VAD.py 127.0.0.1:9443 ssl"; \
	echo ""    or websocat -k  "wss://127.0.0.1:9443/ws?token=\$$TOKEN"; \
	echo ""; \
	echo "==================================="

# Stop and remove services
.PHONY: stop 
stop:
	$(COMPOSE) down

# View logs for all services
.PHONY: logs
logs:
	$(COMPOSE) logs -f

# Show container status
.PHONY: ps
ps:
	docker ps
	docker volume ls

# Clean up containers, images, and volumes
.PHONY: clean
clean:
	@echo "WARNING: This will delete all containers, images, and volumes defined in docker-compose.yml."
	@echo "This includes the 'mysql-data', 'redis-data' volume, which will erase all database data."
	@echo "Proceed? [y/N] (default: N)"
	@read -r response; \
	if [ "$$response" = "y" ] || [ "$$response" = "Y" ]; then \
		$(COMPOSE) down -v --rmi all --remove-orphans; \
		docker system prune -f ; \
		echo "Cleanup completed."; \
	else \
		echo "Cleanup aborted."; \
	fi

# clean db only
.PHONY: clean_db
clean_db:
	@echo "WARNING!!! This clean the 'mysql-data', 'redis-data' data volume"
	@echo "Proceed? [y/N] (default: N)"
	@read -r response; \
        if [ "$$response" = "y" ] || [ "$$response" = "Y" ]; then \
            $(COMPOSE) down; \
			docker volume rm learnlang_server_docker_mysql-data; \
			docker volume rm learnlang_server_docker_redis-data; \
		echo "Cleanup completed."; \
        else \
            echo "Cleanup aborted."; \
        fi

# Rebuild and restart services
.PHONY: restart
restart: stop start

# download #
.PHONY: download
download:
	python3 download_models.py
