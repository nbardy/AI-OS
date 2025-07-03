import base64, os, re
import ai_os.core.macro_helpers as ah
from ai_os.core.models import Message, TextContent, ImageContent
from ai_os.core.chat import chat_completion

def main(ctx, **kwargs):
    prompt = kwargs.get('prompt', 'Create a bar chart showing quarterly sales growth')
    
    # Generate chart code
    code_prompt = f"Write Python code to: {prompt}. Use matplotlib. Save as 'chart.png'. Just the code, no explanation."
    msgs = [Message(role="user", content=code_prompt)]
    code = ""
    for chunk in chat_completion(msgs, "anthropic/claude-3-haiku"):
        code += chunk
    
    # Clean and save code
    code = code.strip().replace("```python", "").replace("```", "").strip()
    with open("chart_gen.py", "w") as f:
        f.write(code)
    
    # Run it
    ah.shell("python chart_gen.py")
    
    # Read chart and judge
    with open("chart.png", "rb") as f:
        chart_b64 = base64.b64encode(f.read()).decode()
    
    judge_msg = Message(role="user", content=[
        TextContent(type="text", text=f"Rate 1-10 how well this chart matches the request: '{prompt}'. Just the number."),
        ImageContent(type="image_url", image_url={"url": f"data:image/png;base64,{chart_b64}"})
    ])
    
    response = ""
    for chunk in chat_completion([judge_msg], "anthropic/claude-3-haiku"):
        response += chunk
    
    score = re.search(r'\b([1-9]|10)\b', response)
    ah.log(f"📊 Chart: {os.path.abspath('chart.png')}")
    ah.log(f"📝 Code: {os.path.abspath('chart_gen.py')}")
    ah.log(f"🎯 Adherence: {score.group(0)}/10" if score else f"Judge: {response.strip()}")