import os
import shutil

WORKSPACE = "./forge_workspace"

async def list_dir(path: str):
    target = os.path.join(WORKSPACE, path) if not os.path.isabs(path) else path
    if not os.path.exists(target):
        return "Path does not exist"
    items = os.listdir(target)
    return "\n".join(items) if items else "Empty directory"

async def read_file(path: str):
    target = os.path.join(WORKSPACE, path) if not os.path.isabs(path) else path
    if not os.path.exists(target):
        return "File does not exist"
    try:
        with open(target, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"

async def delete_file(path: str):
    target = os.path.join(WORKSPACE, path) if not os.path.isabs(path) else path
    if not os.path.exists(target):
        return "Path does not exist"
    try:
        if os.path.isdir(target):
            shutil.rmtree(target)
        else:
            os.remove(target)
        return f"Deleted {target}"
    except Exception as e:
        return f"Error deleting: {e}"
