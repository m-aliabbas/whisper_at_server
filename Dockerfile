FROM nvidia/cuda:12.6.2-runtime-ubuntu22.04

WORKDIR /workspace

RUN apt-get update && \
    apt-get install -y python3 python3-pip curl git ffmpeg build-essential && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    pip install --upgrade pip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python -c "import whisper_at; whisper_at.load_model('medium.en')"

EXPOSE 9007

CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port 9007 --workers 4"]

