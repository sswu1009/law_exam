from setuptools import setup, find_packages

setup(
    name="exam_system",
    version="2.0.0",
    packages=find_packages(),
    install_requires=[
        "streamlit>=1.28.0",
        "pandas>=2.0.0",
        "requests>=2.31.0",
        "google-generativeai>=0.3.0",
        "openpyxl>=3.1.0",
    ],
)
