import json
import os
import uuid

from fastapi import FastAPI, UploadFile, HTTPException, WebSocket
from fastapi.responses import FileResponse
from starlette.websockets import WebSocketDisconnect

from helper import change_file_format, transcribe_file

app = FastAPI()


@app.get("/")
async def root():
    return {"status": "200 OK"}


@app.post("/uploadmedia")
async def upload_media(file: UploadFile):
    try:
        fileID = uuid.uuid4()
        while os.path.exists(f'./media/{fileID}'):
            fileID = uuid.uuid4()
        os.mkdir(f'./media/{fileID}')

        file_path = f"./media/{fileID}/" + file.filename
        print('Uploading file:', file_path)
        with open(file_path, "wb") as f:
            f.write(await file.read())
    except Exception as e:
        print("Error uploading file")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        file.file.close()
    return {"filename": file.filename, "size": file.size, "fileID": str(fileID)}

@app.get('/downloadmedia')
async def download_media(fileID: str, filename: str):
    try:
        filepath = f'./media/{fileID}/{filename}'
        return FileResponse(filepath)
    except Exception as e:
        print("Error downloading file:", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/changeformat")
async def change_format(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            print("Received data:", data)
            filename = data["filename"]
            fileID = data["fileID"]
            output_format = data["output_format"]
            vcodec = data.get("video_codec", "copy")
            acodec = data.get("audio_codec", "copy")
            print(vcodec, acodec)
            print(f"Changing format of {filename} ({fileID}) to {output_format}")
            await change_file_format(websocket, fileID, filename, output_format, vcodec, acodec)
    except WebSocketDisconnect:
        print("WebSocket disconnected")
        await websocket.close(1000, "WebSocket closed")
    except Exception as e:
        print("Error in WebSocket connection:", str(e))
        await websocket.close(1011, "Internal Server Error")

@app.websocket("/transcribe")
async def transcribe(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            print("Received data for transcription:", data)
            filename = data["filename"]
            fileID = data["fileID"]
            model = data.get("model", "base")
            language = data.get("language", "en")
            output_format = data.get("output_format", "srt")
            print(f"Transcribing {filename} ({fileID}) using model {model}")
            await transcribe_file(websocket, fileID, filename, model, language, output_format)

    except WebSocketDisconnect:
        print("WebSocket disconnected during transcription")
        await websocket.close(1000, "WebSocket closed")
    except Exception as e:
        print("Error in transcription WebSocket connection:", str(e))
        await websocket.close(1011, "Internal Server Error")