import subprocess
import os
from agent.healer import AIHealer

class TaskExecutor:
    def __init__(self, base_dir="./forge_workspace"):
        self.base_dir = base_dir
        self.healer = AIHealer()
        os.makedirs(self.base_dir, exist_ok=True)

    async def run_plan(self, steps: list):
        """Planner'dan gelen adımları sırayla çalıştırır."""
        results = []
        for step in steps:
            action = step.get("action")
            try:
                if action == "install":
                    res = self._install(step.get("package"))
                elif action == "write_file":
                    res = await self._write_file(step.get("filename"), step.get("content"))
                elif action == "execute":
                    res = self._execute(step.get("filename"))
                elif action == "fetch":
                    res = self._fetch(step.get("repo_url"))
                else:
                    res = {"status": "error", "message": f"Unknown action: {action}"}
            except Exception as e:
                res = {"status": "error", "message": str(e)}
            
            results.append({"step": step, "result": res})
        return results

    def _install(self, package: str):
        if not package:
            return {"status": "error", "message": "No package specified"}
        # Termux/Android ortamında user space'e kurar
        cmd = ["pip", "install", "--user", package]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        return {"status": "success" if proc.returncode == 0 else "error", "output": proc.stdout + proc.stderr}

    async def _write_file(self, filename: str, content: str):
        if not filename or not content:
            return {"status": "error", "message": "Missing filename or content"}
        
        # Python dosyasıysa AI Healer'dan geçir
        if filename.endswith(".py"):
            content, _ = await self.healer.fix(content)
            
        filepath = os.path.join(self.base_dir, filename)
        dir_name = os.path.dirname(filepath)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return {"status": "success", "path": filepath}

    def _execute(self, filename: str):
        filepath = os.path.join(self.base_dir, filename)
        if not os.path.exists(filepath):
            return {"status": "error", "message": f"File not found: {filepath}"}
            
        proc = subprocess.run(
            ["python", filepath], 
            capture_output=True, 
            text=True, 
            timeout=30,
            cwd=self.base_dir
        )
        return {
            "status": "success" if proc.returncode == 0 else "error",
            "stdout": proc.stdout,
            "stderr": proc.stderr
        }

    def _fetch(self, repo_url: str):
        if not repo_url:
            return {"status": "error", "message": "No repo URL"}
        repo_name = repo_url.rstrip('/').split('/')[-1].replace('.git', '')
        target_dir = os.path.join(self.base_dir, repo_name)
        if os.path.exists(target_dir):
            return {"status": "success", "message": "Already cloned"}
            
        proc = subprocess.run(["git", "clone", repo_url, target_dir], capture_output=True, text=True)
        return {"status": "success" if proc.returncode == 0 else "error", "output": proc.stderr}
