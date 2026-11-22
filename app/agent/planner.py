import httpx

class AgentPlanner:
    def __init__(self, api_url="http://127.0.0.1:11434/api/generate"):
        self.api_url = api_url
        self.model = "llama3"

    async def decompose(self, task: str):
        """Kullanıcı görevini adım adım plana böler."""
        prompt = f"""
        You are an AI agent orchestrator.
        Break down this task into executable Python steps.
        Task: {task}
        
        Return a JSON array of steps. Example:
        [
            {{"action": "install", "package": "pygame"}},
            {{"action": "write_file", "filename": "game.py", "content": "..."}},
            {{"action": "execute", "filename": "game.py"}}
        ]
        Return ONLY valid JSON.
        """

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                self.api_url,
                json={"model": self.model, "prompt": prompt, "stream": False}
            )
            
        if response.status_code == 200:
            raw = response.json().get("response", "").strip()
            # JSON'u parse etmeye çalış
            import json
            try:
                # LLM bazen etrafına metin ekler, {} veya [] bul
                start = raw.find('[')
                end = raw.rfind(']') + 1
                if start != -1 and end != 0:
                    return json.loads(raw[start:end])
            except json.JSONDecodeError:
                pass
                
        return [{"action": "error", "message": "Plan generation failed"}]
