import streamlit as st
import pandas as pd 
from io import StringIO

st.markdown("<h1 style='text-align: center;'>Scriptum</h1>", unsafe_allow_html=True)

uploaded_image = st.file_uploader("Upload an image", type=["png", "jpg", "jpeg"])
image_box = st.container(
    border=True,
    height=400,
)
with image_box:
        if uploaded_image is not None:
         st.image(
        uploaded_image,
        caption="Your Uploaded Image",
        use_container_width= True
        
    )