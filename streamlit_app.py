"""Pintu masuk untuk Streamlit Community Cloud.

Streamlit Cloud secara default mencari `streamlit_app.py`. Aplikasi sebenarnya
ada di `app.py` — file ini hanya menjalankannya, supaya deploy berhasil baik
"Main file path" diisi `app.py` maupun dibiarkan default.
"""
import runpy

runpy.run_path("app.py", run_name="__main__")
