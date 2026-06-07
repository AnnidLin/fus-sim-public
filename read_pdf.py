import urllib.request
import json
import base64
import sys
import os

try:
    import pypdf
except ImportError:
    print("pypdf not installed. Please run: pip install pypdf")
    sys.exit(1)

def extract_pdf_text(filepath):
    try:
        reader = pypdf.PdfReader(filepath)
        text = ""
        # Extract first 5 pages for the abstract and intro
        for i, page in enumerate(reader.pages[:10]):
            text += f"--- Page {i+1} ---\n"
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        return f"Error: {e}"

if __name__ == "__main__":
    filepath = r"d:\杭州医学院\科研项目\经颅聚焦超声联合微泡开放血脑屏障的数值仿真研究_潘婷.pdf"
    print(extract_pdf_text(filepath))
