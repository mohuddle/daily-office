#!/usr/bin/env python3
"""Local and cloud TTS backends for office audio.

Providers:
  chatterbox  — Resemble Chatterbox Multilingual v3 (default). UK/English
                prosody from the v3 checkpoint, not the English-only model.
  kokoro      — Kokoro-82M. CPU-friendly built-in voices.
  qwen3       — Qwen3-TTS. Best cloning / instruction control; wants a GPU.
  leo         — xAI Leo cloud TTS. Optional; needs a funded API key.
"""

from __future__ import annotations

import inspect
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTH_PATH = Path.home() / ".grok" / "auth.json"
TTS_URL = "https://api.x.ai/v1/tts"
CONFIG_PATH = ROOT / "tts.json"
KOKORO_DIR = ROOT / "models" / "kokoro"
KOKORO_ONNX = KOKORO_DIR / "kokoro-v1.0.onnx"
KOKORO_VOICES = KOKORO_DIR / "voices-v1.0.bin"
KOKORO_ONNX_URL = (
    "https://github.com/thewh1teagle/kokoro-onnx/releases/download/"
    "model-files-v1.0/kokoro-v1.0.onnx"
)
KOKORO_VOICES_URL = (
    "https://github.com/thewh1teagle/kokoro-onnx/releases/download/"
    "model-files-v1.0/voices-v1.0.bin"
)
CHATTERBOX_REPO = "ResembleAI/chatterbox"
CHATTERBOX_V3_DIR = ROOT / "models" / "chatterbox-v3"
CHATTERBOX_V3_WEIGHTS = "t3_mtl23ls_v3.safetensors"
CHATTERBOX_V2_WEIGHTS = "t3_mtl23ls_v2.safetensors"
MAX_LEO_CHARS = 14000
PROVIDERS = ("chatterbox", "kokoro", "qwen3", "leo")
TAG_RE = re.compile(
    r"\[(pause|long-pause|silence\s+(\d+(?:\.\d+)?)s)\]",
    re.IGNORECASE,
)

_KOKORO = None
_CHATTERBOX = None
_QWEN = None
_QWEN_PROMPT = None
DESIGNED_VOICE = ROOT / "voices" / "qwen_reader.wav"
DESIGNED_TEXT_PATH = ROOT / "voices" / "qwen_reader.txt"
DESIGN_SAMPLE = (
    "Welcome to Morning Prayer. A reading from sahm twenty-three. "
    "The Lord is my shepherd; I shall not want. SAYlah. "
    "The Word of the Lord. Thanks be to God. Ah-men."
)


@dataclass
class TtsSettings:
    provider: str = "qwen3"
    voice: str = "Aiden"
    clone: bool = False
    language: str = "en"
    device: str = "auto"
    reference: Path | None = None
    reference_text: str = ""
    instruct: str = (
        "Calm, reverent, unhurried Anglican liturgical reading. "
        "Clear male narrator. Speak every sentence slowly and in full. "
        "Pronounce Amen as two slow syllables: Ah-men. "
        "Pronounce Selah as SAYlah."
    )
    exaggeration: float = 0.25
    cfg_weight: float = 0.3
    speed: float = 0.88
    model: str = "1.7b"

    def summary(self) -> str:
        bits = [self.provider]
        if self.provider == "kokoro":
            bits.append(self.voice)
        elif self.provider == "qwen3":
            bits.append(self.model or "1.7b")
            if (self.voice or "").lower() == "design":
                bits.append("design")
            else:
                bits.append("clone" if self.clone else (self.voice or "Aiden"))
        elif self.provider == "chatterbox":
            bits.append(self.model or "v3")
            bits.append(self.language)
            bits.append(f"exag={self.exaggeration:g}")
        if self.reference:
            bits.append(f"ref={self.reference.name}")
        if abs(self.speed - 1.0) >= 0.01:
            bits.append(f"speed={self.speed:g}")
        bits.append(self.resolve_device())
        return " ".join(bits)

    def resolve_device(self) -> str:
        if self.device and self.device != "auto":
            return self.device
        try:
            import torch

            if torch.cuda.is_available():
                return "cuda"
        except Exception:
            pass
        return "cpu"

    @classmethod
    def from_sources(
        cls,
        provider: str | None = None,
        voice: str | None = None,
        device: str | None = None,
        reference: str | None = None,
        instruct: str | None = None,
        exaggeration: float | None = None,
        model: str | None = None,
        reference_text: str | None = None,
    ) -> TtsSettings:
        data: dict = {}
        if CONFIG_PATH.exists():
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        env_provider = os.environ.get("DAILY_OFFICE_TTS", "").strip()
        chosen = (provider or env_provider or data.get("provider") or "qwen3").lower()
        if chosen not in PROVIDERS:
            raise SystemExit(f"unknown TTS provider {chosen!r}; use {', '.join(PROVIDERS)}")
        ref_raw = reference or data.get("reference") or ""
        ref_path = Path(ref_raw) if ref_raw else None
        if ref_path and not ref_path.is_absolute():
            ref_path = ROOT / ref_path
        if ref_path and not ref_path.exists():
            raise SystemExit(f"TTS reference clip not found: {ref_path}")
        defaults = {
            "kokoro": "am_adam",
            "qwen3": "design",
            "chatterbox": "",
            "leo": "leo",
        }
        model_default = "1.7b" if chosen == "qwen3" else ("v3" if chosen == "chatterbox" else "")
        return cls(
            provider=chosen,
            voice=voice or data.get("voice") or defaults[chosen],
            language=(data.get("language") or "en").lower(),
            device=device or data.get("device") or "auto",
            reference=ref_path,
            reference_text=reference_text or data.get("reference_text") or "",
            instruct=instruct or data.get("instruct") or cls.instruct,
            exaggeration=float(
                exaggeration if exaggeration is not None else data.get("exaggeration", 0.25)
            ),
            cfg_weight=float(data.get("cfg_weight", 0.3)),
            speed=float(data.get("speed", 0.88 if chosen == "chatterbox" else 1.0)),
            model=model or data.get("model") or model_default,
            clone=bool(data.get("clone", False)),
        )


