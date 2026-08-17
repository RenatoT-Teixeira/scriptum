from google import genai
from prompts import transcription_prompt
import base64

client = genai.Client()

def image_analise(image_bytes, mime_type):
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    interaction = client.interactions.create(
        model="gemini-3.6-flash",
        input=[
            {"type": "text", "text": transcription_prompt},
            {
                "type": "image",
                "data": image_b64,
                "mime_type": mime_type
            }
        ]
    )

    return interaction.output_text