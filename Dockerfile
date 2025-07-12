# CUDA 12.6.2 base runtime with Ubuntu 22.04
FROM nvidia/cuda:12.6.2-runtime-ubuntu22.04

WORKDIR /workspace

# Install Python, pip, ffmpeg, and curl
RUN apt-get update && \
    apt-get install -y python3 python3-pip ffmpeg curl && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    pip install --upgrade pip

# Install requirements
COPY requirments.txt .
RUN pip install --no-cache-dir -r requirments.txt

# Additional Python packages
RUN pip install redis==5.0.1 httpx==0.25.2

# Copy source code
COPY . .

# Prepare Whisper model
RUN python3 -c "import whisper_at; whisper_at.load_model('small.en')"

# Upgrade torch
RUN pip install -U torch

# Copy worker script and Redis startup script
COPY worker.py /app/worker.py
COPY start_with_redis.sh /app/start_with_redis.sh
RUN chmod +x /app/start_with_redis.sh

EXPOSE 9007

# Use new startup command
CMD ["/app/start_with_redis.sh"]
