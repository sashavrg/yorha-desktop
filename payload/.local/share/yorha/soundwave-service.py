#!/usr/bin/python3
"""One output-monitor analyser shared by the desktop widget and both Waybars."""
import fcntl
import os
import selectors
import signal
import subprocess
import time
from pathlib import Path

from soundwave_hud import BANDS, IMAGE, RUNTIME, SIGNAL, atomic_state, palette, png

running = True


def stop(*_args):
    global running
    running = False


def waybar_pids():
    """Only notify a Waybar that has installed the real-time signal handler."""
    found = []
    mask = 1 << (signal.SIGRTMIN + SIGNAL - 1)
    for entry in Path('/proc').iterdir():
        if not entry.name.isdecimal():
            continue
        try:
            if entry.stat().st_uid != os.getuid() or (entry / 'comm').read_text().strip() != 'waybar':
                continue
            status = (entry / 'status').read_text()
            caught = next(line.split()[1] for line in status.splitlines() if line.startswith('SigCgt:'))
            if int(caught, 16) & mask:
                found.append(int(entry.name))
        except (OSError, StopIteration, ValueError):
            continue
    return found


def notify(pids):
    for pid in pids:
        try:
            # Recheck identity before signalling a cached pid.
            if (Path('/proc') / str(pid) / 'comm').read_text().strip() == 'waybar':
                os.kill(pid, signal.SIGRTMIN + SIGNAL)
        except (OSError, ProcessLookupError):
            pass


def default_sink():
    try:
        result = subprocess.run(['pactl', 'get-default-sink'], capture_output=True,
                                text=True, timeout=.5)
        return result.stdout.strip() if result.returncode == 0 else ''
    except (OSError, subprocess.TimeoutExpired):
        return ''


def main():
    RUNTIME.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (RUNTIME / 'service.lock').open('w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        # Cava resolves the default output monitor on connection, never the microphone.
        config = f'''[general]
framerate = 20
autosens = 1
sensitivity = 100
bars = {BANDS}
lower_cutoff_freq = 55
higher_cutoff_freq = 12000
sleep_timer = 0
[input]
method = pulse
source = auto
[output]
method = raw
channels = mono
mono_option = average
raw_target = /dev/stdout
data_format = ascii
ascii_max_range = 1000
bar_delimiter = 59
frame_delimiter = 10
[smoothing]
noise_reduction = 65
'''
        config_path = RUNTIME / 'cava.conf'
        config_path.write_text(config)
        zeros = [0.] * BANDS
        levels = zeros[:]
        selected = palette()
        atomic_state(levels, selected, False)
        png(IMAGE, levels, selected)
        pids = waybar_pids()
        notify(pids)
        child = None
        last_frame = last_state = time.monotonic()
        last_check = 0.
        last_route_check = 0.
        sink = default_sink()
        signature = None
        pending = b''
        selector = selectors.DefaultSelector()
        try:
            while running:
                if child is None or child.poll() is not None:
                    if child is not None:
                        selector.unregister(child.stdout)
                        child.stdout.close()
                    child = subprocess.Popen(['/usr/bin/cava', '-p', str(config_path)],
                                             stdout=subprocess.PIPE)
                    os.set_blocking(child.stdout.fileno(), False)
                    selector.register(child.stdout, selectors.EVENT_READ)
                    pending = b''
                    last_frame = time.monotonic()
                for key, _mask in selector.select(timeout=.05):
                    chunk = os.read(key.fd, 65536)
                    pending += chunk
                    if len(pending) > 65536:
                        pending = b''
                    while b'\n' in pending:
                        line, pending = pending.split(b'\n', 1)
                        try:
                            values = [int(v) for v in line.rstrip(b';').split(b';')]
                        except ValueError:
                            continue
                        if len(values) != BANDS:
                            continue
                        # A small attack/release smooths movement without inventing audio.
                        target = [max(0., min(1., v / 1000)) for v in values]
                        levels = [a + (b - a) * (.8 if b > a else .45) for a, b in zip(levels, target)]
                        levels = [0. if value < .002 else round(value, 3) for value in levels]
                        last_frame = time.monotonic()
                now = time.monotonic()
                connected = child.poll() is None and now - last_frame < 2
                if not connected:
                    levels = zeros[:]
                if now - last_check >= 1:
                    selected = palette()
                    discovered = waybar_pids()
                    if discovered != pids:
                        pids = discovered
                        signature = None
                    last_check = now
                if now - last_route_check >= 2:
                    current_sink = default_sink()
                    if sink and current_sink and current_sink != sink:
                        # Reconnect to the new output monitor without moving or
                        # interrupting any playback stream.
                        if child.poll() is None:
                            child.terminate()
                    if current_sink:
                        sink = current_sink
                    last_route_check = now
                current = (selected, tuple(round(v * 20) for v in levels))
                if current != signature:
                    png(IMAGE, levels, selected)
                    atomic_state(levels, selected, connected)
                    last_state = now
                    signature = current
                    notify(pids)
                elif now - last_state >= 1:
                    atomic_state(levels, selected, connected)
                    last_state = now
                # Avoid a spin/restart loop if the audio server is unavailable.
                if child.poll() is not None:
                    time.sleep(.5)
        finally:
            if child is not None:
                if child.poll() is None:
                    child.terminate()
                    try:
                        child.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        child.kill()
                        child.wait()
                child.stdout.close()
            selector.close()
            atomic_state(zeros, selected, False)
            png(IMAGE, zeros, selected)
            notify(pids)
            config_path.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
