import os
from pathlib import Path
from dotenv import load_dotenv

print(">>> Starting test_env.py")

# Show current working directory
print("CWD:", os.getcwd())

# List files in current folder
print("Files in CWD:", os.listdir("."))

# Check if .env exists here
env_path = Path(".") / ".env"
print(".env exists here?:", env_path.exists())
print(".env full path should be:", env_path.resolve())

# Try loading .env
loaded = load_dotenv()
print("load_dotenv() returned:", loaded)

# Print the key value
print("OPENAI_API_KEY from env:", repr(os.getenv("OPENAI_API_KEY")))

print(">>> Done test_env.py")