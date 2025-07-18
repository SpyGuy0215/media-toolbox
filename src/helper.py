from concurrent.futures import ThreadPoolExecutor

import ffmpeg
from PIL import Image, features
from pillow_heif import register_heif_opener
import whisper.utils
from fastapi import WebSocket
import mimetypes
import asyncio

mimetypes.add_type("image/webp", ".webp")  # mimetypes does not support webp by default
mimetypes.add_type("video/flv", ".flv")  # mimetypes does not support flv by default


async def change_file_format(websocket: WebSocket, fileID, filename, output_format, vcodec, acodec):
    filepath = f"./media/{fileID}/{filename}"
    filename_without_ext = filename.rsplit('.', 1)[0]
    output_path = f"./media/{fileID}/{filename_without_ext}.{output_format}"

    print(f"Converting {filepath} to {output_path} with format {output_format}")

    # find out whether the file is image or video
    media_type = get_media_type(filepath)
    if media_type is None:
        await websocket.send_json({"status": "error", "message": "Mimetype error: Unsupported file type"})
        return
    elif media_type == 'image':
        # For images, we can use ffmpeg to convert formats
        try:
            # use PIL to open the image and convert it
            input_format = filename.rsplit('.', 1)[-1].lower()
            if output_format in ['heic', 'heif'] or input_format in ['heic', 'heif']:
                register_heif_opener()
            image = Image.open(filepath)
            if output_format.lower() == 'jpg' and image.mode != 'RGB':
                # JPEG does not support palette mode color, needs to be RGB
                image = image.convert('RGB')
            image.save(output_path)
            await websocket.send_json(
                {"status": "success", "message": f"Image converted to {output_format}", "output_format": output_format,
                 "fileID": fileID})
        except Exception as e:
            print("Error converting image:", str(e))
            await websocket.send_json({"status": "error", "message": str(e)})
    elif media_type == 'video':
        # For videos, we can use ffmpeg to convert formats
        try:
            # Get total duration in seconds using ffprobe
            probe = ffmpeg.probe(filepath)
            duration = float(probe['format']['duration'])
            process = (
                ffmpeg
                .input(filepath)
                .output(output_path, vcodec=vcodec, acodec=acodec)
                .global_args('-progress', 'pipe:1', '-nostats', '-loglevel', 'error')
                .run_async(pipe_stdout=True, pipe_stderr=True, overwrite_output=True)
            )

            progress = {"status": "progress"}
            # ffmpeg progress output parsing
            print("Starting ffmpeg process for video conversion...")
            while True:
                output = await asyncio.get_event_loop().run_in_executor(None, process.stdout.readline)
                try:
                    if output == b'' and process.poll() is not None:
                        break
                    if output:
                        print(output)
                        decoded = output.decode(errors='ignore').strip()
                        if '=' in decoded:
                            key, value = decoded.split('=', 1)
                            progress[key] = value
                            # Calculate progress percentage using out_time (in format HH:MM:SS.microseconds)
                            if key == 'out_time' and duration > 0:
                                h, m, s = value.split(':')
                                sec = float(h) * 3600 + float(m) * 60 + float(s)
                                percent = min(100, (sec / duration) * 100)
                                progress['progress_percent'] = percent
                            if key == 'progress':
                                # Only send progress update when ffmpeg emits a 'progress' key
                                await websocket.send_json(progress)
                                if value == 'end':
                                    break  ##
                except Exception as e:
                    print("Error parsing ffmpeg output:", str(e))
                    await websocket.send_json({"status": "error", "message": str(e)})
                    continue

            print("FFmpeg process completed, waiting for finalization...")
            process.wait()
            print("FFmpeg process finalized with return code:", process.returncode)
            stderr_output = process.stderr.read()
            for line in stderr_output.splitlines():
                print(line)
            if process.returncode == 0:
                await websocket.send_json({"status": "success", "message": f"Video converted to {output_format}",
                                           "output_format": output_format, "fileID": fileID})
            else:
                await websocket.send_json({
                    "status": "error",
                    "message": f"ffmpeg failed with exit code {process.returncode}. Check if the output format is valid."
                })
        except ffmpeg.Error as e:
            print("FFmpeg error:", e)
            await websocket.send_json({"status": "error", "message": str(e)})
    elif media_type == 'audio':
        # For audio files, we can also use ffmpeg to convert formats
        try:
            process = (
                ffmpeg
                .input(filepath)
                .output(output_path, acodec=acodec)
                .global_args('-progress', 'pipe:1', '-nostats')
                .run_async(pipe_stdout=True, pipe_stderr=True, overwrite_output=True)
            )

            progress = {"status": "progress"}
            # ffmpeg progress output parsing
            while True:
                output = await asyncio.get_event_loop().run_in_executor(None, process.stdout.readline)
                if output == b'' and process.poll() is not None:
                    break
                if output:
                    decoded = output.decode(errors='ignore').strip()
                    if '=' in decoded:
                        key, value = decoded.split('=', 1)
                        progress[key] = value
                        if key == 'progress':
                            # Only send progress update when ffmpeg emits a 'progress' key
                            await websocket.send_json(progress)
                            if value == 'end':
                                break

            process.wait()
            if process.returncode == 0:
                await websocket.send_json({"status": "success", "message": f"Audio converted to {output_format}",
                                           "output_format": output_format, "fileID": fileID})
            else:
                await websocket.send_json({
                    "status": "error",
                    "message": f"ffmpeg failed with exit code {process.returncode}. Check if the output format is valid."
                })
        except ffmpeg.Error as e:
            print("FFmpeg error:", e)
            await websocket.send_json({"status": "error", "message": str(e)})


