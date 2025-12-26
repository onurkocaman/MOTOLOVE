
import os

def fix_file():
    path = r'c:\Users\HP\OneDrive\Masaüstü\moto\ilan.html'
    
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Define the broken patterns exactly as seen in view_file output
    # Pattern 1
    broken_1 = """                    const currentUserId = {{ user_id | tojson
                }
            };"""
    fixed_1 = """                    const currentUserId = {{ user_id | tojson }};"""
    
    # Pattern 2
    broken_2 = """            const currentUserId = {{ user_id | tojson
        }};"""
    fixed_2 = """            const currentUserId = {{ user_id | tojson }};"""
    
    new_content = content.replace(broken_1, fixed_1).replace(broken_2, fixed_2)
    
    if content == new_content:
        print("No changes needed or patterns not found.")
        # Debug: print snippet around expected location
        idx = content.find("const currentUserId = {{ user_id | tojson")
        if idx != -1:
            print("Found partial match at:", idx)
            print(content[idx:idx+100])
    else:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Successfully fixed ilan.html")

if __name__ == "__main__":
    fix_file()
