import os
import sys
import json
import subprocess
import threading
import asyncio
import shutil
from pathlib import Path
from datetime import datetime

# Kivy imports
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.properties import ObjectProperty, StringProperty

# Network
import httpx

# Android ayarları
try:
    from android.permissions import request_permissions, Permission
    request_permissions([
        Permission.INTERNET,
        Permission.WRITE_EXTERNAL_STORAGE,
        Permission.READ_EXTERNAL_STORAGE
    ])
except:
    pass

Window.softinput_mode = "below_target"

# ============================================
# ÇALIŞMA ALANI (APK İÇİNDE SANDBOX)
# ============================================
WORKSPACE = os.path.join(os.path.expanduser("~"), "forge_workspace")
os.makedirs(WORKSPACE, exist_ok=True)

# ============================================
# AI HEALER (Kod Tamircisi)
# ============================================
class AIHealer:
    def __init__(self):
        # Ollama veya yerel llama.cpp endpoint
        self.api_url = "http://127.0.0.1:11434/api/generate"
        self.model = "tinyllama"
    
    def fix(self, code: str, error_msg: str = "") -> str:
        """Senkron versiyon - thread içinde çalışacak"""
        import ast
        # Syntax check
        try:
            ast.parse(code)
            if not error_msg:
                return code  # Hata yok, döndür
        except SyntaxError as e:
            error_msg = str(e)
        
        prompt = f"""Fix this Python code. Error: {error_msg}
Code:
{code}
Return ONLY fixed code, no explanations, no markdown."""
        
        try:
            with httpx.Client(timeout=60.0) as client:
                res = client.post(self.api_url, json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                })
                if res.status_code == 200:
                    fixed = res.json().get("response", "").strip()
                    # Markdown temizle
                    if fixed.startswith("```python"):
                        fixed = fixed[9:]
                    if fixed.startswith("```"):
                        fixed = fixed[3:]
                    if fixed.endswith("```"):
                        fixed = fixed[:-3]
                    return fixed.strip()
        except Exception as e:
            return f"# AI Healer error: {e}\n{code}"
        return code

# ============================================
# AJAN (Görev Yönetici)
# ============================================
class Agent:
    def __init__(self):
        self.healer = AIHealer()
        self.api_url = "http://127.0.0.1:11434/api/generate"
        self.model = "tinyllama"
    
    def plan(self, task: str) -> list:
        """Görevi adımlara böler"""
        prompt = f"""Break this task into Python steps. Return JSON array only.
Task: {task}
Example: [{{"action":"install","pkg":"pygame"}},{{"action":"write","file":"game.py","content":"..."}},{{"action":"run","file":"game.py"}}]"""
        
        try:
            with httpx.Client(timeout=60.0) as client:
                res = client.post(self.api_url, json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                })
                if res.status_code == 200:
                    raw = res.json().get("response", "").strip()
                    start = raw.find('[')
                    end = raw.rfind(']') + 1
                    if start != -1 and end > start:
                        return json.loads(raw[start:end])
        except Exception as e:
            return [{"action": "error", "msg": str(e)}]
        return [{"action": "error", "msg": "Plan failed"}]
    
    def execute(self, steps: list, log_callback) -> list:
        """Adımları sırayla çalıştırır"""
        results = []
        for i, step in enumerate(steps):
            log_callback(f"\n[STEP {i+1}/{len(steps)}] {step.get('action')}")
            action = step.get("action")
            
            try:
                if action == "install":
                    pkg = step.get("pkg") or step.get("package")
                    log_callback(f"Installing {pkg}...")
                    proc = subprocess.run(
                        [sys.executable, "-m", "pip", "install", "--user", pkg],
                        capture_output=True, text=True, timeout=120
                    )
                    result = {"status": "ok" if proc.returncode == 0 else "err", "out": proc.stdout[-500:]}
                    
                elif action == "write":
                    filename = step.get("file") or step.get("filename")
                    content = step.get("content", "")
                    # Python dosyasıysa heal et
                    if filename.endswith(".py"):
                        content = self.healer.fix(content)
                    filepath = os.path.join(WORKSPACE, filename)
                    os.makedirs(os.path.dirname(filepath), exist_ok=True) if os.path.dirname(filepath) else None
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(content)
                    result = {"status": "ok", "path": filepath}
                    
                elif action == "run" or action == "execute":
                    filename = step.get("file") or step.get("filename")
                    filepath = os.path.join(WORKSPACE, filename)
                    proc = subprocess.run(
                        [sys.executable, filepath],
                        capture_output=True, text=True, timeout=30,
                        cwd=WORKSPACE
                    )
                    result = {"status": "ok" if proc.returncode == 0 else "err", 
                             "stdout": proc.stdout, "stderr": proc.stderr}
                             
                elif action == "clone":
                    url = step.get("url") or step.get("repo")
                    name = url.rstrip('/').split('/')[-1].replace('.git', '')
                    target = os.path.join(WORKSPACE, name)
                    proc = subprocess.run(["git", "clone", url, target], capture_output=True, text=True)
                    result = {"status": "ok" if proc.returncode == 0 else "err", "out": proc.stderr}
                    
                else:
                    result = {"status": "err", "msg": f"Unknown action: {action}"}
                    
            except Exception as e:
                result = {"status": "err", "msg": str(e)}
            
            results.append({"step": step, "result": result})
            log_callback(f"  → {result.get('status', 'unknown')}")
            
        return results

