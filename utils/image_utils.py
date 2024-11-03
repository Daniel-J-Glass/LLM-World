import requests
import os
import io
import base64
from PIL import Image
from utils.visual_utils import generate_svg_image, generate_image, upload_image_to_imgur

import config

class ImageManager:
    def generate_new_image(self, visual_output, config):
        try:
            first_person_description = visual_output.get("first_person_description")
            first_person_svg = visual_output.get("first_person_svg")
            
            if config.GENERATE_SVG and first_person_svg:
                image_bytes = generate_svg_image(
                    positive_prompt=config.FIRST_PERSON_MODIFIER.format(visual=first_person_description),
                    svg=first_person_svg,
                    negative_prompt=config.NEGATIVE_STYLE_MODIFIER,
                    kwargs=config.SVG_IMAGE_ARGS
                )
            else:
                image_bytes = generate_image(
                    positive_prompt=config.FIRST_PERSON_MODIFIER.format(visual=first_person_description),
                    negative_prompt=config.NEGATIVE_STYLE_MODIFIER
                )

            new_image = Image.open(io.BytesIO(image_bytes)) if image_bytes else None
            return new_image
        except Exception as e:
            print(f"Failed to generate image: {str(e)}")
            return None

    def save_image(self, image, path):
        try:
            image.save(path)
            print(f"Saved image to {path}")
        except Exception as e:
            print(f"Error saving image: {e}")

    def encode_image_to_base64(self, image):
        try:
            buffered = io.BytesIO()
            image.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
            return img_str
        except Exception as e:
            print(f"Error encoding image: {e}")
            return None
