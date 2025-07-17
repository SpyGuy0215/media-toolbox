import pytest
from fastapi.testclient import TestClient

from src.main import app

image_ID, video_ID, audio_ID = None, None, None

class TestUploadClass:
    def test_upload_image(self):
        client = TestClient(app)
        with open("tests/test_media/car.jpg", "rb") as file:
            response = client.post("/uploadmedia", files={"file": file})
        assert response.status_code == 200
        data = response.json()
        print("Response data:", data)
        assert "filename" in data
        assert "size" in data
        assert "fileID" in data
        global image_ID
        image_ID = data["fileID"]
        assert data["filename"] == "car.jpg"
        assert data["size"] > 0
        assert data["fileID"] is not None


    def test_upload_video(self):
        client = TestClient(app)
        with open("tests/test_media/bunny.mp4", "rb") as file:
            response = client.post("/uploadmedia", files={"file": file})
        assert response.status_code == 200
        data = response.json()
        print("Response data:", data)
        assert "filename" in data
        assert "size" in data
        assert "fileID" in data
        global video_ID
        video_ID = data["fileID"]
        assert data["filename"] == "bunny.mp4"
        assert data["size"] > 0
        assert data["fileID"] is not None

    def test_upload_audio(self):
        client = TestClient(app)
        with open("tests/test_media/obama.mp3", "rb") as file:
            response = client.post("/uploadmedia", files={"file": file})
        assert response.status_code == 200
        data = response.json()
        print("Response data:", data)
        assert "filename" in data
        assert "size" in data
        assert "fileID" in data
        assert data["filename"] == "obama.mp3"
        global audio_ID
        audio_ID = data["fileID"]
        assert data["size"] > 0
        assert data["fileID"] is not None

class TestDownloadClass:
    def test_download_image(self):
        client = TestClient(app)
        response = client.get(f"/downloadmedia?fileID={image_ID}&filename=car.jpg")
        print("Download response:", response)
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/jpeg"

    def test_download_video(self):
        client = TestClient(app)
        response = client.get(f"/downloadmedia?fileID={video_ID}&filename=bunny.mp4")
        print("Download response:", response)
        assert response.status_code == 200
        assert response.headers["content-type"] == "video/mp4"

    def test_download_audio(self):
        client = TestClient(app)
        response = client.get(f"/downloadmedia?fileID={audio_ID}&filename=obama.mp3")
        print("Download response:", response)
        assert response.status_code == 200
        assert response.headers["content-type"] == "audio/mpeg"

