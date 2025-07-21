import os
import tempfile
import logging
import sys
from typing import Optional

import whisper_at as whisper
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
import librosa
import soundfile as sf
import uvicorn
import numpy as np
from contextlib import asynccontextmanager
from utils import post_process_response_data
import socket

# Configure logging to file and console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("log.txt"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Custom log handler to also capture `print` output
class OutputCapturingHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.setLevel(logging.INFO)
        self.setFormatter(logging.Formatter('%(asctime)s - PRINT - %(message)s'))
        self.file_handler = logging.FileHandler("log.txt", mode="a")

    def emit(self, record):
        self.file_handler.emit(record)

# Redirect `print` to logger
print_logger = logging.getLogger("print_capture")
print_logger.setLevel(logging.INFO)
print_logger.addHandler(OutputCapturingHandler())
original_print = print
def custom_print(*args, **kwargs):
    original_print(*args, **kwargs)
    message = " ".join(str(arg) for arg in args)
    print_logger.info(message)
sys.modules['builtins'].print = custom_print

# Load Whisper-AT model
MODEL_NAME = "medium.en"
model = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global model
    logger.info(f"Loading Whisper-AT model: {MODEL_NAME}")
    model = whisper.load_model(MODEL_NAME)
    logger.info("Model loaded successfully")
    yield
    logger.info("Shutting down application")

# Create FastAPI app
app = FastAPI(
    title="Whisper-AT Transcription API", 
    description="API for transcribing audio files with Whisper-AT",
    version="1.0.18",
    lifespan=lifespan
)

def process_audio(file_path: str) -> tuple:
    """
    Normalize, denoise, pad, and resample audio to 16kHz if needed.
    Returns: (processed_file_path, is_temp_file)
    """
    try:
        def normalize_audio(audio):
            peak = np.max(np.abs(audio))
            return audio / peak if peak > 0 else audio

        def apply_noise_gate(audio, threshold=0.015):
            return np.where(np.abs(audio) < threshold, 0, audio)

        # Load with original sampling rate
        audio_data, sample_rate = librosa.load(file_path, sr=None)
        logger.info(f"Original audio sampling rate: {sample_rate} Hz")

        # Normalize
        audio_data = normalize_audio(audio_data)

        # Denoise with noise gate
        audio_data = apply_noise_gate(audio_data)

        # Pad 1 second silence at start and end
        pad_samples = int(sample_rate * 1)
        silence = np.zeros(pad_samples)
        audio_data = np.concatenate([silence, audio_data, silence])

        # Resample if needed
        target_sr = 16000
        if sample_rate != target_sr:
            logger.info("Resampling to 16000 Hz...")
            audio_data = librosa.resample(audio_data, orig_sr=sample_rate, target_sr=target_sr)
            sample_rate = target_sr

        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            temp_file_path = temp_file.name
        sf.write(temp_file_path, audio_data, sample_rate)
        return temp_file_path, True

    except Exception as e:
        logger.error(f"Error processing audio: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing audio: {str(e)}")

@app.post("/transcribe/", response_class=JSONResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
    audio_tagging_time_resolution: Optional[int] = Form(4.0),
    temperature: Optional[float] = Form(0.01),
    no_speech_threshold: Optional[float] = Form(0.4)
):
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")

    allowed_extensions = [".mp3", ".wav", ".m4a", ".flac", ".ogg"]
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file format. Supported formats: {', '.join(allowed_extensions)}"
        )

    # Save uploaded file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_ext)
    temp_file_path = temp_file.name
    temp_file.close()

    try:
        with open(temp_file_path, "wb") as f:
            f.write(await file.read())

        # Process audio
        processed_file_path, is_processed_temp = process_audio(temp_file_path)
    
        # Transcribe
        logger.info("Starting transcription...")
        result = model.transcribe(
            processed_file_path,
            at_time_res=audio_tagging_time_resolution,
            temperature=0.0,
            no_speech_threshold=no_speech_threshold,
        )

        audio_tag_result = whisper.parse_at_label(
            result,
            language='en',
            top_k=1,
            p_threshold=-3,
            include_class_list=list(range(527))
        )

        text = result.get('text', '')
        hostname = socket.gethostname()
        response_data = {
            "text": text,
            "segments": result.get("segments", []),
            "audio_tags": audio_tag_result,
            "hostname":hostname,
        }
        results_response = post_process_response_data(response_data)
        return JSONResponse(content=results_response)

    except Exception as e:
        logger.error(f"Error during transcription: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error during transcription: {str(e)}")

    finally:
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        if 'processed_file_path' in locals() and is_processed_temp and os.path.exists(processed_file_path):
            os.unlink(processed_file_path)

@app.get("/")
async def root():
    return {"message": "Welcome to Whisper-AT Transcription API. Use /transcribe/ endpoint to transcribe audio files."}

@app.get("/health")
async def health_check():
    try:
        test_file_path = "test.wav"
        if not os.path.exists(test_file_path):
            raise FileNotFoundError("Test file not found")

        processed_file_path, is_temp = process_audio(test_file_path)
        result = model.transcribe(
            processed_file_path,
            at_time_res=10,
            temperature=0.01,
            no_speech_threshold=0.4
        )

        text = result.get("text", "").strip().lower()
        if not text or len(text) < 2:
            raise ValueError("Transcription too short or empty")

        if is_temp and os.path.exists(processed_file_path):
            os.unlink(processed_file_path)

        return {"status": "ok", "text": text}

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")

if __name__ == "__main__":
    print("Starting Whisper-AT Transcription Server")
    uvicorn.run("server:app", host="0.0.0.0", port=9007, reload=True)