def looks_like_api_key(value: str) -> bool:
    if value.startswith("xai-") and len(value) >= 20:
        return True
    if value.startswith("eyJ") and len(value) >= 100:
        return True
    return False


def leo_token() -> str:
    candidates: list[tuple[str, str]] = []
    env = os.environ.get("XAI_API_KEY", "").strip()
    if env:
        candidates.append(("XAI_API_KEY", env))
    key_file = ROOT / ".xai_api_key"
    if key_file.exists():
        value = key_file.read_text(encoding="utf-8").strip()
        if value:
            candidates.append((str(key_file), value))
    if AUTH_PATH.exists():
        auth = json.loads(AUTH_PATH.read_text(encoding="utf-8"))
        value = next(iter(auth.values()), {}).get("key", "")
        if value:
            candidates.append((str(AUTH_PATH), value))
    rejected: list[str] = []
    for source, value in candidates:
        if looks_like_api_key(value):
            if rejected:
                print(
                    f"warning: ignored invalid key from {', '.join(rejected)}; using {source}",
                    flush=True,
                )
            return value
        rejected.append(source)
    raise SystemExit(
        "Leo needs a funded xAI API key. Prefer a local provider instead:\n"
        "  py -3.13 scripts\\generate_office_audio.py --tts chatterbox --week\n"
        "Or create a key at https://console.x.ai (it usually starts with xai-) "
        "and put it in .xai_api_key."
    )


def split_script(text: str) -> list[tuple[str, object]]:
    """Turn [pause] / [long-pause] / [silence Ns] into speech and silence parts."""
    parts: list[tuple[str, object]] = []
    last = 0
    for match in TAG_RE.finditer(text):
        before = text[last : match.start()].strip()
        if before:
            parts.append(("speech", before))
        tag = match.group(1).lower()
        if tag == "pause":
            parts.append(("silence", 0.6))
        elif tag == "long-pause":
            parts.append(("silence", 2.0))
        else:
            parts.append(("silence", float(match.group(2))))
        last = match.end()
    rest = text[last:].strip()
    if rest:
        parts.append(("speech", rest))
    return parts or [("speech", text.strip())]


def merge_short_speech(parts: list[tuple[str, object]], min_chars: int = 160) -> list[tuple[str, object]]:
    """Join tiny phrases so Chatterbox is not asked to speak one sentence alone.

    Short clips are where it hallucinates tails and forces EOS.
    """
    out: list[tuple[str, object]] = []
    i = 0
    while i < len(parts):
        kind, value = parts[i]
        if kind != "speech":
            out.append(parts[i])
            i += 1
            continue
        text = str(value).strip()
        j = i + 1
        while j + 1 < len(parts):
            mid, nxt = parts[j], parts[j + 1]
            if mid[0] != "silence" or nxt[0] != "speech":
                break
            if float(mid[1]) > 1.5:
                break
            nxt_text = str(nxt[1]).strip()
            if len(text) >= min_chars and len(nxt_text) >= min_chars:
                break
            text = f"{text} {nxt_text}".strip()
            j += 2
        out.append(("speech", text))
        i = j
    return out or parts


