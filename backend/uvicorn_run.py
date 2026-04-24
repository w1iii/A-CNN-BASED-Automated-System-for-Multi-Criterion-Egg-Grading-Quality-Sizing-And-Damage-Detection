import sys
import importlib


def check_dependencies():
    required_modules = {
        "fastapi": "fastapi",
        "uvicorn": "uvicorn",
        "sqlalchemy": "sqlalchemy",
        "passlib": "passlib",
        "jose": "jose",
        "pydantic": "pydantic",
        "pydantic-settings": "pydantic_settings",
        "python-multipart": "multipart",
        "bcrypt": "bcrypt",
        "python-dotenv": "dotenv",
        "alembic": "alembic",
        "aiofiles": "aiofiles",
        "numpy": "numpy",
        "opencv-python-headless": "cv2",
        "Pillow": "PIL"
    }
    missing = []
    for pkg, module in required_modules.items():
        try:
            importlib.import_module(module)
        except ModuleNotFoundError:
            missing.append(pkg)

    if missing:
        print("ERROR: Missing required modules:")
        for m in missing:
            print(f"  - {m}")
        print("\nInstall missing modules with:")
        print(f"  pip install {' '.join(missing)}")
        sys.exit(1)


def main():
    check_dependencies()
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()