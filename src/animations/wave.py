import math
import time
import sys

# ── ANSI color codes ────────────────────────────────────────────────────────────
RESET = '\033[0m'
BLUE  = '\033[94m'
CYAN  = '\033[96m'

# ── Wave pattern (Subtle Ocean Swell) ───────────────────────────────────────────
BASE_WAVE   = ".¸¸.·´¯`·.¸¸"                 # 14 chars
WAVE_WIDTH  = 40
# Repeat enough times so any slice of length WAVE_WIDTH is always available
WAVE_STR    = BASE_WAVE * ((WAVE_WIDTH // len(BASE_WAVE)) + 4)

# ── Characters (fat-arms, always facing inward) ────────────────────────────────
LEFT_POSES  = ['╭(˘ω˘)╮', '╰(˘ω˘)╯']   # up / down
RIGHT_POSES = ['╭(˘ω˘)╮', '╰(˘ω˘)╯']   # mirrored, same glyph

SIDE_LEN    = len(LEFT_POSES[0])
TOTAL_LEN   = SIDE_LEN * 2 + WAVE_WIDTH     # constant output length

# ── Helper: build one colored wave slice given a horizontal offset ─────────────
def colored_wave(offset: int) -> str:
    # extract slice; wrap by doubling string
    slice_ = (WAVE_STR + WAVE_STR)[offset:offset + WAVE_WIDTH]
    # apply alternating colors
    return ''.join(
        (CYAN if (i + offset) % 2 else BLUE) + ch + RESET
        for i, ch in enumerate(slice_)
    )

# ── Build one animation frame ──────────────────────────────────────────────────
def make_frame(frame_no: int, phase: float) -> str:
    # half-cycle-offset arm motion (left & right opposite states)
    left  = LEFT_POSES[(frame_no // 8) % 2]
    right = RIGHT_POSES[((frame_no // 8) + 1) % 2]  # ½-cycle shifted

    # horizontal offset oscillates via sine → smooth back-and-forth
    max_shift = len(BASE_WAVE)                      # travel range
    offset    = int((math.sin(phase) + 1) / 2 * max_shift)

    wave  = colored_wave(offset)
    frame = f"{left}{wave}{right}"
    return frame.ljust(TOTAL_LEN)                   # pad for safety

# ── Animation loop ──────────────────────────────────────────────────────────────
def animate(speed: float = 0.09):
    phase, frame_no = 0.0, 0
    try:
        while True:
            sys.stdout.write('\r' + make_frame(frame_no, phase))
            sys.stdout.flush()

            phase    += 0.15   # controls oscillation speed
            frame_no += 1
            time.sleep(speed)
    except KeyboardInterrupt:
        sys.stdout.write('\n╰(˘ω˘)╯  Ocean-thoughts concluded  ╭(˘ω˘)╮\n')

if __name__ == "__main__":
    animate(speed=0.11)