def chunk_text(text: str, limit: int) -> list[str]:
    if len(text) <= limit:
        return [text]
    pieces: list[str] = []
    buf: list[str] = []
    size = 0
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        extra = len(sentence) + (1 if buf else 0)
        if buf and size + extra > limit:
            pieces.append(" ".join(buf))
            buf = [sentence]
            size = len(sentence)
        else:
            buf.append(sentence)
            size += extra
    if buf:
        pieces.append(" ".join(buf))
    return pieces


def wav_to_mp3(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(src),
            "-c:a",
            "libmp3lame",
            "-b:a",
            "128k",
            "-ar",
            "44100",
            "-ac",
            "1",
            str(dest),
        ],
        check=True,
    )
    if dest.stat().st_size < 400:
        raise RuntimeError(f"TTS wrote a suspiciously small file: {dest}")


def write_wav_mp3(samples, rate: int, dest: Path) -> None:
    import soundfile as sf

    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as handle:
        tmp = Path(handle.name)
    try:
        sf.write(tmp, samples, rate)
        wav_to_mp3(tmp, dest)
    finally:
        tmp.unlink(missing_ok=True)


def trim_speech(samples, rate: int, pad_ms: float = 30) -> object:
    """Drop leading/trailing hiss so stitched pauses stay quiet."""
    import numpy as np

    wav = np.asarray(samples, dtype=np.float32).reshape(-1)
    if wav.size == 0:
        return wav
    peak = float(np.max(np.abs(wav))) or 1.0
    mask = np.abs(wav) > (0.045 * peak)
    if not np.any(mask):
        return wav
    start = max(0, int(np.argmax(mask) - rate * pad_ms / 1000))
    end = min(len(wav), int(len(wav) - np.argmax(mask[::-1]) + rate * pad_ms / 1000))
    clip = wav[start:end].copy()
    fade = min(int(rate * 0.04), max(1, len(clip) // 6))
    if fade > 1:
        ramp = np.linspace(0.0, 1.0, fade, dtype=np.float32)
        clip[:fade] *= ramp
        clip[-fade:] *= ramp[::-1]
    return clip


def slow_mp3(src: Path, dest: Path, speed: float) -> None:
    if speed <= 0 or abs(speed - 1.0) < 0.01:
        if src != dest:
            dest.write_bytes(src.read_bytes())
        return
    if not 0.5 <= speed <= 2.0:
        raise RuntimeError(f"speed {speed} is outside ffmpeg atempo range 0.5–2.0")
    tmp = dest.with_suffix(".slow.mp3") if src == dest else dest
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(src),
            "-filter:a",
            f"atempo={speed}",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "128k",
            str(tmp),
        ],
        check=True,
    )
    if tmp != dest:
        tmp.replace(dest)


def make_silence(dest: Path, seconds: float) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=44100:cl=mono",
            "-t",
            str(seconds),
            "-c:a",
            "libmp3lame",
            "-b:a",
            "128k",
            str(dest),
        ],
        check=True,
    )


def concat_mp3(parts: list[Path], dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    inputs: list[str] = []
    for part in parts:
        inputs.extend(["-i", str(part)])
    filters = "".join(f"[{i}:a]" for i in range(len(parts)))
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            *inputs,
            "-filter_complex",
            f"{filters}concat=n={len(parts)}:v=0:a=1[out]",
            "-map",
            "[out]",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "128k",
            str(dest),
        ],
        check=True,
    )


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"downloading {dest.name}…", flush=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    urllib.request.urlretrieve(url, tmp)
    tmp.replace(dest)


def _ensure_kokoro_onnx_files() -> None:
    if not KOKORO_ONNX.exists() or KOKORO_ONNX.stat().st_size < 1_000_000:
        _download(KOKORO_ONNX_URL, KOKORO_ONNX)
    if not KOKORO_VOICES.exists() or KOKORO_VOICES.stat().st_size < 100_000:
        _download(KOKORO_VOICES_URL, KOKORO_VOICES)


