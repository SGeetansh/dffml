import os
import sys
import ast
from pathlib import Path
from io import open

from setuptools import find_packages, setup

self_path = os.path.dirname(os.path.realpath(__file__))

with open(
    os.path.join(self_path, "dffml_model_transformers", "version.py"), "r"
) as f:
    for line in f:
        if line.startswith("VERSION"):
            version = ast.literal_eval(line.strip().split("=")[-1].strip())
            break

with open(os.path.join(self_path, "README.md"), "r", encoding="utf-8") as f:
    readme = f.read()

setup(
    name="dffml-model-transformers",
    version=version,
    description="",
    long_description=readme,
    long_description_content_type="text/markdown",
    author="Himanshu Tripathi",
    author_email="himanshutripathi366@gmail.com",
    url="https://github.com/intel/dffml/blob/master/model/transformers/README.md",
    license="MIT",
    keywords=[""],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
    ],
    entry_points={
        "dffml.model": [
            "ner_tagger = dffml_model_transformers.ner.ner_model:NERModel",
            "qa_model = dffml_model_transformers.qa.qa_model:QAModel",
            "hfclassifier = dffml_model_transformers.classification.classification_model:HFClassificationModel",
        ]
    },
)
