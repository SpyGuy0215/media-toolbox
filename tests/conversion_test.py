import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

image_types = ["jpg", "png", "webp", "gif", "tiff", "bmp", "avif", "heic"]
video_types = ["mp4", "mov", "avi", "mkv", "flv", "wmv", "webm"]
audio_types = ["mp3", "wav", "ogg", "flac", "aac", "m4a", "opus"]


class TestImageConversionClass:
    @pytest.fixture(scope="class", autouse=True)
    def setup_files(self, request):
        with open("tests/test_media/car.jpg", "rb") as file:
            image_response = client.post("/uploadmedia", files={"file": file})
            print("Image upload response:", image_response.json())
            request.cls.file_ID = image_response.json()["fileID"]
        yield
        print("Cleaning up uploaded files...")
        client.post(f"/deletemedia?fileID={request.cls.file_ID}")

    @pytest.mark.parametrize("output_type", image_types)
    @pytest.mark.parametrize("input_type", image_types)
    def test_image_conversion(self, input_type, output_type):
        print(f"Testing image conversion from {input_type} to {output_type}")
        if input_type == output_type:
            pytest.skip("Input and output types are the same, skipping conversion test.")

        data = {
            "filename": f"car.{input_type}",
            "fileID": self.file_ID,
            "output_format": output_type
        }

        with client.websocket_connect("/changeformat") as websocket:
            websocket.send_json(data)
            response = websocket.receive_json()
            print(response)
            assert response["status"] == "success"
            assert response["output_format"] == output_type
            assert response["fileID"] == self.file_ID


class TestVideoConversionClass:
    @pytest.fixture(scope="class", autouse=True)
    def setup_files(self, request):
        with open("tests/test_media/bunny.mp4", "rb") as file:
            video_response = client.post("/uploadmedia", files={"file": file})
            print("Video upload response:", video_response.json())
            request.cls.file_ID = video_response.json()["fileID"]
        yield
        print("Cleaning up uploaded files...")
        client.post(f"/deletemedia?fileID={request.cls.file_ID}")

    @pytest.mark.parametrize("output_type", video_types)
    @pytest.mark.parametrize("input_type", video_types)
    def test_video_conversion(self, input_type, output_type):
        print(f"Testing video conversion from {input_type} to {output_type}")
        if input_type == output_type:
            pytest.skip("Input and output types are the same, skipping conversion test.")

        data = {
            "filename": f"bunny.{input_type}",
            "fileID": self.file_ID,
            "output_format": output_type
        }

        if output_type == "webm":
            data["video_codec"] = "libvpx-vp9"
            data["audio_codec"] = "libvorbis"
        elif output_type == "avi":
            data["video_codec"] = "mpeg4"
            data["audio_codec"] = "mp3"
        elif output_type == "flv":
            data["video_codec"] = "flv"
            data["audio_codec"] = "mp3"
        elif output_type == "wmv":
            data["video_codec"] = "wmv2"
        elif output_type == "mov":
            data["video_codec"] = "libx264"
        elif output_type == "mp4":
            data["video_codec"] = "libx264"
            data["audio_codec"] = "aac"

        with client.websocket_connect("/changeformat") as websocket:
            websocket.send_json(data)
            while True:
                response = websocket.receive_json()
                if response["status"] == "progress":
                    print("Progress:", response)
                elif response["status"] == "error" and response["message"] == "not enough values to unpack (expected 3, got 1)":
                    # issue in ffmpeg, process is still running
                    print(response["message"])
                    continue
                else:
                    print(response["message"])
                    final_response = response
                    break
            print(final_response)
            assert final_response["status"] == "success"
            assert final_response["output_format"] == output_type
            assert final_response["fileID"] == self.file_ID


class TestAudioConversionClass:
    @pytest.fixture(scope="class", autouse=True)
    def setup_files(self, request):
        with open("tests/test_media/obama.mp3", "rb") as file:
            audio_response = client.post("/uploadmedia", files={"file": file})
            print("Audio upload response:", audio_response.json())
            request.cls.file_ID = audio_response.json()["fileID"]
        yield
        print("Cleaning up uploaded files...")
        client.post(f"/deletemedia?fileID={request.cls.file_ID}")

    @pytest.mark.parametrize("output_type", audio_types)
    @pytest.mark.parametrize("input_type", audio_types)
    def test_audio_conversion(self, input_type, output_type):
        print(f"Testing audio conversion from {input_type} to {output_type}")
        if input_type == output_type:
            pytest.skip("Input and output types are the same, skipping conversion test.")

        data = {
            "filename": f"obama.{input_type}",
            "fileID": self.file_ID,
            "output_format": output_type
        }
        if output_type == "ogg":
            data["audio_codec"] = "libvorbis"
        elif output_type == "flac":
            data["audio_codec"] = "flac"
        elif output_type == "mp3":
            data["audio_codec"] = "libmp3lame"
        elif output_type == "aac" or output_type == "m4a":
            data["audio_codec"] = "aac"
        elif output_type == "opus":
            data["audio_codec"] = "libopus"
        elif output_type == "wav":
            data["audio_codec"] = "pcm_s16le"

        with client.websocket_connect("/changeformat") as websocket:
            websocket.send_json(data)
            while True:
                response = websocket.receive_json()
                print(response)
                if response["status"] == "progress":
                    print("Progress:", response)
                else:
                    final_response = response
                    break
            assert final_response["status"] == "success"
            assert final_response["output_format"] == output_type
            assert final_response["fileID"] == self.file_ID
