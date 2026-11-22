from fastapi import FastAPI
from pydantic import BaseModel
import subprocess
import asyncio
from agent.healer import AIHealer
from agent.planner import AgentPlanner

app = FastAPI()
healer = AIHealer()
planner = AgentPlanner()

class CodeRequest(BaseModel):
    code: str

class TaskRequest(BaseModel):
    task: str

@app.post("/api/heal")
async def heal_code(req: CodeRequest):
    """Hatalı kodu AI ile düzelt."""
    fixed_code, errors = await healer.fix(req.code)
    return {"fixed_code": fixed_code, "errors_fixed": errors}

@app.post("/api/run")
async def run_code(req: CodeRequest):
    """Python kodunu güvenli bir şekilde çalıştır."""
    try:
        result = subprocess.run(
            ["python", "-c", req.code],
            capture_output=True, text=True, timeout=15
        )
        return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}
    except subprocess.TimeoutExpired:
        return {"error": "Execution timed out (15s limit)"}

@app.post("/api/agent")
async def run_agent(req: TaskRequest):
    """Ajan modu: Görevi planla ve çalıştır."""
    plan = await planner.decompose(req.task)
    return {"status": "planned", "steps": plan}

@app.get("/api/health")
async def health_check():
    return {"status": "forge_online", "api": "fastapi", "ai": "ready"}
