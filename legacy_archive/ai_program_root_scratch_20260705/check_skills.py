import os
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

skills_dir = r"<LOCAL_USER_HOME>\.gemini\antigravity\skills"

def parse_frontmatter(content):
    lines = content.split('\n')
    fm = {}
    if len(lines) > 0 and lines[0].strip() == '---':
        fm_lines = []
        for line in lines[1:]:
            if line.strip() == '---':
                break
            fm_lines.append(line)
        for line in fm_lines:
            if ':' in line:
                key, val = line.split(':', 1)
                fm[key.strip()] = val.strip().strip('"').strip("'")
    return fm

def main():
    if not os.path.exists(skills_dir):
        print(f"Error: Skills directory {skills_dir} does not exist.")
        return
        
    items = os.listdir(skills_dir)
    results = []
    
    for item in items:
        full_path = os.path.join(skills_dir, item)
        is_dir = os.path.isdir(full_path)
        
        files = []
        try:
            files = os.listdir(full_path)
            has_skill_md = "SKILL.md" in files
        except Exception as e:
            has_skill_md = False
            files = []
            
        skill_md_status = "N/A"
        name = "N/A"
        desc = "N/A"
        size = 0
        
        if has_skill_md:
            skill_md_path = os.path.join(full_path, "SKILL.md")
            try:
                size = os.path.getsize(skill_md_path)
                with open(skill_md_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                fm = parse_frontmatter(content)
                name = fm.get('name', item)
                desc = fm.get('description', 'No description found')
                skill_md_status = "Readable"
            except Exception as e:
                skill_md_status = f"Read Error: {str(e)}"
        else:
            if files:
                skill_md_status = "No SKILL.md (Files: " + ", ".join(files[:3]) + ")"
            else:
                skill_md_status = "Empty / Unreadable folder"
                
        results.append({
            "item_name": item,
            "is_dir": is_dir,
            "has_skill_md": has_skill_md,
            "skill_md_status": skill_md_status,
            "name": name,
            "description": desc,
            "size_bytes": size,
            "files_count": len(files)
        })
        
    print(f"## 📋 技能物理可用性校验报告 (共 {len(results)} 个项)")
    print("\n| # | 技能目录项 | 物理类型 | SKILL.md状态 | Frontmatter 名称 | 字节大小 | 包含文件数 |")
    print("|---|---|---|---|---|---|---|")
    for idx, r in enumerate(results, 1):
        type_str = "目录" if r["is_dir"] else "文件"
        print(f"| {idx} | {r['item_name']} | {type_str} | {r['skill_md_status']} | {r['name']} | {r['size_bytes']} | {r['files_count']} |")

if __name__ == "__main__":
    main()
