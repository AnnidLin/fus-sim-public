import sys
from pathlib import Path

try:
    import pypdf
except ImportError:
    print("pypdf not installed. Installing standard requirements...")
    sys.exit(1)

def extract_pdf_text(filepath, max_pages=15):
    try:
        reader = pypdf.PdfReader(filepath)
        text = ""
        # Extract first max_pages pages for scanning
        for i, page in enumerate(reader.pages[:max_pages]):
            text += f"--- Page {i+1} ---\n"
            content = page.extract_text()
            if content:
                text += content + "\n"
        return text
    except Exception as e:
        return f"Error: {e}"

def search_keywords(text, keywords):
    matches = {}
    lines = text.split("\n")
    for kw in keywords:
        matches[kw] = []
        for line in lines:
            if kw.lower() in line.lower():
                matches[kw].append(line.strip())
    return matches

def main():
    pdf_files = [
        "经颅聚焦超声治疗脑血栓的数值仿真研究_孙天宇.pdf",
        "经颅聚焦超声联合微泡开放血脑屏障的数值仿真研究_潘婷.pdf",
        "经颅聚焦超声调控系统的参数仿真研究_高鹏皓.pdf"
    ]
    
    keywords = [
        "换能器", "焦距", "孔径", "频率", "声强", "温升", "声压", "网格", "步长", 
        "transducer", "frequency", "aperture", "focal", "k-wave", "pennes"
    ]
    
    output_dir = Path("outputs/literature_pdf_summary")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for pdf in pdf_files:
        pdf_path = Path(pdf)
        if not pdf_path.exists():
            print(f"Skipping {pdf}: not found")
            continue
            
        print(f"Processing {pdf}...")
        text = extract_pdf_text(pdf_path, max_pages=30)
        
        # Write full extracted text first
        txt_out = output_dir / f"{pdf_path.stem}_text.txt"
        txt_out.write_text(text, encoding="utf-8")
        
        # Search keywords
        matches = search_keywords(text, keywords)
        
        summary_out = output_dir / f"{pdf_path.stem}_keywords.json"
        import json
        summary_out.write_text(json.dumps(matches, ensure_ascii=False, indent=2), encoding="utf-8")
        
        print(f"Saved text to {txt_out} and keywords to {summary_out}")

if __name__ == "__main__":
    main()
