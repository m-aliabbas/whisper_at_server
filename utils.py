def post_process_response_data(response_data):
    target_classes = {
        "Telephone", "Telephone bell ringing", "Ringtone", "Telephone dialing, DTMF",
        "Dial tone", "Busy signal", "Alarm clock", "Siren", "Civil defense siren",
        "Buzzer", "Tearing", "Beep, bleep", "Ping", "Sine wave", "Echo",
        "Sidetone", "Sound effect", "Cowbell", "Vibraphone"
    }

    # Step 1: Filter segments
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

    # Step 3: Determine final text
    if contains_dialtone_audio:
        final_text = "DIAL TONE"
    else:
        final_text = " ".join(segment.get("text", "") for segment in filtered_segments).strip()

    # Step 4: Construct final response
    return {
        "text": final_text,
        "segments": filtered_segments,
        "audio_tags": response_data.get("audio_tags", [])
    }
