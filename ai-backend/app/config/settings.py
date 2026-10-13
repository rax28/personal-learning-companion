import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[3]
load_dotenv(ROOT_DIR / ".env")
class Settings:
    ai_internal_token=os.getenv('AI_INTERNAL_TOKEN','change-me')
    online_provider=os.getenv('ONLINE_PROVIDER','mock')
    local_model=os.getenv('LOCAL_MODEL','qwen2.5:3b')
settings=Settings()
