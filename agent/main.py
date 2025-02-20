from fastapi import FastAPI
from .routes import router as agent_router

# Create FastAPI instance
app = FastAPI(
    title="Orianna Agent",
    version="0.1.0",
    description="A personal home assistant/agent",
)

# Include your routes from routes.py
app.include_router(agent_router)

# Example root path (health check)
@app.get("/")
def read_root():
    return {"message": "Welcome to Orianna Agent API"}