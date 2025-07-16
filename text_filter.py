import re, unicodedata

# Example BoH list (lowercase, punctuation stripped)
BOH = {
    "thank you", "thanks for watching", "thank you for watching",
    "so", "the", "you", "oh"
}

def normalize_text(text):
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r"[^a-zA-Z0-9.,'\s]", '', text)
    return re.sub(r'\s+', ' ', text).strip().lower()

def remove_whisper_hallucinations(text):
    norm = normalize_text(text)
    if not norm:
        return ""
    # remove if only dots or 3+ consecutive dots
    if re.fullmatch(r"[.]+", norm) or re.search(r"\.{3,}", norm):
        return ""
    # remove if it exactly matches a BoH phrase
    if norm in BOH:
        return ""
    return text
