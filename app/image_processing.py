import hashlib
from PIL import Image

def rotate_image(image_path: str, direction: str):
    """Rotates an image and returns the new md5sum."""
    try:
        image = Image.open(image_path)
        if direction == 'cw':
            rotated_image = image.rotate(-90, expand=True)
        elif direction == 'ccw':
            rotated_image = image.rotate(90, expand=True)
        else:
            return None

        rotated_image.save(image_path)

        with open(image_path, 'rb') as f:
            md5sum = hashlib.md5(f.read()).hexdigest()
        
        return md5sum
    except Exception as e:
        print(f"Error rotating image: {e}")
        return None
