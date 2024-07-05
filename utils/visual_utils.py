# this file should return the generated image as bytes
import requests

from config import (IMAGE_GENERATION_MODEL, SD_KEY, SD_API_HOST)


def generate_image(positive_prompt, negative_prompt):
    """takes in prompt and filename and saves generated image to filename

    Args:
        prompt (str): image generation prompt

    Returns:
        str: base64 image encoding or none
    """

    if "sd3" in IMAGE_GENERATION_MODEL:
        response = requests.post(
            f"https://api.stability.ai/v2beta/stable-image/generate/core",
            headers={
                "authorization": f"Bearer {SD_KEY}",
                "accept": "image/*"
            },
            files={"none": ''},
            data={
                "prompt": positive_prompt,
                "negative_prompt": negative_prompt,
                "samples": 1,
                "aspect_ratio": "3:2",
                "output_format": "jpeg",
                "seed": 1,
                "model": {IMAGE_GENERATION_MODEL},
            },
        )

        if response.status_code == 200:
            return response.content
        else:
            raise Exception(str(response.json()))
        
    elif "sd2" in IMAGE_GENERATION_MODEL:
        raise NotImplementedError
        engine_id = "stable-diffusion-v1-6"
        api_host = SD_API_HOST
        response = requests.post(
            f"{api_host}/v1/generation/{engine_id}/text-to-image",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {SD_KEY}"
            },
            json={
                "text_prompts": [
                    {
                        "text": prompt
                    }
                ],
                "cfg_scale": 7,
                "height": 640,
                "width": 448,
                "samples": 1,
                "steps": 20,
            },
        )

        if response.status_code != 200:
            raise Exception("Non-200 response: " + str(response.text))

        data = response.json()

        return [image["base64"] for image in data["artifacts"]][0]

    return None

if __name__=="__main__":
    from PIL import Image
    import io

    image_bytes = generate_image("A red circle")

    image_stream = io.BytesIO(image_bytes)

    # Open the image
    image = Image.open(image_stream)

    # Display the image
    image.show()