# ============================================
# MCP ARAÇLARI (GitHub + Dosya Sistemi)
# ============================================
class MCPTools:
    @staticmethod
    def github_search(query: str) -> str:
        try:
            url = f"https://api.github.com/search/repositories?q={query}&sort=stars&per_page=5"
            with httpx.Client(timeout=15) as client:
                res = client.get(url, headers={"Accept": "application/vnd.github.v3+json"})
                if res.status_code == 200:
                    items = res.json().get("items", [])
                    lines = []
                    for it in items:
                        lines.append(f"★ {it['stargazers_count']} | {it['full_name']}\n  {it['html_url']}")
                    return "\n\n".join(lines) if lines else "No results"
                return f"HTTP {res.status_code}"
        except Exception as e:
            return f"Error: {e}"
    
    @staticmethod
    def github_clone(url: str) -> str:
        name = url.rstrip('/').split('/')[-1].replace('.git', '')
        target = os.path.join(WORKSPACE, name)
        if os.path.exists(target):
            return f"Already exists: {target}"
        try:
            proc = subprocess.run(["git", "clone", url, target], capture_output=True, text=True, timeout=60)
            if proc.returncode == 0:
                return f"Cloned to {target}"
            return f"Clone failed: {proc.stderr}"
        except Exception as e:
            return f"Error: {e}"
    
    @staticmethod
    def list_files(path: str = "") -> str:
        target = os.path.join(WORKSPACE, path) if path else WORKSPACE
        if not os.path.exists(target):
            return "Path not found"
        try:
            items = os.listdir(target)
            lines = []
            for it in sorted(items):
                full = os.path.join(target, it)
                mark = "[DIR]" if os.path.isdir(full) else "[FILE]"
                lines.append(f"{mark} {it}")
            return "\n".join(lines) if lines else "(empty)"
        except Exception as e:
            return f"Error: {e}"
    
    @staticmethod
    def read_file(path: str) -> str:
        target = os.path.join(WORKSPACE, path)
        if not os.path.exists(target):
            return "File not found"
        try:
            with open(target, "r", encoding="utf-8") as f:
                content = f.read()
                if len(content) > 5000:
                    content = content[:5000] + f"\n\n... ({len(content)} chars total, truncated)"
                return content
        except Exception as e:
            return f"Error: {e}"
    
    @staticmethod
    def clean_workspace() -> str:
        removed = []
        for root, dirs, files in os.walk(WORKSPACE):
            for d in ["__pycache__", ".pytest_cache", "build", "dist"]:
                if d in dirs:
                    shutil.rmtree(os.path.join(root, d), ignore_errors=True)
                    removed.append(d)
                    dirs.remove(d)
            for f in files:
                if f.endswith((".pyc", ".pyo", ".log", ".tmp")):
                    try:
                        os.remove(os.path.join(root, f))
                        removed.append(f)
                    except:
                        pass
        return f"Removed {len(removed)} items"

