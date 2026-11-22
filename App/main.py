import threading
import uvicorn
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager
from kivy.core.window import Window
from ui.screens import TerminalScreen, AIScreen, MCPScreen
from api import app as fastapi_app

# Android'de klavye davranışını düzelt
Window.softinput_mode = "below_target"

def start_api_server():
    """FastAPI sunucusunu arka planda başlatır."""
    uvicorn.run(fastapi_app, host="127.0.0.1", port=8000, log_level="warning")

class AIForgeApp(App):
    def build(self):
        self.title = "AI Forge"
        
        # API'yi arka plan thread'inde başlat
        api_thread = threading.Thread(target=start_api_server, daemon=True)
        api_thread.start()
        
        # Ekran yöneticisini kur
        self.sm = ScreenManager()
        self.sm.add_widget(TerminalScreen(name='terminal'))
        self.sm.add_widget(AIScreen(name='ai'))
        self.sm.add_widget(MCPScreen(name='mcp'))
        
        return self.sm

    def switch_screen(self, screen_name):
        self.sm.current = screen_name

if __name__ == '__main__':
    AIForgeApp().run()
