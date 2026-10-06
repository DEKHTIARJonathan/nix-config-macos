"""Convert curl's progress meter into structured Nix build-phase updates."""

import json
import os
import re
import subprocess
import sys
import time


PERCENT = re.compile(rb"[ #]*([0-9]+(?:\.[0-9]+)?)%")


class Progress:
    def __init__(self, output, clock=time.monotonic):
        self.output = output
        self.clock = clock
        self.pending = b""
        self.last_phase = None
        self.last_time = float("-inf")
        self.last_percent = None

    def line(self, line, ending=b"\n"):
        text = line.strip()
        match = PERCENT.fullmatch(text)
        if match:
            percent = float(match[1])
            phase = f"download {percent:.1f}%"
        elif text and set(text) <= set(b" #-=oO"):
            percent = None
            phase = "downloading (size unknown)"
        else:
            # Errors and other curl diagnostics retain their contents. Empty
            # redraw separators contain no information and are discarded.
            if line:
                self.output.write(line + ending)
                self.output.flush()
            return
        now = self.clock()
        restarted = percent is not None and self.last_percent is not None and percent < self.last_percent
        if phase != self.last_phase and (now - self.last_time >= 0.5 or percent == 100 or restarted):
            event = {"action": "setPhase", "phase": phase}
            self.output.write(b"@nix " + json.dumps(event).encode() + b"\n")
            self.output.flush()
            self.last_phase, self.last_time = phase, now
        self.last_percent = percent

    def feed(self, chunk):
        self.pending += chunk
        lines = re.split(rb"[\r\n]", self.pending)
        self.pending = lines.pop()
        for line in lines:
            self.line(line)

    def finish(self):
        if self.pending:
            self.line(self.pending, ending=b"")
            self.pending = b""


def main():
    # stdout (including curl -V and downloaded data) remains inherited.
    progress = Progress(sys.stderr.buffer)
    with subprocess.Popen(sys.argv[1:], stderr=subprocess.PIPE) as process:
        while True:
            chunk = os.read(process.stderr.fileno(), 4096)
            if not chunk:
                break
            progress.feed(chunk)
        progress.finish()
        status = process.wait()
    return status if status >= 0 else 128 - status


if __name__ == "__main__":
    raise SystemExit(main())
