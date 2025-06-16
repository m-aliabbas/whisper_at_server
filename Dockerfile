# CUDA 12.6.2 base runtime with Ubuntu 22.04
FROM nvidia/cuda:12.6.2-runtime-ubuntu22.04

WORKDIR /workspace

# Install Python, pip, and ffmpeg
RUN apt-get update && \
    apt-get install -y python3 python3-pip ffmpeg && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    pip install --upgrade pip

# Install requirements
COPY requirments.txt .
RUN pip install --no-cache-dir -r requirments.txt

# Copy source code
COPY . .

# At the end of your Dockerfile
RUN python3 -c "import whisper_at; whisper_at.load_model('medium.en')"


EXPOSE 9007

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "9007", "--workers", "4"]
