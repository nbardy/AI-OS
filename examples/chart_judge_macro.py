#!/usr/bin/env python3
"""Dense macro: Draw chart → VLLM judges quality"""

import matplotlib.pyplot as plt
import numpy as np
import base64
from io import BytesIO
from ai_os.core.models import Message, TextContent, ImageContent
from ai_os.core.chat import chat_completion

# 1. Generate & save chart
def draw_chart():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    
    # Sales trend
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May']
    sales = [120, 135, 125, 145, 160]
    ax1.plot(months, sales, 'bo-', linewidth=2, markersize=8)
    ax1.set_title('Q1 Sales Trend', fontsize=14, fontweight='bold')
    ax1.set_ylabel('Sales ($k)')
    ax1.grid(True, alpha=0.3)
    
    # Market share
    companies = ['Us', 'CompA', 'CompB', 'Other']
    shares = [35, 25, 20, 20]
    colors = ['#2ecc71', '#3498db', '#e74c3c', '#95a5a6']
    ax2.pie(shares, labels=companies, colors=colors, autopct='%1.1f%%', startangle=90)
    ax2.set_title('Market Share', fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    
    # Save to base64
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    plt.close()
    
    return base64.b64encode(buf.getvalue()).decode('utf-8')

# 2. VLLM as judge
def judge_chart(chart_b64):
    messages = [
        Message(
            role="user",
            content=[
                TextContent(type="text", text="Rate this business chart (1-10) on: clarity, professionalism, and insight value. Be critical."),
                ImageContent(type="image_url", image_url={"url": f"data:image/png;base64,{chart_b64}"})
            ]
        )
    ]
    
    print("📊 Chart created. VLLM Judge says:\n")
    
    # Use a vision-capable model for judging
    for chunk in chat_completion(messages, model="openai/gpt-4-vision-preview"):
        print(chunk, end='', flush=True)

# Run macro
if __name__ == "__main__":
    chart_b64 = draw_chart()
    judge_chart(chart_b64)