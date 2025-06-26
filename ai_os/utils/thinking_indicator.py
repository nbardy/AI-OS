import threading
import time
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.animations.wave import make_frame, TOTAL_LEN

class ThinkingIndicator:
    """Displays a thinking animation with emoji, wave, and elapsed time."""
    
    def __init__(self, console=None):
        self.console = console
        self.running = False
        self.thread = None
        self.start_time = None
        
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
        sys.stdout.write('\r' + ' ' * (TOTAL_LEN + 25) + '\r')
        sys.stdout.flush()
        
        return elapsed
        
    def _run(self):
        """Run the animation loop."""
        frame_no = 0
        phase = 0.0
        
        try:
            while self.running:
                elapsed = int(time.time() - self.start_time)
                wave = make_frame(frame_no, phase)
                
                # Format: 🤔 💭 [wave animation] [Xs]
                display = f"🤔 💭 {wave} [{elapsed}s]"
                
                sys.stdout.write('\r' + display)
                sys.stdout.flush()
                
                phase += 0.15
                frame_no += 1
                time.sleep(0.09)
                
        except Exception:
            # Silently handle any display errors
            pass