# ============================================
# TERMINAL EKRANI
# ============================================
class TerminalScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.healer = AIHealer()
        layout = BoxLayout(orientation='vertical', padding=10, spacing=8)
        
        # Başlık
        header = Label(text='[ TERMINAL FORGE ]', font_size='22sp', bold=True,
                       color=(0, 1, 0, 1), size_hint_y=0.07)
        layout.add_widget(header)
        
        # Kod giriş
        self.code_input = TextInput(
            hint_text='# Write Python code here...\nprint("hello world")',
            size_hint_y=0.35,
            background_color=(0.08, 0.08, 0.08, 1),
            foreground_color=(0, 1, 0, 1),
            font_size='14sp'
        )
        layout.add_widget(self.code_input)
        
        # Butonlar
        btn_row = BoxLayout(size_hint_y=0.08, spacing=8)
        run_btn = Button(text='RUN', background_color=(0.2, 0.7, 0.2, 1), bold=True)
        run_btn.bind(on_press=self.run_code)
        heal_btn = Button(text='HEAL (AI)', background_color=(0.7, 0.2, 0.7, 1), bold=True)
        heal_btn.bind(on_press=self.heal_code)
        clear_btn = Button(text='CLEAR', background_color=(0.5, 0.5, 0.5, 1), bold=True)
        clear_btn.bind(on_press=lambda x: setattr(self.output, 'text', ''))
        btn_row.add_widget(run_btn)
        btn_row.add_widget(heal_btn)
        btn_row.add_widget(clear_btn)
        layout.add_widget(btn_row)
        
        # Çıktı
        scroll = ScrollView(size_hint_y=0.42)
        self.output = Label(
            text='> Ready. Type code and press RUN.',
            size_hint_y=None,
            text_size=(None, None),
            halign='left', valign='top',
            color=(0.9, 0.9, 0.9, 1),
            font_size='13sp'
        )
        self.output.bind(texture_size=self.output.setter('size'))
        scroll.add_widget(self.output)
        layout.add_widget(scroll)
        
        self.add_widget(layout)
    
    def log(self, text):
        Clock.schedule_once(lambda dt: self._append(text), 0)
    
    def _append(self, text):
        self.output.text += "\n" + text
    
    def run_code(self, instance):
        code = self.code_input.text
        self.log(f"\n>>> Running...\n{'─'*40}")
        
        def _run():
            try:
                proc = subprocess.run(
                    [sys.executable, "-c", code],
                    capture_output=True, text=True, timeout=15,
                    cwd=WORKSPACE
                )
                if proc.stdout:
                    self.log(proc.stdout)
                if proc.stderr:
                    self.log(f"[STDERR] {proc.stderr}")
                self.log(f"\n[exit code: {proc.returncode}]")
            except subprocess.TimeoutExpired:
                self.log("[TIMEOUT] 15s limit exceeded")
            except Exception as e:
                self.log(f"[ERROR] {e}")
        
        threading.Thread(target=_run, daemon=True).start()
    
    def heal_code(self, instance):
        code = self.code_input.text
        self.log("\n[AI] Healing code...")
        
        def _heal():
            fixed = self.healer.fix(code)
            Clock.schedule_once(lambda dt: setattr(self.code_input, 'text', fixed), 0)
            self.log("[AI] Done. Code updated.")
        
        threading.Thread(target=_heal, daemon=True).start()

# ============================================
# AJAN EKRANI
# ============================================
class AgentScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.agent = Agent()
        layout = BoxLayout(orientation='vertical', padding=10, spacing=8)
        
        header = Label(text='[ AGENT MODE ]', font_size='22sp', bold=True,
                       color=(1, 0.6, 0, 1), size_hint_y=0.07)
        layout.add_widget(header)
        
        self.task_input = TextInput(
            hint_text='e.g., "make a snake game with pygame"',
            size_hint_y=0.12,
            multiline=False,
            background_color=(0.08, 0.08, 0.08, 1),
            foreground_color=(1, 1, 1, 1),
            font_size='14sp'
        )
        layout.add_widget(self.task_input)
        
        deploy_btn = Button(
            text='DEPLOY AGENT',
            size_hint_y=0.08,
            background_color=(0.9, 0.5, 0.1, 1),
            bold=True
        )
        deploy_btn.bind(on_press=self.deploy)
        layout.add_widget(deploy_btn)
        
        scroll = ScrollView(size_hint_y=0.65)
        self.output = Label(
            text='> Agent idle. Describe a task and press DEPLOY.',
            size_hint_y=None,
            text_size=(None, None),
            halign='left', valign='top',
            color=(0.9, 0.9, 0.9, 1),
            font_size='13sp'
        )
        self.output.bind(texture_size=self.output.setter('size'))
        scroll.add_widget(self.output)
        layout.add_widget(scroll)
        
        self.add_widget(layout)
    
    def log(self, text):
        Clock.schedule_once(lambda dt: self._append(text), 0)
    
    def _append(self, text):
        self.output.text += "\n" + text
    
    def deploy(self, instance):
        task = self.task_input.text
        if not task.strip():
            self.log("[!] Empty task")
            return
        
        self.log(f"\n[AGENT] Planning: {task}")
        
        def _deploy():
            # Plan
            self.log("[AGENT] Generating plan...")
            plan = self.agent.plan(task)
            self.log(f"[AGENT] Plan has {len(plan)} steps:")
            for i, s in enumerate(plan):
                self.log(f"  {i+1}. {s}")
            
            # Execute
            self.log("\n[AGENT] Executing...")
            results = self.agent.execute(plan, self.log)
            
            # Summary
            ok = sum(1 for r in results if r['result'].get('status') == 'ok')
            self.log(f"\n[AGENT] Done. {ok}/{len(results)} steps succeeded.")
        
        threading.Thread(target=_deploy, daemon=True).start()