def _kokoro_engine(settings: TtsSettings):
    global _KOKORO
    if _KOKORO is not None:
        return _KOKORO
    try:
        from kokoro_onnx import Kokoro
    except ImportError:
        Kokoro = None
    if Kokoro is not None:
        _ensure_kokoro_onnx_files()
        print("loading Kokoro-82M (onnx)…", flush=True)
        _KOKORO = ("onnx", Kokoro(str(KOKORO_ONNX), str(KOKORO_VOICES)))
        return _KOKORO
    try:
        from kokoro import KPipeline
    except ImportError as exc:
        raise SystemExit(
            "Kokoro is not installed. In PowerShell:\n"
            "  pip install kokoro-onnx soundfile\n"
            "First run downloads ~340MB of model files into models/kokoro/."
        ) from exc
    print("loading Kokoro-82M…", flush=True)
    _KOKORO = ("pipeline", KPipeline(lang_code="a"))
    return _KOKORO


def synthesize_kokoro(settings: TtsSettings, text: str, dest: Path) -> None:
    import numpy as np

    kind, engine = _kokoro_engine(settings)
    voice = settings.voice or "am_adam"
    if kind == "onnx":
        samples, rate = engine.create(text, voice=voice, speed=0.95, lang="en-us")
        write_wav_mp3(samples, int(rate), dest)
        return
    chunks = []
    for _gs, _ps, audio in engine(text, voice=voice):
        chunks.append(audio)
    if not chunks:
        raise RuntimeError("Kokoro produced no audio")
    write_wav_mp3(np.concatenate(chunks), 24000, dest)


def _download_chatterbox_v3() -> Path:
    """Fetch Multilingual v3 into models/chatterbox-v3.

    PyPI chatterbox-tts 0.1.7 hardcodes t3_mtl23ls_v2.safetensors and has no
    t3_model= argument. Alias the v3 file so from_local() loads v3 weights.
    """
    from huggingface_hub import snapshot_download

    CHATTERBOX_V3_DIR.mkdir(parents=True, exist_ok=True)
    print(
        f"downloading Chatterbox Multilingual v3 ({CHATTERBOX_V3_WEIGHTS})…",
        flush=True,
    )
    ckpt = Path(
        snapshot_download(
            repo_id=CHATTERBOX_REPO,
            repo_type="model",
            revision="main",
            allow_patterns=[
                "ve.pt",
                CHATTERBOX_V3_WEIGHTS,
                "s3gen.pt",
                "grapheme_mtl_merged_expanded_v1.json",
                "conds.pt",
                "Cangjie5_TC.json",
            ],
            local_dir=str(CHATTERBOX_V3_DIR),
        )
    )
    v3 = ckpt / CHATTERBOX_V3_WEIGHTS
    if not v3.exists():
        raise RuntimeError(f"Hugging Face did not provide {CHATTERBOX_V3_WEIGHTS}")
    alias = ckpt / CHATTERBOX_V2_WEIGHTS
    if not alias.exists() or alias.stat().st_size != v3.stat().st_size:
        if alias.exists() or alias.is_symlink():
            alias.unlink()
        try:
            os.link(v3, alias)
        except OSError:
            shutil.copy2(v3, alias)
    return ckpt


def _ensure_perth_watermarker() -> None:
    """Chatterbox always constructs perth.PerthImplicitWatermarker().

    resemble-perth 1.0.1 leaves that name as None when pkg_resources
    (setuptools) is missing, which crashes from_local() on a fresh venv.
    """
    import perth

    if perth.PerthImplicitWatermarker is not None:
        return
    perth.PerthImplicitWatermarker = perth.DummyWatermarker
    print(
        "warning: Perth watermarker unavailable; using a no-op so generation can continue",
        flush=True,
    )


def _load_chatterbox_v3(device: str):
    _ensure_perth_watermarker()
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS

    sig = inspect.signature(ChatterboxMultilingualTTS.from_pretrained)
    if "t3_model" in sig.parameters:
        return ChatterboxMultilingualTTS.from_pretrained(device=device, t3_model="v3")
    ckpt = _download_chatterbox_v3()
    print(f"loading v3 weights from {ckpt}…", flush=True)
    return ChatterboxMultilingualTTS.from_local(ckpt, device)


