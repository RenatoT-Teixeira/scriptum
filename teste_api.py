from google import genai

client = genai.Client()
uploaded_image = client.files.upload(file="images/teste.png")

interaction = client.interactions.create(
    model="gemini-3.6-flash",
    input=[
        {"type": "text", "text": "Descreva essa imagem"},
        {
            "type": "image",
            "uri": uploaded_image.uri,
            "mime_type": uploaded_image.mime_type
        }
    ]
)
print(interaction.output_text)