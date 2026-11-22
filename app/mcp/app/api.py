 (EKLENMESİ GEREKEN YENİ ENDPOINTLER)
# Mevcut api.py dosyanın içine bunları ekle:

from agent.executor import TaskExecutor
from agent.cleaner import FileCleaner

executor = TaskExecutor()
cleaner = FileCleaner()

@app.post("/api/execute_plan")
async def execute_plan(steps: list[dict]):
    """Planner'dan gelen planı çalıştırır."""
    results = await executor.run_plan(steps)
    return {"status": "executed", "results": results}

@app.post("/api/clean")
async def clean_workspace():
    """Workspace'deki gereksiz dosyaları temizler."""
    removed = cleaner.clean()
    return {"status": "cleaned", "removed_count": len(removed), "items": removed}