def _chatterbox_model(settings: TtsSettings):
    global _CHATTERBOX
    if _CHATTERBOX is not None:
        return _CHATTERBOX
    device = settings.resolve_device()
    kind = (settings.model or "v3").lower()
    print(f"loading Chatterbox {kind} on {device}…", flush=True)
    try:
        if kind in {"v3", "multilingual", "mtl"}:
            model = _load_chatterbox_v3(device)
            kind = "v3"
        elif kind in {"nano", "turbo"}:
            from chatterbox.tts_turbo import ChatterboxTurboTTS

            model = ChatterboxTurboTTS.from_pretrained(device=device, nano=(kind == "nano"))
        else:
            from chatterbox.tts import ChatterboxTTS

            model = ChatterboxTTS.from_pretrained(device=device)
    except ImportError as exc:
        raise SystemExit(
            "Chatterbox is not installed. From the repo root:\n"
            "  .\\.venv\\Scripts\\python.exe -m pip install chatterbox-tts"
        ) from exc
    _CHATTERBOX = (kind, model)
    return _CHATTERBOX


def spoken_for_office(text: str, provider: str = "qwen3") -> str:
    """Respell a few liturgical words for the active TTS backend."""
    replacements: list[tuple[str, str]] = [
        # Phonetic spellings: "Psalm" otherwise becomes "Pee-salm".
        (r"\bPsalms\b", "sahms"),
        (r"\bPsalm\b", "sahm"),
        # Y-into-L keeps SAY-lah from splitting into See-loo.
        (r"\bSelah\b", "SAYlah"),
        (r"\bAmen\b", "Ah-men"),
        (r"\bAMEN\b", "Ah-men"),
    ]
    if provider == "chatterbox":
        replacements = [
            (r"\bPsalms\b", "sahms"),
            (r"\bPsalm\b", "sahm"),
            (r"\bSelah\b", "SAYlah"),
            (r"\bAmen\b", "Ah-men"),
            (r"\bAMEN\b", "Ah-men"),
            (r"\bHallelujah\b", "Hal-le-lu-jah"),
            (r"\bAlleluia\b", "Al-le-lu-ia"),
        ]
    out = text
    for pattern, spoken in replacements:
        out = re.sub(pattern, spoken, out)
    return out


def spoken_for_chatterbox(text: str) -> str:
    return spoken_for_office(text, "chatterbox")


def synthesize_chatterbox(settings: TtsSettings, text: str, dest: Path) -> None:
    import numpy as np

    kind, model = _chatterbox_model(settings)
    kwargs: dict = {"exaggeration": settings.exaggeration}
    if settings.reference:
        kwargs["audio_prompt_path"] = str(settings.reference)
    elif kind in {"nano", "turbo"}:
        raise SystemExit(
            "Chatterbox Turbo/Nano need a reference clip for cloning.\n"
            "Put a 5–10s WAV of a voice you own in voices/reader.wav and set\n"
            '  "reference": "voices/reader.wav"  in tts.json\n'
            "or use --tts-ref voices/reader.wav.\n"
            "Do not clone xAI Leo from existing MP3s."
        )
    if kind == "v3":
        kwargs["language_id"] = settings.language or "en"
        kwargs["cfg_weight"] = settings.cfg_weight
        kwargs["temperature"] = 0.7
        kwargs["repetition_penalty"] = 1.4
    pieces = []
    for chunk in chunk_text(text, 500):
        wav = model.generate(chunk, **kwargs)
        if hasattr(wav, "detach"):
            wav = wav.detach().cpu().numpy()
        pieces.append(trim_speech(np.squeeze(wav), int(model.sr)))
    write_wav_mp3(np.concatenate(pieces), int(model.sr), dest)


def _qwen_torch():
    try:
        import torch
        from qwen_tts import Qwen3TTSModel
    except ImportError as exc:
        raise SystemExit(
            "Qwen3-TTS is not installed. From the repo root:\n"
            "  .\\.venv\\Scripts\\python.exe -m pip install qwen-tts\n"
            "  .\\.venv\\Scripts\\python.exe -m pip install torch torchvision torchaudio "
            "--index-url https://download.pytorch.org/whl/cu124"
        ) from exc
    return torch, Qwen3TTSModel


