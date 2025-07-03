import os
from dotenv import load_dotenv

def load_env_and_credentials():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dotenv_path = os.path.join(base_dir, 'secrets', '.env')
    load_dotenv(dotenv_path=dotenv_path, override=True)
    creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if creds_path:
        # Always use forward slashes for compatibility
        creds_path_fixed = creds_path.replace('\\', '/')
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = creds_path_fixed
        if not os.path.isfile(creds_path_fixed):
            print(f"[DEBUG] GOOGLE_APPLICATION_CREDENTIALS set to: {creds_path_fixed} (file not found)")
        else:
            print(f"[DEBUG] GOOGLE_APPLICATION_CREDENTIALS set to: {creds_path_fixed} (file found)")
    else:
        default_creds = os.path.join(base_dir, 'secrets', 'dcpr-ai-80688-7aa4df1a1327.json')
        if os.path.exists(default_creds):
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = default_creds
            print(f"[DEBUG] GOOGLE_APPLICATION_CREDENTIALS set to default: {default_creds}")
        else:
            print("[DEBUG] No GOOGLE_APPLICATION_CREDENTIALS found or set!") 