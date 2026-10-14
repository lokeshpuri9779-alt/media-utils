"""Deterministic caption-window planning for narration and dialogue.

No transcription claim: timestamps must come from an upstream narration,
subtitle or dialogue source. Character-length estimates are explicitly marked.
"""


def build_caption_windows(text, *, start=0.0, duration=None,
                          word_times=None, words_per_caption=4):
    if not isinstance(text, str) or not text.strip():
        return []
    if not 1 <= words_per_caption <= 12:
        raise ValueError("words_per_caption out of range")
    if start < 0:
        raise ValueError("negative start")
    words = text.split()
    if word_times is not None:
        if len(word_times) != len(words):
            raise ValueError("word_times must contain one (start,end) per word")
        previous = start
        for first, last in word_times:
            if first < previous - 1e-7 or last <= first:
                raise ValueError("overlapping or invalid word timestamps")
            previous = last
        chunks = []
        for i in range(0, len(words), words_per_caption):
            end = min(len(words), i + words_per_caption)
            chunks.append({"text": " ".join(words[i:end]),
                           "start": round(float(word_times[i][0]), 3),
                           "end": round(float(word_times[end - 1][1]), 3),
                           "timing_source": "word_timestamps"})
        return chunks
    if duration is None or duration <= 0:
        raise ValueError("positive duration required without word timestamps")
    if duration < .12:
        raise ValueError("duration too short for captions")
    # Estimate by character count rather than allocating equal time to
    # short and long phrases. This is not word-level audio alignment.
    lengths = [max(1, len(w)) for w in words]
    total = sum(lengths)
    elapsed = 0
    times = []
    for length in lengths:
        a = start + duration * elapsed / total
        elapsed += length
        b = start + duration * elapsed / total
        times.append((a, b))
    chunks = build_caption_windows(text, start=start,
                                   word_times=times,
                                   words_per_caption=words_per_caption)
    for item in chunks:
        item["timing_source"] = "estimated_text_length"
    return chunks


def active_caption(windows, timestamp):
    if timestamp < 0:
        return None
    for window in windows:
        if window["start"] <= timestamp < window["end"]:
            return window["text"]
    return None
