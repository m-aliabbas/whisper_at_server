# worker.py
import os
import redis
import json
import time
import httpx
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


class WhisperWorker:
    def __init__(self):
        self.redis = redis.Redis(
            host=os.environ.get("REDIS_HOST"),
            port=6379,
            password=os.environ.get("REDIS_PASSWORD"),
            decode_responses=False
        )
        self.redis.ping()
        logger.info("Connected to Redis")

    def run(self):
        logger.info("Worker started, waiting for jobs...")
        while True:
            try:
                job_id = self.redis.brpoplpush("queue:pending", "queue:processing", timeout=5)
                if job_id:
                    job_id = job_id.decode() if isinstance(job_id, bytes) else job_id
                    self.process_job(job_id)
                    self.redis.lrem("queue:processing", 1, job_id)
            except Exception as e:
                logger.error(f"Error: {e}")
                time.sleep(5)

    def process_job(self, job_id):
        try:
            audio_data = self.redis.get(f"audio:{job_id}")
            if not audio_data:
                return

            with httpx.Client(timeout=300) as client:
                files = {'audio': ('audio.wav', audio_data, 'audio/wav')}
                response = client.post("http://localhost:9007/transcribe", files=files)

                if response.status_code == 200:
                    result = response.json()
                    self.redis.setex(
                        f"result:{job_id}",
                        3600,
                        json.dumps({"text": result.get("text", ""), "job_id": job_id})
                    )
                    logger.info(f"Job {job_id} completed")
        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")


if __name__ == "__main__":
    WhisperWorker().run()