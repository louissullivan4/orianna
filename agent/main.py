from fastapi import FastAPI
from agent.routes import router as agent_router

app = FastAPI(
    title="Orianna Agent",
    version="0.1.0",
    description="A personal home assistant/agent"
)

app.include_router(agent_router)

@app.get("/")
def read_root():
    return {"message": "Welcome to Orianna Agent API"}