def _qwen_device(settings: TtsSettings) -> tuple[str, object]:
    torch, _Qwen = _qwen_torch()
    device = settings.resolve_device()
    if (settings.device or "").lower() == "cuda" and device == "cpu":
        raise SystemExit(
            "tts.json asks for cuda but this venv has CPU-only PyTorch.\n"
            "  .\\.venv\\Scripts\\python.exe -m pip install torch torchvision torchaudio "
            "--index-url https://download.pytorch.org/whl/cu124"
        )
    if device == "cpu":
        print("warning: Qwen3-TTS on CPU is very slow", flush=True)
    dtype = torch.float16 if device.startswith("cuda") else torch.float32
    device_map = "cuda:0" if device.startswith("cuda") else "cpu"
    return device_map, dtype


def _load_qwen_weights(model_id: str, device_map: str, dtype) -> object:
    torch, Qwen3TTSModel = _qwen_torch()
    print(f"loading {model_id} on {device_map} ({dtype})…", flush=True)
    load_kw = {"device_map": device_map, "dtype": dtype}
    try:
        return Qwen3TTSModel.from_pretrained(model_id, attn_implementation="sdpa", **load_kw)
    except TypeError:
        return Qwen3TTSModel.from_pretrained(model_id, **load_kw)
    except Exception as exc:
        if "out of memory" not in str(exc).lower() or "0.6B" in model_id:
            raise
        print(f"warning: {model_id} did not fit; falling back to 0.6B", flush=True)
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        small = model_id.replace("1.7B", "0.6B")
        try:
            return Qwen3TTSModel.from_pretrained(small, attn_implementation="sdpa", **load_kw)
        except TypeError:
            return Qwen3TTSModel.from_pretrained(small, **load_kw)


def _ensure_designed_reader(settings: TtsSettings) -> tuple[Path, str]:
    """Create a reusable British reader with VoiceDesign, then we clone it."""
    if DESIGNED_VOICE.exists() and DESIGNED_VOICE.stat().st_size > 20_000:
        sample = (
            DESIGNED_TEXT_PATH.read_text(encoding="utf-8").strip()
            if DESIGNED_TEXT_PATH.exists()
            else DESIGN_SAMPLE
        )
        return DESIGNED_VOICE, sample
    torch, _Qwen = _qwen_torch()
    device_map, dtype = _qwen_device(settings)
    size = "1.7B" if "0.6" not in (settings.model or "").lower() else "0.6B"
    model_id = f"Qwen/Qwen3-TTS-12Hz-{size}-VoiceDesign"
    design = _load_qwen_weights(model_id, device_map, dtype)
    prompt = settings.instruct or (
        "A warm, calm, and polite male voice in his 40s with a clear British "
        "accent and a gentle, reassuring delivery."
    )
    print("designing office reader voice…", flush=True)
    wavs, sr = design.generate_voice_design(
        text=DESIGN_SAMPLE,
        language="English",
        instruct=prompt,
        max_new_tokens=4096,
    )
    DESIGNED_VOICE.parent.mkdir(parents=True, exist_ok=True)
    import soundfile as sf

    sf.write(DESIGNED_VOICE, wavs[0], int(sr))
    DESIGNED_TEXT_PATH.write_text(DESIGN_SAMPLE + "\n", encoding="utf-8")
    del design
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    print(f"wrote {DESIGNED_VOICE}", flush=True)
    return DESIGNED_VOICE, DESIGN_SAMPLE


def _qwen_model(settings: TtsSettings):
    global _QWEN
    if _QWEN is not None:
        return _QWEN
    device_map, dtype = _qwen_device(settings)
    design = (settings.voice or "").lower() == "design"
    clone = settings.clone or design or (settings.model or "").lower() == "clone"
    if design:
        wav, ref_text = _ensure_designed_reader(settings)
        settings.reference = wav
        settings.reference_text = ref_text
        settings.clone = True
        clone = True
    size = "1.7B" if "0.6" not in (settings.model or "").lower() else "0.6B"
    model_id = (
        f"Qwen/Qwen3-TTS-12Hz-{size}-Base"
        if clone
        else f"Qwen/Qwen3-TTS-12Hz-{size}-CustomVoice"
    )
    model = _load_qwen_weights(model_id, device_map, dtype)
    _QWEN = (clone, model)
    return _QWEN


