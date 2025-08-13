# Makefile for TED-V1 Development

.PHONY: help build up down restart logs shell clean test

help:
	@echo "Available commands:"
	@echo "  make build    - Build all Docker images"
	@echo "  make up       - Start all services"
	@echo "  make down     - Stop all services"
	@echo "  make restart  - Restart all services"
	@echo "  make logs     - View logs from all services"
	@echo "  make shell    - Open shell in backend container"
	@echo "  make clean    - Remove containers and volumes"
	@echo "  make test     - Run tests"

build:
	docker-compose build

up:
	docker-compose up -d
	@echo "Services starting..."
	@echo "Frontend: http://localhost:3000"
	@echo "Backend:  http://localhost:8000"
	@echo "MongoDB:  mongodb://localhost:27017"

down:
	docker-compose down

restart:
	docker-compose restart

logs:
	docker-compose logs -f

shell:
	docker-compose exec backend /bin/bash

clean:
	docker-compose down -v
	docker system prune -f

test:
	docker-compose exec backend python -m pytest