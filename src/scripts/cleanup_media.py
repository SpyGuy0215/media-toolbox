import os
import time
from pathlib import Path
import cronitor
from dotenv import load_dotenv

MEDIA_DIR = Path(__file__).parent.parent.parent / 'media'
AGE_LIMIT_SECONDS = 12 * 60 * 60  # 12 hours

load_dotenv()
cronitor.api_key = os.getenv('CRONITOR_API_KEY')  # Set your Cronitor API key in environment variables

@cronitor.job('jPqGYP')
def cleanup_media_folder():
    now = time.time()
    for folder in MEDIA_DIR.iterdir():
        if folder.is_dir():
            for file in folder.iterdir():
                if file.is_file():
                    mtime = file.stat().st_mtime
                    if now - mtime > AGE_LIMIT_SECONDS:
                        try:
                            file.unlink()
                        except Exception as e:
                            print(f"Failed to delete {file}: {e}")
            # Remove folder if empty
            if not any(folder.iterdir()):
                try:
                    folder.rmdir()
                except Exception as e:
                    print(f"Failed to remove folder {folder}: {e}")

if __name__ == "__main__":
    cleanup_media_folder()

