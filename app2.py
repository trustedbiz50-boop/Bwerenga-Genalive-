from dotenv import load_dotenv
load_dotenv(

)
# === NEW: needed for Cloudinary photo uploads ===
import os
print("CLUD_NAME:", os.environ.get("CLOUDINARY_CLOUD_NAME")),
print("API_KEY:", os.environ.get("CLOUDINARY_API_KEY")),
print("API_SECRET:", os.environ.get("CLOUDINARY_API_SECRET")),