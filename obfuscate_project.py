import os
import shutil
import base64
import random
import string

def obfuscate_file(filepath):
    """
    Simple obfuscation: Reads file, base64 encodes it, and wraps it in an exec() decoder.
    This is basic protection to prevent casual reading.
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Encode content to base64
    encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')

    # Create the loader script
    # It decodes the base64 string and executes it
    loader_code = f"""
import base64
exec(base64.b64decode("{encoded}").decode("utf-8"))
"""
    return loader_code

def main():
    source_dir = "src"
    dist_dir = "dist_obfuscated/src"

    # Clean previous build
    if os.path.exists("dist_obfuscated"):
        shutil.rmtree("dist_obfuscated")
    
    os.makedirs(dist_dir)

    print(f"🔒 Obfuscating {source_dir} -> {dist_dir}...")

    # Copy and obfuscate files
    for root, dirs, files in os.walk(source_dir):
        # Create corresponding directory in dist
        rel_path = os.path.relpath(root, source_dir)
        target_dir = os.path.join(dist_dir, rel_path)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

        for file in files:
            if file.endswith(".py") and file != "__init__.py":
                # Obfuscate Python files
                src_file = os.path.join(root, file)
                dst_file = os.path.join(target_dir, file)
                print(f"   Hidden: {file}")
                
                obfuscated_content = obfuscate_file(src_file)
                with open(dst_file, 'w', encoding='utf-8') as f:
                    f.write(obfuscated_content)
            else:
                # Copy other files as-is (e.g., config, assets)
                src_file = os.path.join(root, file)
                dst_file = os.path.join(target_dir, file)
                shutil.copy2(src_file, dst_file)
    
    # Copy root files needed for distribution
    files_to_copy = ["install_SkyTools.ps1", "README.md", "requirements.txt"]
    for f in files_to_copy:
        if os.path.exists(f):
             shutil.copy2(f, f"dist_obfuscated/{f}")

    print("\n✅ Obfuscation Complete!")
    print(f"📁 Protected version is in: {os.path.abspath('dist_obfuscated')}")
    print("\n👉 To release: Zip the contents of 'dist_obfuscated' and upload to GitHub Releases.")

if __name__ == "__main__":
    main()
