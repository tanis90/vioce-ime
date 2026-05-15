"""Audio recording: hold hotkey to record, release to stop."""

import wave
import numpy as np
import keyboard
import sounddevice as sd
from config import Config


def _find_input_device():
    """Find the first available input device."""
    devices = sd.query_devices()
    for i, dev in enumerate(devices):
        if dev["max_input_channels"] > 0:
            return i
    return None


def record_audio(cfg: Config) -> str:
    """Record audio while the hotkey is held down. Save to WAV.

    Returns:
        Path to the saved WAV file.
    """
    sample_rate = cfg.audio_rate
    channels = cfg.audio_channels

    import time
    print(f"\n[Mic] 录音中... 松开 {cfg.hotkey_record} 结束")
    start = time.time()
    frames = []

    def callback(indata, frame_count, time_info, status):
        frames.append(indata.copy())

    device = _find_input_device()
    if device is None:
        print("[Mic Error] 找不到麦克风设备")
        return cfg.audio_temp_file

    stream = sd.InputStream(
        samplerate=sample_rate,
        channels=channels,
        dtype=np.int16,
        callback=callback,
        device=device,
    )

    with stream:
        while keyboard.is_pressed(cfg.hotkey_record):
            sd.sleep(50)

    elapsed = time.time() - start
    print(f"[Mic] 录音结束，时长: {elapsed:.2f}s")

    if not frames:
        return cfg.audio_temp_file

    audio_data = np.concatenate(frames, axis=0)
    wf = wave.open(cfg.audio_temp_file, "wb")
    wf.setnchannels(channels)
    wf.setsampwidth(2)  # int16 = 2 bytes
    wf.setframerate(sample_rate)
    wf.writeframes(audio_data.tobytes())
    wf.close()
    return cfg.audio_temp_file
