from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import sys
import shlex
import msvcrt as m


def decode_user_comment(user_comment):
    try:
        # Decode the byte string as UTF-16 big-endian with backslash replacement
        decoded_comment = user_comment.decode('utf-16be', 'backslashreplace')
        return decoded_comment
    except UnicodeDecodeError:
        # If decoding fails, return the original byte string
        return user_comment

def get_exif_data(image_path):
    # Open the image file
    image = Image.open(image_path)

    # Check if the image has EXIF data
    if hasattr(image, '_getexif') and image._getexif() is not None:
        # Get the EXIF data
        exif_data = image._getexif()

        # Print all EXIF data
        for tag, value in exif_data.items():
            tag_name = TAGS.get(tag, tag)

            # Special handling for UserComment tag
            if tag_name == 'UserComment':
                value = decode_user_comment(value)
                value = value[4:]
                print(f"{value}")

        # For GPS data
        if 'GPSInfo' in exif_data:
            for tag, value in exif_data['GPSInfo'].items():
                tag_name = GPSTAGS.get(tag, tag)
                print(f"GPS {tag_name}: {value}")

    elif image_path.endswith(".png"):
        #print("image is png file")
        png_filename = image_path
        # Check if the image has a PNGInfo object
        png_info = image.info
        if png_info and 'tEXt' in png_info:
            #print(f"tEXt and PNGInfo found in the image.")
            text_chunks = png_info['tEXt']  # Access the list of key-value pairs
            for key, value in text_chunks:  # Iterate over the list
                print(f"tEXt {key}: {value}")  # Access the key and value directly
                # Process the text based on the key (e.g., decode if necessary)

        else:
            try:
                # Read the PNG file as binary
                with open(png_filename, 'rb') as f:
                    # Read the binary content
                    binary_content = f.read()

                    # Find the start and end of the relevant text
                    start_index = binary_content.find(b'parameters')
                    near_end_index = binary_content.find(b'Hashes: ')
                    end_index = binary_content.find(b'tEXt', near_end_index) -9

                    # Extract the relevant portion
                    if start_index != -1 and end_index != -1:
                        extracted_info = binary_content[start_index + len(b'parameters') + 1:end_index + 1].decode('utf-8').strip()  # noqa: E501
                        # print modified info extracted from the PNG between the start and end indices
                        print(extracted_info)
                    else:
                        print(f"No valid data found in {png_filename}.")
            except Exception as e:
                print(f"Error processing {png_filename}: {e}")
    else:
        print("No EXIF data or PNG tEXt chunks found in the image.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python your_script.py <image_path>")
        sys.exit(1)

    # Use shlex.split to properly parse command-line arguments
    # Enclose the image path in double quotes to handle spaces
    image_path = shlex.split(f'"{sys.argv[1]}"')[0]
    get_exif_data(image_path)
    print("Image Path:", image_path)

    # Add this line to keep the command prompt window open
    print("Press any key to exit...")
    m.getch()
