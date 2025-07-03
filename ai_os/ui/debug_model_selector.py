from textual.app import App
from textual.widgets import Static

class DebugModelSelector(App):
    """Minimal test to see if we can get ANY text to show"""
    
    def compose(self):
        yield Static("THIS IS A TEST - CAN YOU SEE THIS TEXT?", id="test1")
        yield Static("Second line of text", id="test2")
        yield Static("Third line with different styling", id="test3")

def test_text_visibility():
    app = DebugModelSelector()
    app.run()

if __name__ == "__main__":
    test_text_visibility()