import os
import argparse
import json
import requests
from typing import Dict, Any, Optional, Union


class WhisperATClient:
    """Client for interacting with the Whisper-AT Transcription API"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        Initialize the Whisper-AT client.
        
        Args:
            base_url: Base URL of the Whisper-AT API server
        """
        self.base_url = base_url.rstrip('/')
        self.transcribe_endpoint = f"{self.base_url}/transcribe/"
    
    def check_server_status(self) -> bool:
        """
        Check if the server is running.
        
        Returns:
            bool: True if server is accessible, False otherwise
        """
        try:
            response = requests.get(self.base_url, timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    def transcribe(
        self, 
        audio_file_path: str, 
        audio_tagging_time_resolution: int = 10,
        temperature: float = 0.01,
        no_speech_threshold: float = 0.4,
        output_file: Optional[str] = None,
        verbose: bool = False
    ) -> Dict[str, Any]:
        """
        Transcribe an audio file using the Whisper-AT API.
        
        Args:
            audio_file_path: Path to the audio file
            audio_tagging_time_resolution: Temporal resolution for audio tagging in seconds
            temperature: Temperature for sampling
            no_speech_threshold: Threshold for determining no speech
            output_file: Optional path to save the transcription results as JSON
            verbose: Whether to print progress information
            
        Returns:
            Dict containing the transcription results
        """
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")
        
        if verbose:
            print(f"Sending file {audio_file_path} for transcription...")
        
        # Prepare the form data
        files = {
            'file': (os.path.basename(audio_file_path), open(audio_file_path, 'rb'), self._get_content_type(audio_file_path))
        }
        
        data = {
            'audio_tagging_time_resolution': str(audio_tagging_time_resolution),
            'temperature': str(temperature),
            'no_speech_threshold': str(no_speech_threshold)
        }
        
        try:
            # Send the request
            response = requests.post(
                self.transcribe_endpoint,
                files=files,
                data=data
            )
            
            # Close the file
            files['file'][1].close()
            
            # Check if the request was successful
            response.raise_for_status()
            
            # Parse the response
            result = response.json()
            
            if verbose:
                print("Transcription completed successfully.")
                print(f"Transcribed text: {result['text']}")
            
            # Save the results to a file if requested
            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                if verbose:
                    print(f"Results saved to {output_file}")
            
            return result
            
        except requests.RequestException as e:
            # Close the file if it's still open
            if 'file' in locals() and hasattr(files['file'][1], 'close'):
                files['file'][1].close()
            
            error_message = f"Error during transcription request: {str(e)}"
            
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_details = e.response.json()
                    error_message += f"\nServer response: {error_details.get('detail', 'Unknown error')}"
                except ValueError:
                    error_message += f"\nServer response status code: {e.response.status_code}"
            
            raise RuntimeError(error_message)
    
    def _get_content_type(self, file_path: str) -> str:
        """
        Get the content type based on the file extension.
        
        Args:
            file_path: Path to the file
            
        Returns:
            str: MIME type for the file
        """
        extension = os.path.splitext(file_path)[1].lower()
        
        content_types = {
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.m4a': 'audio/m4a',
            '.flac': 'audio/flac',
            '.ogg': 'audio/ogg'
        }
        
        return content_types.get(extension, 'application/octet-stream')


def main():
    """Command-line interface for the Whisper-AT client"""
    parser = argparse.ArgumentParser(description="Whisper-AT Transcription Client")
    
    parser.add_argument("audio_file", help="Path to the audio file to transcribe")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of the Whisper-AT API (default: http://localhost:8000)")
    parser.add_argument("--time-res", type=int, default=10, help="Audio tagging time resolution in seconds (default: 10)")
    parser.add_argument("--temp", type=float, default=0.01, help="Temperature for sampling (default: 0.01)")
    parser.add_argument("--no-speech", type=float, default=0.4, help="No speech threshold (default: 0.4)")
    parser.add_argument("--output", help="Path to save the transcription results as JSON")
    parser.add_argument("--verbose", action="store_true", help="Print detailed information")
    
    args = parser.parse_args()
    
    client = WhisperATClient(base_url=args.url)
    
    # Check if the server is running
    if not client.check_server_status():
        print(f"Error: Could not connect to the server at {args.url}")
        print("Make sure the server is running and the URL is correct.")
        return
    
    try:
        # Transcribe the audio file
        result = client.transcribe(
            audio_file_path=args.audio_file,
            audio_tagging_time_resolution=args.time_res,
            temperature=args.temp,
            no_speech_threshold=args.no_speech,
            output_file=args.output,
            verbose=args.verbose
        )
        
        # Print the transcribed text
        if not args.verbose:
            print(result["text"])
        
    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    main()