def get_media_type(filename):
    mimestart = mimetypes.guess_type(filename)[0]
    print(mimestart)
    if mimestart and mimestart.startswith('image/'):
        return 'image'
    elif mimestart and mimestart.startswith('video/'):
        return 'video'
    elif mimestart and mimestart.startswith('audio/'):
        return 'audio'
    else:
        return None


async def transcribe_file(websocket: WebSocket, fileID, filename, model, language, output_format):
    filepath = f"./media/{fileID}/{filename}"
    filename_without_ext = filename.rsplit('.', 1)[0]

    if language != "en" and model != "tiny":
        await websocket.send_json(
            {"status": "error", "message": "Only tiny models are supported for non-English languages"})
        return

    if language != "en" and "en" in model:
        await websocket.send_json(
            {"status": "error", "message": "English model cannot transcribe non-English languages"})
        return

    if language == 'en':
        MODEL_TIMEOUT = 60
    else:
        MODEL_TIMEOUT = 120

    print(f"Transcribing {filepath} using model {model} and language {language}")
    try:
        model = whisper.load_model(model)
        queue: asyncio.Queue = asyncio.Queue()
        loop = asyncio.get_running_loop()
        executor = ThreadPoolExecutor(max_workers=1)
        print("Setting up transcription with Whisper model...")

        def progress_callback(progress):
            print("Progress callback:", progress)
            queue.put_nowait({"status": "progress", "progress": progress})

        task = loop.run_in_executor(
            executor,
            lambda: model.transcribe(filepath, verbose=False, language=language, progress_callback=progress_callback)
        )

        await websocket.send_json({"status": "progress", "message": "Transcription started", "progress": 0.0})
        while True:
            try:
                print("Waiting for transcription updates...")
                update = await asyncio.wait_for(queue.get(), timeout=MODEL_TIMEOUT)
                await websocket.send_json(update)
                await asyncio.sleep(0.1)  # Avoid busy waiting
                if update.get("status") == "progress" and update.get("progress") == 100.0:
                    break
            except asyncio.TimeoutError:
                await websocket.send_json({"status": "error", "message": f"Transcription timeout ({MODEL_TIMEOUT}s without updates)"})

        result = await task
        writer = whisper.utils.get_writer(output_format, f'./media/{fileID}/')
        writer(result, filepath)
        await websocket.send_json(
            {"status": "success", "message": f"Transcription completed: {filename_without_ext}.{output_format}",
             "filename": f"{filename_without_ext}.{output_format}"})

    except Exception as e:
        print("Error during transcription:", str(e))
        await websocket.send_json({"status": "error", "message": str(e)})
        return
