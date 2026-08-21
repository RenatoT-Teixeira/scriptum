import streamlit as st
import pandas as pd
from io import StringIO
from gemini_api import image_analise

st.markdown("<h1 style='text-align: center;'>Scriptum</h1>", unsafe_allow_html=True)

uploaded_image = st.file_uploader("Upload an image", type=["png", "jpg", "jpeg"])
image_box = st.container(
    border=True,
    height=400,
)
with image_box:
    if uploaded_image is not None:
        st.image(
            uploaded_image, caption="Your Uploaded Image", use_container_width=True
        )

option = st.selectbox(
    "Selecione a opção desejada",
    ["Transcrição", "Correções", "Trechos incertos", "Analise Genealogica"],
)

with st.spinner("Analisando a imagem..."):
    if uploaded_image is not None:
        image_bytes = uploaded_image.getvalue()
        mime_type = uploaded_image.type

        result = image_analise(image_bytes, mime_type)

        st.write("Tipo recebido no app.py:", type(result))
