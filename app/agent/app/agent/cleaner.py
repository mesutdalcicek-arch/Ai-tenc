import os
import shutil

class FileCleaner:
    def __init__(self, base_dir="./forge_workspace"):
        self.base_dir = base_dir
        self.targets = ["__pycache__", ".pytest_cache", ".mypy_cache", ".venv", "build", "dist"]
        self.extensions = [".pyc", ".pyo", ".pyd", ".log", ".tmp"]

    def clean(self):
        """Gereksiz önbellek ve derleme dosyalarını siler."""
        removed = []
        for root, dirs, files in os.walk(self.base_dir):
            # Hedef dizinleri sil
            for target in self.targets:
                if target in dirs:
                    target_path = os.path.join(root, target)
                    shutil.rmtree(target_path, ignore_errors=True)
                    removed.append(f"DIR: {target_path}")
                    dirs.remove(target) # İçi boşaltıldı,.walk devam etmesin

            # Hedef uzantılı dosyaları sil
            for file in files:
                if any(file.endswith(ext) for ext in self.extensions):
                    file_path = os.path.join(root, file)
                    try:
                        os.remove(file_path)
                        removed.append(f"FILE: {file_path}")
                    except OSError:
                        pass
        return removed
