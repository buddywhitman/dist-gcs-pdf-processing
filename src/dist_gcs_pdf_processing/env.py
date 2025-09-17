import os
from dotenv import load_dotenv

def load_env_and_credentials():
    # Look for .env in multiple locations
    # Get the project root (two levels up from this file)
    base_dir = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    
    # Try multiple .env locations in order of preference
    dotenv_paths = [
        os.path.join(base_dir, 'secrets', '.env'),  # Original location
        os.path.join(base_dir, '.env'),             # Root directory (EasyPanel default)
        os.path.join(os.getcwd(), '.env'),          # Current working directory
        os.path.join(os.getcwd(), 'secrets', '.env') # CWD secrets directory
    ]

    # Debug information
    print(f"[DEBUG] Looking for .env in multiple locations...")
    for i, path in enumerate(dotenv_paths):
        print(f"[DEBUG] {i+1}. {path} - exists: {os.path.exists(path)}")

    # Try to load from the first existing .env file
    loaded = False
    for dotenv_path in dotenv_paths:
        if os.path.exists(dotenv_path):
            print(f"[DEBUG] Loading .env from: {dotenv_path}")
            load_dotenv(dotenv_path=dotenv_path, override=True)
            print(f"[DEBUG] .env loaded successfully from {dotenv_path}")
            loaded = True
            break
    
    if not loaded:
        print(f"[DEBUG] No .env file found in any of the expected locations")
        print(f"[DEBUG] CWD: {os.getcwd()}")
        print(f"[DEBUG] .env loaded at entrypoint: {os.getenv('DOTENV_LOADED')}")
    # Handle Google Cloud Storage credentials
    gcs_creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    print(f"[DEBUG] GOOGLE_APPLICATION_CREDENTIALS: {gcs_creds_path}")

    if gcs_creds_path:
        # Always use forward slashes for compatibility
        gcs_creds_path_fixed = gcs_creds_path.replace('\\', '/')
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = gcs_creds_path_fixed
        print(f"[DEBUG] GOOGLE_APPLICATION_CREDENTIALS set to: {gcs_creds_path_fixed}")
        print(f"[DEBUG] File exists: {os.path.exists(gcs_creds_path_fixed)}")
    else:
        # Try default GCS credentials file
        default_gcs_creds = os.path.join(
            base_dir, 'secrets', 'dcpr-ai-80688-7aa4df1a1327.json'
        )
        cwd_default_gcs_creds = os.path.join(
            os.getcwd(), 'secrets', 'dcpr-ai-80688-7aa4df1a1327.json'
        )

        if os.path.exists(default_gcs_creds):
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = default_gcs_creds
            print(f"[DEBUG] Using default GCS credentials from: {default_gcs_creds}")
        elif os.path.exists(cwd_default_gcs_creds):
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = (
                cwd_default_gcs_creds)
            print(f"[DEBUG] Using default GCS credentials from CWD: {cwd_default_gcs_creds}")
        else:
            print("[DEBUG] No GCS credentials file found. Tried:")
            print(f"[DEBUG]   - {default_gcs_creds}")
            print(f"[DEBUG]   - {cwd_default_gcs_creds}")

    # Handle Google Drive credentials
    drive_creds_path = os.getenv('GOOGLE_DRIVE_CREDENTIALS')
    print(f"[DEBUG] GOOGLE_DRIVE_CREDENTIALS: {drive_creds_path}")

    if drive_creds_path:
        # Always use forward slashes for compatibility
        drive_creds_path_fixed = drive_creds_path.replace('\\', '/')
        os.environ['GOOGLE_DRIVE_CREDENTIALS'] = drive_creds_path_fixed
        print(f"[DEBUG] GOOGLE_DRIVE_CREDENTIALS set to: {drive_creds_path_fixed}")
        print(f"[DEBUG] File exists: {os.path.exists(drive_creds_path_fixed)}")
    else:
        # Try default Drive credentials file
        default_drive_creds = (
            os.path.join(base_dir, 'secrets', 'drive-service-account.json'))
        cwd_default_drive_creds = os.path.join(
            os.getcwd(), 'secrets', 'drive-service-account.json'
        )

        if os.path.exists(default_drive_creds):
            os.environ['GOOGLE_DRIVE_CREDENTIALS'] = default_drive_creds
            print(f"[DEBUG] Using default Drive credentials from: {default_drive_creds}")
        elif os.path.exists(cwd_default_drive_creds):
            os.environ['GOOGLE_DRIVE_CREDENTIALS'] = cwd_default_drive_creds
            print(f"[DEBUG] Using default Drive credentials from CWD: {cwd_default_drive_creds}")
        else:
            print("[DEBUG] No Drive credentials file found. Tried:")
            print(f"[DEBUG]   - {default_drive_creds}")
            print(f"[DEBUG]   - {cwd_default_drive_creds}")

    # Final check
    final_gcs_creds = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    final_drive_creds = os.getenv('GOOGLE_DRIVE_CREDENTIALS')
    print(f"[DEBUG] Final GOOGLE_APPLICATION_CREDENTIALS: {final_gcs_creds}")
    print(f"[DEBUG] Final GOOGLE_DRIVE_CREDENTIALS: {final_drive_creds}")
    if final_gcs_creds:
        print(f"[DEBUG] Final GCS credentials file exists: {os.path.exists(final_gcs_creds)}")
    if final_drive_creds:
        print(f"[DEBUG] Final Drive credentials file exists: {os.path.exists(final_drive_creds)}")
