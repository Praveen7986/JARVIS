"""
Real-time Sound-driven Audio Visualizer Engine.
Captures live system/music audio output via Windows WASAPI Loopback (comtypes/ctypes)
and computes real-time 5-band frequency spectrum (Bass, Low-Mid, Mid, High-Mid, Treble)
with physics-based attack/decay for smooth, organic equalizer animation.
"""

import ctypes
from ctypes import wintypes, POINTER, c_float, c_uint, byref, c_void_p, c_int, Structure, c_short, c_ulong
import logging
import threading
import time
from typing import List, Optional
import numpy as np

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)

# --- Windows WASAPI COM Interfaces ---

class WAVEFORMATEX(Structure):
    _fields_ = [
        ('wFormatTag', c_short),
        ('nChannels', c_short),
        ('nSamplesPerSec', c_ulong),
        ('nAvgBytesPerSec', c_ulong),
        ('nBlockAlign', c_short),
        ('wBitsPerSample', c_short),
        ('cbSize', c_short),
    ]


try:
    import comtypes
    from comtypes import GUID, IUnknown, COMMETHOD, HRESULT

    class IAudioCaptureClient(IUnknown):
        _iid_ = GUID('{C8ADBD64-E71E-48A0-A4DE-185C395CD317}')
        _methods_ = [
            COMMETHOD([], HRESULT, 'GetBuffer',
                      (['out'], POINTER(POINTER(ctypes.c_byte)), 'ppData'),
                      (['out'], POINTER(c_uint), 'pNumFramesToRead'),
                      (['out'], POINTER(c_ulong), 'pdwFlags'),
                      (['out'], POINTER(c_ulong), 'pu64DevicePosition'),
                      (['out'], POINTER(c_ulong), 'pu64QPCPosition')),
            COMMETHOD([], HRESULT, 'ReleaseBuffer',
                      (['in'], c_uint, 'NumFramesRead')),
            COMMETHOD([], HRESULT, 'GetNextPacketSize',
                      (['out'], POINTER(c_uint), 'pNumFramesInNextPacket')),
        ]

    class IAudioClient(IUnknown):
        _iid_ = GUID('{1CB9AD4C-DBFA-4c32-B178-C2F568A703B2}')
        _methods_ = [
            COMMETHOD([], HRESULT, 'Initialize',
                      (['in'], c_int, 'ShareMode'),
                      (['in'], c_ulong, 'StreamFlags'),
                      (['in'], c_ulong, 'hnsBufferDuration'),
                      (['in'], c_ulong, 'hnsPeriodicity'),
                      (['in'], POINTER(WAVEFORMATEX), 'pFormat'),
                      (['in'], c_void_p, 'AudioSessionGuid')),
            COMMETHOD([], HRESULT, 'GetBufferSize', (['out'], POINTER(c_uint), 'pNumBufferFrames')),
            COMMETHOD([], HRESULT, 'GetStreamLatency', (['out'], POINTER(c_ulong), 'phnsLatency')),
            COMMETHOD([], HRESULT, 'GetCurrentPadding', (['out'], POINTER(c_uint), 'pNumPaddingFrames')),
            COMMETHOD([], HRESULT, 'IsFormatSupported',
                      (['in'], c_int, 'ShareMode'),
                      (['in'], POINTER(WAVEFORMATEX), 'pFormat'),
                      (['out'], POINTER(POINTER(WAVEFORMATEX)), 'ppClosestMatch')),
            COMMETHOD([], HRESULT, 'GetMixFormat', (['out'], POINTER(POINTER(WAVEFORMATEX)), 'ppDeviceFormat')),
            COMMETHOD([], HRESULT, 'GetDevicePeriod',
                      (['out'], POINTER(c_ulong), 'phnsDefaultDevicePeriod'),
                      (['out'], POINTER(c_ulong), 'phnsMinimumDevicePeriod')),
            COMMETHOD([], HRESULT, 'Start'),
            COMMETHOD([], HRESULT, 'Stop'),
            COMMETHOD([], HRESULT, 'Reset'),
            COMMETHOD([], HRESULT, 'SetEventHandle', (['in'], wintypes.HANDLE, 'eventHandle')),
            COMMETHOD([], HRESULT, 'GetService',
                      (['in'], POINTER(GUID), 'riid'),
                      (['out'], POINTER(POINTER(IUnknown)), 'ppv')),
        ]

    class IMMDevice(IUnknown):
        _iid_ = GUID('{D666063F-1587-4E43-81F1-B948E807363F}')
        _methods_ = [
            COMMETHOD([], HRESULT, 'Activate',
                      (['in'], POINTER(GUID), 'iid'),
                      (['in'], wintypes.DWORD, 'dwClsCtx'),
                      (['in'], c_void_p, 'pActivationParams'),
                      (['out'], POINTER(POINTER(IAudioClient)), 'ppInterface')),
        ]

    class IMMDeviceEnumerator(IUnknown):
        _iid_ = GUID('{A95664D2-9614-4F35-A746-DE8DB63617E6}')
        _methods_ = [
            COMMETHOD([], HRESULT, 'EnumAudioEndpoints'),
            COMMETHOD([], HRESULT, 'GetDefaultAudioEndpoint',
                      (['in'], wintypes.DWORD, 'dataFlow'),
                      (['in'], wintypes.DWORD, 'role'),
                      (['out'], POINTER(POINTER(IMMDevice)), 'ppDevice')),
        ]

    WASAPI_COM_AVAILABLE = True
