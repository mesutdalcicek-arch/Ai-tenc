
import threading
import uvicorn
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager
from ui.screens import TerminalScreen, AIScreen, MCPScreen
from api import app as fastapi_app

def start_api_server():
    """FastAPI sunucusunu arka planda başlatır."""
    uvicorn.run(fastapi_app, host="127.0.0.1", port=8000, log_level="warning")

class AIForgeApp(App):
    def build(self):
        # API'yi arka plan thread'inde başlat
        api_thread = threading.Thread(target=start_api_server, daemon=True)
        api_thread.start()
        
        # Ekran yöneticisini kur
        sm = ScreenManager()
        sm.add_widget(TerminalScreen(name='terminal'))
        sm.add_widget(AIScreen(name='ai'))
        sm.add_widget(MCPScreen(name='mcp'))
        return sm

if __name__ == '__main__':
    AIForgeApp().run()
