import os
import shutil

def list_files(directory="."):
    try:
        files = os.listdir(directory)
        return "\n".join(files) if files else "📂 No files found."
    except Exception as e:
        return f"❌ Error: {str(e)}"

def create_folder(folder_name):
    try:
        os.makedirs(folder_name, exist_ok=True)
        return f"📂 Folder '{folder_name}' created."
    except Exception as e:
        return f"❌ Error: {str(e)}"

def move_file(source, destination):
    try:
        shutil.move(source, destination)
        return f"📂 Moved '{source}' → '{destination}'."
    except Exception as e:
        return f"❌ Error: {str(e)}"
