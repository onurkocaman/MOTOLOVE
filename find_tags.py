import re

def find_multiline_jinja(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Regex for {{ ... }} with newline inside
    # We use non-greedy match .*? and DOTALL is not set, so . doesn't match newline.
    # But we want to find {{ followed by anything including newline followed by }}
    
    # Pattern: {{ [^}]*\n[^}]* }} roughly
    # Better: {{ (anything that contains \n) }}
    
    pattern = re.compile(r'(\{\{.*?\}\}|{% .*? %})', re.DOTALL)
    
    matches = pattern.finditer(content)
    
    found = False
    for m in matches:
        text = m.group(1)
        if '\n' in text:
            line_no = content[:m.start()].count('\n') + 1
            print(f"Found multiline tag at line {line_no}:")
            print(f"---\n{text}\n---")
            found = True
            
    if not found:
        print("No multiline tags found.")

if __name__ == "__main__":
    find_multiline_jinja('ihale.html')
