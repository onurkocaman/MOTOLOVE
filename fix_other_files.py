
import os

def fix_all():
    base = r'c:\Users\HP\OneDrive\Masaüstü\moto'
    
    # 1. Fix ilan_detay.html
    path_ia = os.path.join(base, 'ilan_detay.html')
    with open(path_ia, 'r', encoding='utf-8') as f:
        content = f.read()

    broken_ia = """                const isLoggedIn = {{ (user_id is not none) | tojson
        }};"""
    fixed_ia = """                const isLoggedIn = {{ (user_id is not none) | tojson }};"""

    if broken_ia in content:
        content = content.replace(broken_ia, fixed_ia)
        with open(path_ia, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Fixed ilan_detay.html")
    else:
        print("ilan_detay.html already clean or pattern not found.")

    # 2. Fix mesajlarim.html
    path_msg = os.path.join(base, 'mesajlarim.html')
    with open(path_msg, 'r', encoding='utf-8') as f:
        content = f.read()

    broken_msg = """            const currentUserId = {{ user_id | tojson
        }};"""
    fixed_msg = """            const currentUserId = {{ user_id | tojson }};"""

    if broken_msg in content:
        content = content.replace(broken_msg, fixed_msg)
        with open(path_msg, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Fixed mesajlarim.html")
    else:
        print("mesajlarim.html already clean or pattern not found.")

if __name__ == "__main__":
    fix_all()
