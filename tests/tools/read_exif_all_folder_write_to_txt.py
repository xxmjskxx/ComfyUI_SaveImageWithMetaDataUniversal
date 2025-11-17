from PIL import Image, UnidentifiedImageError
from PIL.ExifTags import TAGS, GPSTAGS
import sys
import os
import argparse

def decode_user_comment(user_comment):
    try:
        # Decode the byte string as UTF-16 big-endian with backslash replacement
        decoded_comment = user_comment.decode('utf-16be', 'backslashreplace')
        return decoded_comment
    except UnicodeDecodeError:
        # If decoding fails, return the original byte string
        return user_comment

def get_exif_data(image_path: str) -> str:
    """Return metadata string for the image (EXIF UserComment or PNG parameters)."""
    lines: list[str] = []
    try:
        with Image.open(image_path) as image:
            # EXIF path (JPEG/WebP/etc.)
            if hasattr(image, '_getexif') and image._getexif() is not None:
                try:
                    exif_data = image._getexif()
                    for tag, value in exif_data.items():
                        tag_name = TAGS.get(tag, tag)
                        if tag_name == 'UserComment':
                            value = decode_user_comment(value)
                            # EXIF UserComment may start with an encoding marker/BOM; trim the first
                            # four bytes to drop that prefix and match the original script's behavior.
                            if len(value) >= 4:
                                value = value[4:]
                            lines.append(str(value))
                    if 'GPSInfo' in exif_data:
                        for tag, value in exif_data['GPSInfo'].items():
                            tag_name = GPSTAGS.get(tag, tag)
                            lines.append(f"GPS {tag_name}: {value}")
                except (KeyError, TypeError, ValueError) as e:
                    lines.append(f"Error reading EXIF: {e}")
            # PNG path
            elif image_path.lower().endswith('.png'):
                png_info = image.info
                # If structured tEXt chunks accessible via Pillow
                if png_info and 'tEXt' in png_info:
                    try:
                        for key, value in png_info['tEXt']:
                            lines.append(f"tEXt {key}: {value}")
                    except (KeyError, ValueError) as e:
                        lines.append(f"Error reading tEXt chunks: {e}")
                else:
                    # Fallback: raw binary search between markers (keep original ordering; do NOT move Hashes)
                    try:
                        with open(image_path, 'rb') as f:
                            binary_content = f.read()
                        start_index = binary_content.find(b'parameters')
                        near_end_index = binary_content.find(b'Hashes: ')
                        end_index = binary_content.find(b'tEXt', near_end_index) - 9 if near_end_index != -1 else -1
                        if start_index != -1 and end_index != -1:
                            extracted_info = binary_content[start_index + len(b'parameters') + 1:end_index + 1].decode('utf-8', 'replace').strip()
                            lines.append(extracted_info)
                        else:
                            lines.append("No valid parameter block found in PNG.")
                    except (OSError, UnicodeDecodeError) as e:
                        lines.append(f"Error processing PNG binary: {e}")
            else:
                lines.append("No EXIF data or PNG metadata found.")
    except (UnidentifiedImageError, OSError) as e:
        return f"Error opening image: {e}"
    return "\n".join(lines)

def collect_images(folder: str) -> list[str]:
    exts = {'.png', '.jpg', '.jpeg', '.webp', '.bmp'}
    paths: list[str] = []
    # Recursively walk all subfolders to collect images
    for root, _, files in os.walk(folder):
        for name in sorted(files):
            lower = name.lower()
            if any(lower.endswith(ext) for ext in exts):
                paths.append(os.path.join(root, name))
    return paths


def main():
    parser = argparse.ArgumentParser(description="Extract metadata from all images in a folder.")
    parser.add_argument("--img-folder", required=True, help="Path to folder containing images.")
    parser.add_argument("--output", default=None, help="Optional output txt path (defaults to <img-folder>/metadata_dump.txt)")
    args = parser.parse_args()

    folder = os.path.abspath(args.img_folder)
    if not os.path.isdir(folder):
        print(f"Folder not found: {folder}")
        sys.exit(1)

    images = collect_images(folder)
    if not images:
        print("No images found in folder.")
        sys.exit(0)

    output_path = args.output or os.path.join(folder, "metadata_dump.txt")
    try:
        with open(output_path, 'w', encoding='utf-8') as out:
            for img_path in images:
                metadata = get_exif_data(img_path)
                out.write(f"{os.path.basename(img_path)}\n")
                out.write(f"{metadata}\n\n")
        print(f"Metadata written to: {output_path}")
    except OSError as e:
        print(f"Failed writing output: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
