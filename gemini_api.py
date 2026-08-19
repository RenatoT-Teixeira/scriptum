from google import genai
from prompts import transcription_prompt
from pydantic import BaseModel
import base64

client = genai.Client()

class TranscriptionResult(BaseModel):
    transcription: str
    corrections: str
    uncertain_excerpts: str
    
def image_analise(image_bytes, mime_type):
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    interaction = client.interactions.create(
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": TranscriptionResult.model_json_schema()            
        }
        model="gemini-3.6-flash",
        input=[
            {"type": "text", "text": transcription_prompt},
            {"type": "image", "data": image_b64, "mime_type": mime_type},
        ],
    )

    return interaction.output_text
