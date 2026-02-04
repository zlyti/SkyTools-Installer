
import os
import sys

def patch_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        new_content = content.replace("https://files.luatools.work/GameBypasses/", "https://github.com/madoiscool/lt_api_links/releases/download/unsteam/")
        new_content = new_content.replace("https://files.luatools.work/OnlineFix1/", "https://github.com/madoiscool/lt_api_links/releases/download/unsteam/")

        if content != new_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Patched: {file_path}")
        else:
            print(f"Skipped (already patched or not found): {file_path}")

    except Exception as e:
        print(f"Error patching {file_path}: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_dir = sys.argv[1]
        for root, dirs, files in os.walk(target_dir):
            for file in files:
                if file.endswith("fixes.py"):
                    patch_file(os.path.join(root, file))