# ============================================
# MCP EKRANI
# ============================================
class MCPScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.mcp = MCPTools()
        layout = BoxLayout(orientation='vertical', padding=10, spacing=8)
        
        header = Label(text='[ MCP BRIDGE ]', font_size='22sp', bold=True,
                       color=(0, 0.9, 0.9, 1), size_hint_y=0.07)
        layout.add_widget(header)
        
        # Arama
        search_row = BoxLayout(size_hint_y=0.08, spacing=8)
        self.search_input = TextInput(
            hint_text='GitHub search query...',
            multiline=False,
            background_color=(0.08, 0.08, 0.08, 1),
            foreground_color=(1, 1, 1, 1)
        )
        search_btn = Button(text='SEARCH', background_color=(0.2, 0.5, 0.8, 1), bold=True)
        search_btn.bind(on_press=self.search_github)
        search_row.add_widget(self.search_input)
        search_row.add_widget(search_btn)
        layout.add_widget(search_row)
        
        # Clone
        clone_row = BoxLayout(size_hint_y=0.08, spacing=8)
        self.clone_input = TextInput(
            hint_text='https://github.com/user/repo',
            multiline=False,
            background_color=(0.08, 0.08, 0.08, 1),
            foreground_color=(1, 1, 1, 1)
        )
        clone_btn = Button(text='CLONE', background_color=(0.2, 0.7, 0.4, 1), bold=True)
        clone_btn.bind(on_press=self.clone_github)
        clone_row.add_widget(self.clone_input)
        clone_row.add_widget(clone_btn)
        layout.add_widget(clone_row)
        
        # Araçlar
        tool_row = BoxLayout(size_hint_y=0.08, spacing=8)
        list_btn = Button(text='LIST FILES', background_color=(0.5, 0.5, 0.5, 1), bold=True)
        list_btn.bind(on_press=lambda x: self.show_files())
        clean_btn = Button(text='CLEAN', background_color=(0.7, 0.3, 0.3, 1), bold=True)
        clean_btn.bind(on_press=lambda x: self.do_clean())
        tool_row.add_widget(list_btn)
        tool_row.add_widget(clean_btn)
        layout.add_widget(tool_row)
        
        # Çıktı
        scroll = ScrollView(size_hint_y=0.61)
        self.output = Label(
            text='> MCP Bridge active.\nSearch GitHub, clone repos, manage files.',
            size_hint_y=None,
            text_size=(None, None),
            halign='left', valign='top',
            color=(0.9, 0.9, 0.9, 1),
            font_size='13sp'
        )
        self.output.bind(texture_size=self.output.setter('size'))
        scroll.add_widget(self.output)
        layout.add_widget(scroll)
        
        self.add_widget(layout)
    
    def log(self, text):
        Clock.schedule_once(lambda dt: self._append(text), 0)
    
    def _append(self, text):
        self.output.text += "\n" + text
    
    def search_github(self, instance):
        q = self.search_input.text.strip()
        if not q:
            return
        self.log(f"\n[MCP] Searching: {q}")
        def _s():
            res = self.mcp.github_search(q)
            self.log(res)
        threading.Thread(target=_s, daemon=True).start()
    
    def clone_github(self, instance):
        url = self.clone_input.text.strip()
        if not url:
            return
        self.log(f"\n[MCP] Cloning: {url}")
                def _c():
            res = self.mcp.github_clone(url)
            self.log(res)
        threading.Thread(target=_c, daemon=True).start()
    
    def show_files(self):
        self.log("\n[MCP] Workspace contents:")
        self.log(self.mcp.list_files())
    
    def do_clean(self):
        self.log("\n[MCP] " + self.mcp.clean_workspace())

# ============================================
# ANA UYGULAMA
# ============================================
class AIForgeApp(App):
    def build(self):
        self.title = "AI Forge"
        
        # Ana layout
        root = BoxLayout(orientation='vertical')
        
        # Ekran yöneticisi
        self.sm = ScreenManager()
        self.sm.add_widget(TerminalScreen(name='terminal'))
        self.sm.add_widget(AgentScreen(name='agent'))
        self.sm.current = name
        self.sm.add_widget(MCPScreen(name='mcp'))

        root.add_widget(self.sm)
    
if __name__ == '__main__':
        
                        color=(0.9, 0.9, 0.9, 1))
    def switch(self, name):
            nav.add_widget(btn)
            btn = Button(text=label, bold=True,
                        background_color=(0.15, 0.15, 0.15, 1),
        
        nav = BoxLayout(size_hint_y=0.08, spacing=2)
        root.add_widget(nav)
    AIForgeApp().run()
