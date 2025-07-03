import threading
import time
import sys
import os
import math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.animations.wave import make_frame, TOTAL_LEN, BASE_WAVE, WAVE_WIDTH, LEFT_POSES, RIGHT_POSES, SIDE_LEN

class ThinkingIndicator:
    """Displays a thinking animation with emoji, wave, and elapsed time."""
    
    def __init__(self, console=None):
        self.console = console
        self.running = False
        self.thread = None
        self.start_time = None
        self.use_rich = console is not None
        
    def start(self):
        """Start the thinking animation in a background thread."""
        self.running = True
        self.start_time = time.time()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        
    def stop(self):
        """Stop the animation and return elapsed time."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=0.5)  # Don't wait forever
        elapsed = time.time() - self.start_time if self.start_time else 0
        
        # Clear the animation line
        if self.use_rich and self.console:
            self.console.print(' ' * (TOTAL_LEN + 25), end='\r')
        else:
            sys.stdout.write('\r' + ' ' * (TOTAL_LEN + 25) + '\r')
            sys.stdout.flush()
        
        return elapsed
        
    def _make_rich_wave(self, offset: int) -> str:
        """Create a wave slice with Rich color markup instead of ANSI codes."""
        # Repeat wave pattern enough times
        wave_str = BASE_WAVE * ((WAVE_WIDTH // len(BASE_WAVE)) + 4)
        # Extract slice
        slice_ = (wave_str + wave_str)[offset:offset + WAVE_WIDTH]
        # Apply alternating colors using Rich markup
        result = ''
        for i, ch in enumerate(slice_):
            color = 'cyan' if (i + offset) % 2 else 'blue'
            result += f'[{color}]{ch}[/{color}]'
        return result
    
    def _run(self):
        """Run the animation loop."""
        frame_no = 0
        phase = 0.0
        
        try:
            while self.running:
                elapsed = int(time.time() - self.start_time)
                
                if self.use_rich and self.console:
                    # Use Rich-compatible formatting
                    left = LEFT_POSES[(frame_no // 8) % 2]
                    right = RIGHT_POSES[((frame_no // 8) + 1) % 2]
                    max_shift = len(BASE_WAVE)
                    offset = int((math.sin(phase) + 1) / 2 * max_shift)
                    wave = self._make_rich_wave(offset)
                    
                    # Format: 🤔 💭 [wave animation] [Xs]
                    display = f"🤔 💭 {left}{wave}{right} [{elapsed}s]"
                    self.console.print(display, end='\r')
                else:
                    # Use original ANSI code version
                    wave = make_frame(frame_no, phase)
                    display = f"🤔 💭 {wave} [{elapsed}s]"
                    sys.stdout.write('\r' + display)
                    sys.stdout.flush()
                
                phase += 0.15
                frame_no += 1
                time.sleep(0.09)
                
        except Exception:
            # Silently handle any display errors
            pass