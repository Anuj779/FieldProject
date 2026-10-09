"""Prepare CDN assets without moving the fonts needed by the PDF renderer."""
from pathlib import Path
from shutil import copytree

if __name__ == '__main__':
    root = Path(__file__).resolve().parent
    copytree(root / 'static', root / 'public' / 'static', dirs_exist_ok=True)