def synthesize_qwen3(settings: TtsSettings, text: str, dest: Path) -> None:
    global _QWEN_PROMPT
    import numpy as np

    clone, model = _qwen_model(settings)
    # Long psalms need a high cap so Qwen does not stop mid-verse.
    gen_kw = {"max_new_tokens": 8192}
    if clone and _QWEN_PROMPT is None:
        if not settings.reference:
            raise SystemExit("Qwen3 clone mode needs tts.json reference (a WAV you own).")
        _QWEN_PROMPT = model.create_voice_clone_prompt(
            ref_audio=str(settings.reference),
            ref_text=settings.reference_text or None,
            x_vector_only_mode=not settings.reference_text,
        )
    pieces = []
    rate = 24000
    # Short chunks keep volume and pace from fading over a long psalm.
    for chunk in chunk_text(text, 750):
        if clone:
            wavs, sr = model.generate_voice_clone(
                text=chunk,
                language="English",
                voice_clone_prompt=_QWEN_PROMPT,
                **gen_kw,
            )
        else:
            wavs, sr = model.generate_custom_voice(
                text=chunk,
                language="English",
                speaker=settings.voice or "Aiden",
                instruct=settings.instruct,
                **gen_kw,
            )
        pieces.append(np.asarray(wavs[0]).reshape(-1))
        rate = int(sr)
    write_wav_mp3(np.concatenate(pieces), rate, dest)


def synthesize_leo(text: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if len(text) > MAX_LEO_CHARS:
        raise RuntimeError(f"script too long ({len(text)} chars) for {dest.name}")
    payload = json.dumps(
        {
            "text": text,
            "voice_id": "leo",
            "language": "en",
            "text_normalization": True,
            "output_format": {"codec": "mp3", "sample_rate": 44100, "bit_rate": 128000},
        }
    ).encode()
    last: Exception | None = None
    for attempt in range(1, 4):
        req = urllib.request.Request(
            TTS_URL,
            data=payload,
            headers={
                "Authorization": f"Bearer {leo_token()}",
                "Content-Type": "application/json",
                "User-Agent": "daily-office-tts/1.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                dest.write_bytes(resp.read())
            if dest.stat().st_size < 1000:
                raise RuntimeError(f"TTS wrote a suspiciously small file: {dest}")
            return
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace").strip()
            last = RuntimeError(f"HTTP {exc.code} {exc.reason}: {body[:500]}")
            print(f"  TTS attempt {attempt} failed: {last}", flush=True)
            if exc.code in {400, 401, 403, 404}:
                break
            time.sleep(2 * attempt)
        except (urllib.error.URLError, TimeoutError, RuntimeError) as exc:
            last = exc
            print(f"  TTS attempt {attempt} failed: {exc}", flush=True)
            time.sleep(2 * attempt)
    raise RuntimeError(f"TTS failed for {dest.name}: {last}")


def _speak_local(settings: TtsSettings, text: str, dest: Path) -> None:
    if settings.provider == "kokoro":
        synthesize_kokoro(settings, text, dest)
    elif settings.provider == "chatterbox":
        synthesize_chatterbox(settings, text, dest)
    elif settings.provider == "qwen3":
        synthesize_qwen3(settings, text, dest)
    else:
        raise RuntimeError(f"not a local provider: {settings.provider}")


def synthesize(settings: TtsSettings, text: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if settings.provider == "leo":
        synthesize_leo(text, dest)
        return
    work = spoken_for_office(text, settings.provider)
    parts = split_script(work)
    if settings.provider == "chatterbox":
        parts = merge_short_speech(parts)
    speech_n = sum(1 for kind, _ in parts if kind == "speech")
    spoken = 0

    def speak_to(path: Path, spoken_text: str) -> None:
        nonlocal spoken
        spoken += 1
        print(f"  speech {spoken}/{speech_n} ({len(spoken_text)} chars)", flush=True)
        _speak_local(settings, spoken_text, path)
        if abs(settings.speed - 1.0) >= 0.01:
            slow_mp3(path, path, settings.speed)

    speech_parts = [p for p in parts if p[0] == "speech"]
    if len(parts) == 1 and speech_parts:
        speak_to(dest, str(speech_parts[0][1]))
        return
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        files: list[Path] = []
        for i, (kind, value) in enumerate(parts):
            path = tmpdir / f"part-{i:03d}.mp3"
            if kind == "silence":
                seconds = float(value)
                if seconds <= 0:
                    continue
                make_silence(path, seconds)
            else:
                speak_to(path, str(value))
            files.append(path)
        if not files:
            raise RuntimeError("nothing to synthesize")
        if len(files) == 1:
            dest.write_bytes(files[0].read_bytes())
        else:
            concat_mp3(files, dest)
