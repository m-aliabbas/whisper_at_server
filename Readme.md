# Whisper-AT Transcription API

A FastAPI server that provides audio transcription services using Whisper-AT, with automatic sampling rate conversion to 16000 Hz when needed.

## Features

- Audio file transcription using Whisper-AT model
- Automatic sampling rate detection and conversion to 16000 Hz
- Configurable audio tagging time resolution
- Adjustable temperature and no-speech threshold parameters
- RESTful API interface

## Installation

1. Clone this repository:

```bash
git clone https://github.com/yourusername/whisper-at-api.git
cd whisper-at-api
```

2. Create a virtual environment (optional but recommended):

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

1. Start the server:

```bash
python app.py
```

The server will be available at `http://localhost:8000` by default.

2. Access the interactive API documentation:

Open your browser and navigate to `http://localhost:8000/docs`

3. Send requests to the API:

```bash
curl -X 'POST' \
  'http://localhost:8000/transcribe/' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@your_audio_file.wav' \
  -F 'audio_tagging_time_resolution=10' \
  -F 'temperature=0.01' \
  -F 'no_speech_threshold=0.4'
```

## API Endpoints

### `POST /transcribe/`

Transcribes an audio file and returns the transcribed text along with segments and audio tags.

**Parameters:**

- `file` (required): Audio file to transcribe (supported formats: .mp3, .wav, .m4a, .flac, .ogg)
- `audio_tagging_time_resolution` (optional, default=10): Temporal resolution for audio tagging in seconds
- `temperature` (optional, default=0.01): Temperature for sampling
- `no_speech_threshold` (optional, default=0.4): Threshold for determining no speech

**Response:**

```json
{
  "text": "Transcribed text content",
  "segments": [...],
  "audio_tags": [...]
}
```

## Environment Variables

None required for basic functionality. The server runs on port 8000 by default.

## Dependencies

See `requirements.txt` for the complete list of dependencies.

## Model Information

This API uses the Whisper-AT model, which is an extension of OpenAI's Whisper model with audio tagging capabilities. The default model size is "base" but can be changed to other sizes (tiny, small, medium, large) by modifying the `MODEL_NAME` constant in the code.

## License

mit
