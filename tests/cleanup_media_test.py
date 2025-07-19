import os
import time
import shutil
from pathlib import Path
import pytest

from src.scripts.cleanup_media import cleanup_media_folder

TEST_MEDIA_ROOT = Path(__file__).parent / 'test_media_cleanup'

@pytest.fixture(autouse=True)
def setup_and_teardown():
    # Setup: create test folders and files
    if TEST_MEDIA_ROOT.exists():
        shutil.rmtree(TEST_MEDIA_ROOT)
    TEST_MEDIA_ROOT.mkdir()
    old_folder = TEST_MEDIA_ROOT / 'old_folder'
    new_folder = TEST_MEDIA_ROOT / 'new_folder'
    old_folder.mkdir()
    new_folder.mkdir()
    old_file = old_folder / 'old_file.txt'
    new_file = new_folder / 'new_file.txt'
    old_file.write_text('old')
    new_file.write_text('new')
    # Set old file mtime to 13 hours ago
    old_time = time.time() - (13 * 60 * 60)
    os.utime(old_file, (old_time, old_time))
    # Set new file mtime to now
    os.utime(new_file, None)
    yield
    # Teardown
    shutil.rmtree(TEST_MEDIA_ROOT)

def test_cleanup_deletes_old_files_and_folders(monkeypatch):
    # Patch MEDIA_DIR in the script to point to our test folder
    monkeypatch.setattr('src.scripts.cleanup_media.MEDIA_DIR', TEST_MEDIA_ROOT)
    cleanup_media_folder()
    # old_file should be deleted, old_folder should be removed
    assert not (TEST_MEDIA_ROOT / 'old_folder').exists()
    # new_file should remain, new_folder should remain
    assert (TEST_MEDIA_ROOT / 'new_folder' / 'new_file.txt').exists()
    assert (TEST_MEDIA_ROOT / 'new_folder').exists()