except Exception as e:
    logger.warning(f"WASAPI COM structures unavailable: {e}")
    WASAPI_COM_AVAILABLE = False


class RealtimeAudioSpectrumWorker(QObject):
    """
    Background worker thread capturing audio and computing 5-band spectrum.
    Emits spectrum_updated([b0, b1, b2, b3, b4]) values in range [6..34] pixels.
    """

    spectrum_updated = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._is_playing = False
        self._current_levels = np.array([6.0, 10.0, 8.0, 12.0, 6.0], dtype=np.float32)

    def set_playing(self, is_playing: bool):
        self._is_playing = is_playing

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.5)

    def _run_loop(self):
        if WASAPI_COM_AVAILABLE:
            try:
                comtypes.CoInitialize()
                self._run_wasapi_capture()
                comtypes.CoUninitialize()
                return
            except Exception as e:
                logger.debug(f"WASAPI loopback capture exception: {e}")

        # Fallback loop if WASAPI loopback is unavailable
        self._run_fallback_loop()

    def _run_wasapi_capture(self):
        CLSID_MMDeviceEnumerator = GUID('{BCDE0395-E52F-467C-8E3D-C4579291692E}')
        enumerator = comtypes.CoCreateInstance(CLSID_MMDeviceEnumerator, IMMDeviceEnumerator, comtypes.CLSCTX_INPROC_SERVER)
        device = enumerator.GetDefaultAudioEndpoint(0, 0)  # eRender, eConsole
        audio_client = device.Activate(byref(IAudioClient._iid_), 23, None)
        mix_format = audio_client.GetMixFormat()

        n_channels = max(1, int(mix_format.contents.nChannels))
        sample_rate = max(8000, int(mix_format.contents.nSamplesPerSec))
        bits_per_sample = int(mix_format.contents.wBitsPerSample)

        # AUDCLNT_STREAMFLAGS_LOOPBACK = 0x00020000
        AUDCLNT_STREAMFLAGS_LOOPBACK = 0x00020000
        audio_client.Initialize(0, AUDCLNT_STREAMFLAGS_LOOPBACK, 10000000, 0, mix_format, None)
        capture_client_p = audio_client.GetService(byref(IAudioCaptureClient._iid_))
        capture_client = capture_client_p.QueryInterface(IAudioCaptureClient)
        audio_client.Start()

        buffer_list = []
        last_emit_time = time.time()

        while self._running:
            try:
                packet_size = capture_client.GetNextPacketSize()
                while packet_size > 0:
                    p_data, num_frames, flags, dev_pos, qpc_pos = capture_client.GetBuffer()
                    if num_frames > 0 and p_data:
                        byte_count = num_frames * n_channels * (bits_per_sample // 8)
                        raw = ctypes.string_at(p_data, byte_count)
                        if bits_per_sample == 32:
                            samples = np.frombuffer(raw, dtype=np.float32)
                            # Convert stereo/multichannel to mono
                            if n_channels > 1:
                                samples = samples.reshape(-1, n_channels).mean(axis=1)
                            buffer_list.append(samples)
                        elif bits_per_sample == 16:
                            samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
                            if n_channels > 1:
                                samples = samples.reshape(-1, n_channels).mean(axis=1)
                            buffer_list.append(samples)

                    capture_client.ReleaseBuffer(num_frames)
                    packet_size = capture_client.GetNextPacketSize()

                now = time.time()
                # Process spectrum at ~33 FPS (every 30ms)
                if now - last_emit_time >= 0.030:
                    last_emit_time = now
                    if buffer_list:
                        full_audio = np.concatenate(buffer_list)
                        buffer_list.clear()
                        # Keep recent 1024 or 2048 samples
                        if len(full_audio) > 2048:
                            full_audio = full_audio[-2048:]
                        self._process_audio_frame(full_audio, sample_rate)
                    else:
                        # Decay towards resting
                        self._apply_decay()

                time.sleep(0.010)
            except Exception as loop_err:
                logger.debug(f"Audio capture loop error: {loop_err}")
                time.sleep(0.05)

        try:
            audio_client.Stop()
        except Exception:
            pass

    def _process_audio_frame(self, audio: np.ndarray, sample_rate: int):
        if len(audio) < 128:
            self._apply_decay()
            return

        # Fast FFT
        window = np.hanning(len(audio))
        fft_vals = np.abs(np.fft.rfft(audio * window))
        freqs = np.fft.rfftfreq(len(audio), 1.0 / sample_rate)

        # 5 frequency bands: Sub-bass, Bass/Low-mid, Mid, High-mid, Treble
        bands = [
            (30, 160),     # Sub-bass / Kick
            (160, 500),    # Bass / Drums
            (500, 2000),   # Mid / Vocals
            (2000, 6000),  # High-mid / Guitars & Synths
            (6000, 16000)  # Treble / Cymbals
        ]

        raw_targets = []
        for low_f, high_f in bands:
            idx = np.where((freqs >= low_f) & (freqs < high_f))[0]
            if len(idx) > 0:
                mag = np.mean(fft_vals[idx])
                # Log-scale magnitude to pixel heights [6..34]
                height = 6.0 + min(28.0, np.log1p(mag * 30.0) * 8.5)
            else:
                height = 6.0
            raw_targets.append(height)

        target_arr = np.array(raw_targets, dtype=np.float32)

        # Smooth physics: Fast attack, smooth release decay
        for i in range(5):
            if target_arr[i] > self._current_levels[i]:
                # Attack
                self._current_levels[i] = self._current_levels[i] * 0.4 + target_arr[i] * 0.6
            else:
                # Decay
                self._current_levels[i] = max(6.0, self._current_levels[i] * 0.85)

        self.spectrum_updated.emit([int(v) for v in self._current_levels])

    def _apply_decay(self):
        resting = np.array([6.0, 10.0, 8.0, 12.0, 6.0], dtype=np.float32)
        if not self._is_playing:
            self._current_levels = self._current_levels * 0.8 + resting * 0.2
        else:
            # Subtle resting wave when paused / quiet
            self._current_levels = self._current_levels * 0.9 + resting * 0.1
        self.spectrum_updated.emit([int(v) for v in self._current_levels])

    def _run_fallback_loop(self):
        """Dynamic pulse rhythm when WASAPI loopback is unavailable."""
        phase = 0.0
        while self._running:
            if self._is_playing:
                phase += 0.3
                b0 = int(12 + 14 * (np.sin(phase) + 1) * 0.5)
                b1 = int(10 + 18 * (np.sin(phase + 1.2) + 1) * 0.5)
                b2 = int(14 + 16 * (np.sin(phase + 2.4) + 1) * 0.5)
                b3 = int(16 + 18 * (np.sin(phase + 3.6) + 1) * 0.5)
                b4 = int(8 + 12 * (np.sin(phase + 4.8) + 1) * 0.5)
                self.spectrum_updated.emit([b0, b1, b2, b3, b4])
            else:
                self.spectrum_updated.emit([6, 10, 8, 12, 6])
            time.sleep(0.040)
