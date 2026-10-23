"""Local whisper transcript for media with no subtitle tracks (Instagram reels).

Usage: python scripts/transcribe_whisper.py <audio-or-video file> <out.txt> [model]
Needs `pip install faster-whisper` (CPU, int8). The model downloads on first use.
"""
import sys

from faster_whisper import WhisperModel


def transcribe(src, out, model_name="small.en"):
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    segs, info = model.transcribe(src, vad_filter=True)
    text = "\n".join(s.text.strip() for s in segs)
    with open(out, "w", encoding="utf-8") as f:
        f.write(text)
    return info.duration, len(text)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    dur, n = transcribe(*sys.argv[1:4])
    print(f"duration={dur:.0f}s chars={n}")
