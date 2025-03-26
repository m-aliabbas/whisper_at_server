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
from contextlib import asynccontextmanager

# Configure logging to write to file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("log.txt"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create a custom log handler for output capturing
class OutputCapturingHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.setLevel(logging.INFO)
        self.setFormatter(logging.Formatter('%(asctime)s - PRINT - %(message)s'))
        self.file_handler = logging.FileHandler("log.txt", mode="a")
    
    def emit(self, record):
        self.file_handler.emit(record)

# Setup a logger for print statements
print_logger = logging.getLogger("print_capture")
print_logger.setLevel(logging.INFO)
print_logger.addHandler(OutputCapturingHandler())

# Save the original print function
original_print = print

# Define a custom print function
def custom_print(*args, **kwargs):
    # Call the original print function
    original_print(*args, **kwargs)
    
    # Log the print statement
    message = " ".join(str(arg) for arg in args)
    print_logger.info(message)

# Replace the built-in print with our custom print
sys.modules['builtins'].print = custom_print

# Global model variable
MODEL_NAME = "base"  # You can change this to other model sizes: tiny, small, medium, large, etc.
model = None

# Define lifespan context manager (replaces on_event)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Load model
    global model
    logger.info(f"Loading Whisper-AT model: {MODEL_NAME}")
    model = whisper.load_model(MODEL_NAME)
    logger.info("Model loaded successfully")
    
    yield  # This is where FastAPI serves requests
    
    # Shutdown: Add any cleanup code here if needed
    logger.info("Shutting down application")

# Create FastAPI app with lifespan
app = FastAPI(
    title="Whisper-AT Transcription API", 
    description="API for transcribing audio files with Whisper-AT",
    version="1.0.0",
    lifespan=lifespan
)

def process_audio(file_path: str,sr1=None) -> tuple:
    """
    Check audio sampling rate and convert if necessary
    
    Returns:
        tuple: (processed_file_path, is_temp_file)
    """
    try:
        # Get the audio sampling rate
        audio_data, sample_rate = librosa.load(file_path, sr=None)
        if sr1:
            sample_rate = sr1
        logger.info(f"Original audio sampling rate: {sample_rate} Hz")
        
        # If sampling rate is not 16000 Hz, convert it
        if sample_rate != 16000:
            logger.info("Converting audio to 16000 Hz...")
            
            # Create a temporary file for the resampled audio
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            temp_file_path = temp_file.name
            temp_file.close()
            
            # Resample audio to 16000 Hz
            audio_resampled = librosa.resample(audio_data, orig_sr=sample_rate, target_sr=16000)
            
            # Save the resampled audio
            sf.write(temp_file_path, audio_resampled, 16000)
            
            return temp_file_path, True
        
        # If sampling rate is already 16000 Hz, return the original file path
        return file_path, False
    
    except Exception as e:
        logger.error(f"Error processing audio: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing audio: {str(e)}")

@app.post("/transcribe/", response_class=JSONResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
    audio_tagging_time_resolution: Optional[int] = Form(10),
    temperature: Optional[float] = Form(0.01),
    no_speech_threshold: Optional[float] = Form(0.4)
):
    """
    Endpoint to transcribe audio files using Whisper-AT.
    
    Parameters:
        - file: Audio file to transcribe
        - audio_tagging_time_resolution: Temporal resolution for audio tagging in seconds
        - temperature: Temperature for sampling
        - no_speech_threshold: Threshold for determining no speech
        
    Returns:
        JSON with transcription results
    """
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Check if the file has an audio extension
    allowed_extensions = [".mp3", ".wav", ".m4a", ".flac", ".ogg"]
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file format. Supported formats: {', '.join(allowed_extensions)}"
        )
    
    # Save the uploaded file temporarily
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_ext)
    temp_file_path = temp_file.name
    temp_file.close()
    
    try:
        # Write the file content
        with open(temp_file_path, "wb") as f:
            f.write(await file.read())
        
        # Process the audio file (check sampling rate and convert if needed)
        processed_file_path, is_processed_temp = process_audio(temp_file_path)
        
        # Transcribe using Whisper-AT
        logger.info("Starting transcription...")
        result = model.transcribe(
            processed_file_path, 
            at_time_res=audio_tagging_time_resolution,
            temperature=0.01,
            no_speech_threshold=0.4
        )
        # print('AT result', result)
        # print(result['segments'], len(result['segments']))
        try:
            no_speech_prob = float(result['segments'][0]['no_speech_prob'])
        except Exception as e:
            no_speech_prob = 0.2
            processed_file_path, is_processed_temp = process_audio(temp_file_path,sr1=8000)
            result = model.transcribe(
            processed_file_path, 
            at_time_res=audio_tagging_time_resolution,
            temperature=0.01,
            no_speech_threshold=0.4
                ) 
            print('Error', e, "Setting to no_speech_prob 0.5")
        print('Result Text',result['text'])
        if no_speech_prob >= 0.4:
            text = ""
        else:
            text = result["text"]
       
        logger.info("Transcription completed")

        text = text.lower()
        text = text.strip()

        if 'bye bye' in text:
            return ''

        if len(text) <= 10:
            
            if text == 'you':
                text = ''
            elif 'the' in text:
                text = ''

            elif 'bye bye' in text:
                text = ''
            
        print('Final Text', text)
        # Prepare response
        response_data = {
            "text": text,
            "segments": result.get("segments", []),
            "audio_tags": result.get("audio_tags", [])
        }
        
        return JSONResponse(content=response_data)
    
    except Exception as e:
        logger.error(f"Error during transcription: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error during transcription: {str(e)}")
    
    finally:
        # Clean up temporary files
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        
        if 'processed_file_path' in locals() and is_processed_temp and os.path.exists(processed_file_path):
            os.unlink(processed_file_path)

@app.get("/")
async def root():
    return {"message": "Welcome to Whisper-AT Transcription API. Use /transcribe/ endpoint to transcribe audio files."}

if __name__ == "__main__":
    print("Starting Whisper-AT Transcription Server")
    uvicorn.run("server:app", host="0.0.0.0", port=9007, reload=True)