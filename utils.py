import re
import unicodedata
from text_filter import remove_whisper_hallucinations

def clean_text(text):
    # Normalize and remove non-ASCII characters
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')

    # Remove emojis and pictographs
    emoji_pattern = re.compile(
        "["                     
        "\U0001F600-\U0001F64F"  # Emoticons
        "\U0001F300-\U0001F5FF"  # Symbols & pictographs
        "\U0001F680-\U0001F6FF"  # Transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # Flags
        "\U00002700-\U000027BF"  # Dingbats
        "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
        "\U00002600-\U000026FF"  # Misc symbols
        "]+", flags=re.UNICODE
    )
    text = emoji_pattern.sub('', text)

    # Remove all characters except letters, numbers, '.', ',', and "'"
    text = re.sub(r"[^a-zA-Z0-9.,'\s]", '', text)

    # Remove extra spaces
    text = re.sub(r'\s+', ' ', text).strip()

    # If only dots or contains more than two consecutive dots, return empty string
    if re.fullmatch(r"[.]+", text) or re.search(r"\.{3,}", text):
        return ""

    return text



# def post_process_response_data(response_data):
#     target_classes = {
#         "Telephone", "Telephone bell ringing", "Ringtone", "Telephone dialing, DTMF",
#         "Dial tone", "Busy signal", "Alarm clock", "Siren", "Civil defense siren",
#         "Buzzer", "Tearing", "Beep, bleep", "Ping", "Echo",
#         "Sidetone", "Sound effect", "Cowbell", "Vibraphone"
#     }

#     music_classes = {"Music","Musical instrument","Plucked string instrument","Guitar","Tapping (guitar technique)",
#     "Drum","Television","Radio","Noise","Echo","Reverberation","Environmental noise","Knock","Tap"}

#     # Step 1: Filter segments
#     filtered_segments = [
#         segment for segment in response_data.get("segments", [])
#         if segment.get("no_speech_prob", 1.0) <= 0.55
#     ]

#     # Step 2: Check for dialtone-related audio tags
#     contains_dialtone_audio = any(
#         tag in target_classes
#         for tag_entry in response_data.get("audio_tags", [])
#         for tag, _ in tag_entry.get("audio tags", [])
#     )

#     # Step 3: Determine final text
#     if contains_dialtone_audio:
#         final_text = "DIAL TONE"
#     else:
#         final_segments = []
#         previous_text = None

#         for segment in filtered_segments:
#             text = segment.get("text", "").strip()
#             if text and text != previous_text:
#                 final_segments.append(text)
#                 previous_text = text

#         final_text = " ".join(final_segments)
#         final_text = clean_text(final_text)
#         final_text = remove_whisper_hallucinations(final_text)

#     # Step 4: Construct final response
#     return {
#         "text": final_text,
#         "segments": filtered_segments,
#         "audio_tags": response_data.get("audio_tags", [])
#     }



def post_process_response_data(response_data):
    target_classes = {
        "Telephone", "Telephone bell ringing", "Ringtone", "Telephone dialing, DTMF",
        "Dial tone", "Busy signal", "Alarm clock", "Siren", "Civil defense siren",
        "Buzzer", "Tearing", "Beep, bleep", "Ping", "Echo",
        "Sidetone", "Sound effect", "Cowbell", "Vibraphone"
    }

    music_classes = {
        "Music", "Musical instrument", "Plucked string instrument", "Guitar", 
        "Tapping (guitar technique)", "Drum", "Television", "Radio", "Noise", 
        "Echo", "Reverberation", "Environmental noise", "Knock", "Tap"
    }

    # Step 1: Filter segments by no_speech_prob
    filtered_segments = [
        segment for segment in response_data.get("segments", [])
        if segment.get("no_speech_prob", 1.0) <= 0.55
    ]

    # Step 2: Check for dialtone-related audio tags
    contains_dialtone_audio = any(
        tag in target_classes
        for tag_entry in response_data.get("audio_tags", [])
        for tag, _ in tag_entry.get("audio tags", [])
    )

    # Step 3: Blank segment text if overlapping music tag
    for segment in filtered_segments:
        seg_start = segment.get("start", 0)
        seg_end = segment.get("end", 0)

        for tag_entry in response_data.get("audio_tags", []):
            tag_start = tag_entry.get("start", 0)
            tag_end = tag_entry.get("end", 0)

            if tag_start < seg_end and tag_end > seg_start:  # overlap
                for tag, _ in tag_entry.get("audio tags", []):
                    if tag in music_classes:
                        segment["text"] = ""
                        break  # no need to check more tags for this segment
                else:
                    continue
                break  # exit outer loop if segment text was cleared

    # Step 4: Determine final text
    if contains_dialtone_audio:
        final_text = "DIAL TONE"
    else:
        final_segments = []
        previous_text = None

        for segment in filtered_segments:
            text = segment.get("text", "").strip()
            if text and text != previous_text:
                final_segments.append(text)
                previous_text = text

        final_text = " ".join(final_segments)
        final_text = clean_text(final_text)
        final_text = remove_whisper_hallucinations(final_text)

    # Step 5: Return final structured response
    return {
        "text": final_text,
        "segments": filtered_segments,
        "audio_tags": response_data.get("audio_tags", [])
    }
