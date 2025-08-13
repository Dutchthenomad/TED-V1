# Docker Development Environment for TED-V1

## Quick Start

1. **Build and start all services:**
   ```bash
   make build
   make up
   ```

2. **Access the application:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - MongoDB: mongodb://localhost:27017

## Available Commands

```bash
make build    # Build all Docker images
make up       # Start all services
make down     # Stop all services
make restart  # Restart all services
make logs     # View logs from all services
make shell    # Open shell in backend container
make clean    # Remove containers and volumes
make test     # Run tests
```

## Manual Docker Commands

### Start with docker-compose:
```bash
docker-compose up -d
```

### Start with development configuration:
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### View logs:
```bash
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f mongodb
```

### Rebuild after code changes:
```bash
docker-compose build backend
docker-compose up -d backend
```

## Features

- **Hot Reload**: Both frontend and backend automatically reload on code changes
- **MongoDB**: Persistent data storage with volume mounting
- **Environment Variables**: Properly configured for development
- **Network Isolation**: Services communicate through Docker network
- **Volume Mounting**: Code changes reflect immediately without rebuilding

## Troubleshooting

### Port already in use:
```bash
# Check what's using the port
lsof -i :3000
lsof -i :8000

# Kill the process or change ports in docker-compose.yml
```

### MongoDB connection issues:
```bash
# Check MongoDB logs
docker-compose logs mongodb

# Connect to MongoDB directly
docker-compose exec mongodb mongosh -u admin -p password123
```

### Frontend not connecting to backend:
- Check that `REACT_APP_BACKEND_URL` is set correctly
- Verify backend is running: `curl http://localhost:8000/health`

### Clean restart:
```bash
make clean
make build
make up
```

## Environment Variables

The following are configured in `docker-compose.yml`:

### Backend:
- `MONGO_URL`: MongoDB connection string
- `RUGS_BACKEND_URL`: External API endpoint
- `LOG_LEVEL`: Logging verbosity (DEBUG/INFO/WARNING/ERROR)

### Frontend:
- `REACT_APP_BACKEND_URL`: Backend API URL
- `REACT_APP_WS_URL`: WebSocket URL

## Development Workflow

1. Make code changes in your editor
2. Changes auto-reload in the containers
3. Check logs if something breaks: `make logs`
4. Access shell for debugging: `make shell`
5. Run tests: `make test`

## Notes

- MongoDB data persists in Docker volume `mongodb_data`
- Node modules and Python cache are excluded from volume mounts for performance
- WSL2 users: File watching works with `WATCHPACK_POLLING=true`