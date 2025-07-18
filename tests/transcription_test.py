import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)
supported_models = ["tiny", "tiny.en", "base", "base.en", "small", "small.en"]

class TestTranscriptionClass:
    @pytest.fixture(scope="class", autouse=True)
    def setup_files(self, request):
        with open("tests/test_media/obama.mp3", "rb") as file:
            audio_response = client.post("/uploadmedia", files={"file": file})
            print("Audio upload response:", audio_response.json())
            request.cls.file_ID = audio_response.json()["fileID"]
        yield
        print("Cleaning up uploaded files...")
        client.post(f"/deletemedia?fileID={request.cls.file_ID}")
    @pytest.mark.parametrize("model", supported_models)
    @pytest.mark.parametrize("language", ["en", "fr", "de", "es"])
    @pytest.mark.parametrize("output_format", ["srt", "vtt", "txt"])
    def test_transcription(self, model, language, output_format):
        if "en" in model and language != "en":
            pytest.skip(f"Skipping transcription test for model {model} with language {language} (English model)")
        elif  language != 'en' and model != 'tiny':
            pytest.skip(f"Skipping test for model {model} with language {language} (only model 'tiny' supported for non-English languages)")

        print(f"Testing transcription with model {model}, output format {output_format}")
        data = {
            "filename": "obama.mp3",
            "fileID": self.file_ID,
            "model": model,
            "language": language,
            "output_format": output_format
        }
        with client.websocket_connect("/transcribe") as websocket:
            websocket.send_json(data)
            while True:
                response = websocket.receive_json()
                print(response)
                if response["status"] == "progress":
                    print("Progress:", response)
                elif response["status"] == "error":
                    print("Error during transcription:", response["message"])
                    if "Transcription timeout" in response["message"]:
                        final_response = response
                        break
                else:
                    final_response = response
                    break
            print(final_response)
            assert final_response["status"] == "success"
            assert final_response["filename"] == f"obama.{output_format}"

class TestFastTranscriptionClass:
    @pytest.fixture(scope="class", autouse=True)
    def setup_files(self, request):
        with open("tests/test_media/obama.mp3", "rb") as file:
            audio_response = client.post("/uploadmedia", files={"file": file})
            print("Audio upload response:", audio_response.json())
            request.cls.file_ID = audio_response.json()["fileID"]
        yield
        print("Cleaning up uploaded files...")
        client.post(f"/deletemedia?fileID={request.cls.file_ID}")

    @pytest.mark.parametrize("model", supported_models)
    @pytest.mark.parametrize("output_format", ["srt", "vtt", "txt", "ass"])
    def test_fast_transcription(self, model, output_format):
        print(f"Testing fast transcription with model {model}, output format {output_format}")
        data = {
            "filename": "obama.mp3",
            "fileID": self.file_ID,
            "model": model,
            "output_format": output_format
        }
        with client.websocket_connect("/transcribe-fast") as websocket:
            websocket.send_json(data)
            while True:
                response = websocket.receive_json()
                print(response)
                if response["status"] == "progress":
                    print("Progress:", response)
                elif response["status"] == "error":
                    print("Error during transcription:", response["message"])
                    if "Transcription timeout" in response["message"]:
                        final_response = response
                        break
                else:
                    final_response = response
                    break
            print(final_response)
            assert final_response["status"] == "success"
            assert final_response["filename"] == f"obama.{output_format}"
