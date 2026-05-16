# SwiftDrop Backend

This is the high-concurrency backend API for the SwiftDrop flash sale marketplace, built with FastAPI, PostgreSQL, and Redis.

## Architecture Highlights
- **FastAPI**: Provides robust async capabilities and automated OpenAPI docs.
- **Redis Lua Scripts**: Completely eliminates the "overselling" problem by processing purchase reservations atomically.
- **Background Tasks**: Offloads PostgreSQL DB writes to background workers, preventing the database from collapsing under the "Thundering Herd" traffic spike.
- **WebSockets**: Pushes real-time stock drops to the clients directly.

## Prerequisites
- Docker & Docker Compose
- Python 3.10+

## Local Setup Instructions

1. **Start the Infrastructure**
   ```bash
   docker-compose up -d
   ```
   *This starts PostgreSQL on port 5432 and Redis on port 6379.*

2. **Setup Python Environment**
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Environment Variables**
   Create a `.env` file in the `backend/` directory:
   ```env
   PROJECT_NAME="SwiftDrop API"
   REDIS_URL="redis://localhost:6379/0"
   DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/swiftdrop"
   SECRET_KEY="your-super-secret-jwt-key"
   ALGORITHM="HS256"
   ACCESS_TOKEN_EXPIRE_MINUTES=60
   ```

4. **Initialize Database**
   To create the tables, we use SQLAlchemy. Since we are using an async engine, we can run a simple startup script or Alembic migrations. (For this prototype, the tables must be created via SQLAlchemy `metadata.create_all()` or an Alembic init).

5. **Start the API Server**
   ```bash
   uvicorn app.main:app --reload
   ```
   *The API will be available at `http://localhost:8000`.*
   *Swagger Docs available at `http://localhost:8000/docs`.*

## Seeding an Admin Account
To create an admin account, connect to the PostgreSQL database and run:
```sql
INSERT INTO users (email, display_name, hashed_password, role, is_active) 
VALUES ('admin@swiftdrop.com', 'Super Admin', '$2b$12$K...', 'admin', true);
```
*(Note: Use a bcrypt hashed string for the password).*
