import subprocess
import httpx
import os

WORKSPACE = "./forge_workspace"
os.makedirs(WORKSPACE, exist_ok=True)

async def github_clone(url: str):
    repo_name = url.rstrip('/').split('/')[-1].replace('.git', '')
    target = os.path.join(WORKSPACE, repo_name)
    if os.path.exists(target):
        return f"Already exists at {target}"
    proc = subprocess.run(["git", "clone", url, target], capture_output=True, text=True)
    if proc.returncode == 0:
        return f"Cloned to {target}"
    return f"Clone failed: {proc.stderr}"

async def github_search(query: str):
    url = f"https://api.github.com/search/repositories?q={query}&sort=stars&order=desc"
    async with httpx.AsyncClient() as client:
        res = await client.get(url, headers={"Accept": "application/vnd.github.v3+json"})
        if res.status_code == 200:
            data = res.json()
            items = data.get("items", [])[:5]
            results = [f"{item['full_name']} ({item['stargazers_count']} stars): {item['html_url']}" for item in items]
            return "\n".join(results) if results else "No results found"
        return f"Search failed: {res.status_code}"
