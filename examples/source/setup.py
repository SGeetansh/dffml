import os
import importlib.util
from setuptools import setup

# Boilerplate to load commonalities
spec = importlib.util.spec_from_file_location(
    "setup_common", os.path.join(os.path.dirname(__file__), "setup_common.py")
)
common = importlib.util.module_from_spec(spec)
spec.loader.exec_module(common)

common.KWARGS["install_requires"] += ["aiosqlite>=0.15.0"]
common.KWARGS["entry_points"] = {
    "dffml.source": [
        f"customsqlite = {common.IMPORT_NAME}.custom_sqlite:CustomSQLiteSource"
    ]
}

setup(**common.KWARGS)
