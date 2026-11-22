from kivy.uix.screenmanager import Screen
from kivy.properties import ObjectProperty
import httpx
import asyncio
import threading

class TerminalScreen(Screen):
    code_input = ObjectProperty(None)
    output_label = ObjectProperty(None)

    def run_code(self):
        """API'ye kodu gönder, çıktıyı ekrana bas."""
        code = self.code_input.text
        
        def _request():
            try:
                res = httpx.post("http://127.0.0.1:8000/api/run", json={"code": code}, timeout=20)
                data = res.json()
                out = data.get("stdout", "") + data.get("stderr", "")
                self.output_label.text = out if out else "[No output]"
            except Exception as e:
                self.output_label.text = f"Error: {str(e)}"

        threading.Thread(target=_request, daemon=True).start()

    def heal_code(self):
        """AI Healer'ı çağır, kodu düzelt."""
        code = self.code_input.text
        
        def _request():
            try:
                res = httpx.post("http://127.0.0.1:8000/api/heal", json={"code": code}, timeout=60)
                data = res.json()
                self.code_input.text = data.get("fixed_code", code)
                self.output_label.text = f"Healed {data.get('errors_fixed', 0)} errors."
            except Exception as e:
                self.output_label.text = f"Heal Error: {str(e)}"

        threading.Thread(target=_request, daemon=True).start()


class AIScreen(Screen):
    task_input = ObjectProperty(None)
    plan_output = ObjectProperty(None)

    def run_agent(self):
        """Ajanı başlat."""
        task = self.task_input.text
        self.plan_output.text = "Agent thinking..."
        
        def _request():
            try:
                res = httpx.post("http://127.0.0.1:8000/api/agent", json={"task": task}, timeout=60)
                data = res.json()
                import json
                self.plan_output.text = json.dumps(data.get("steps", []), indent=2)
            except Exception as e:
                self.plan_output.text = f"Agent Error: {str(e)}"

        threading.Thread(target=_request, daemon=True).start()


class MCPScreen(Screen):
    pass
