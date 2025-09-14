import os
from dotenv import load_dotenv

def load_env_and_credentials():
    # Look for .env in the project root's secrets directory
    # Get the project root (two levels up from this file)
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    dotenv_path = os.path.join(base_dir, 'secrets', '.env')
    
    # Debug information
    print(f"[DEBUG] .env path: {dotenv_path}")
    print(f"[DEBUG] .env exists: {os.path.exists(dotenv_path)}")
    print(f"[DEBUG] .env readable: {os.access(dotenv_path, os.R_OK) if os.path.exists(dotenv_path) else False}")
    
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path, override=True)
        print(f"[DEBUG] .env loaded successfully from {dotenv_path}")
    else:
        print(f"[DEBUG] Could not read .env: [Errno 2] No such file or directory: '{dotenv_path}'")
        print(f"[DEBUG] CWD: {os.getcwd()}")
        print(f"[DEBUG] .env loaded at entrypoint: {os.getenv('DOTENV_LOADED')}")
    
    # Also try loading from current working directory as fallback
    cwd_dotenv = os.path.join(os.getcwd(), 'secrets', '.env')
    if os.path.exists(cwd_dotenv) and not os.path.exists(dotenv_path):
        print(f"[DEBUG] Loading .env from CWD: {cwd_dotenv}")
        load_dotenv(dotenv_path=cwd_dotenv, override=True)
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
        default_gcs_creds = os.path.join(base_dir, 'secrets', 'dcpr-ai-80688-7aa4df1a1327.json')
        cwd_default_gcs_creds = os.path.join(os.getcwd(), 'secrets', 'dcpr-ai-80688-7aa4df1a1327.json')
        
        if os.path.exists(default_gcs_creds):
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = default_gcs_creds
            print(f"[DEBUG] Using default GCS credentials from: {default_gcs_creds}")
        elif os.path.exists(cwd_default_gcs_creds):
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = cwd_default_gcs_creds
            print(f"[DEBUG] Using default GCS credentials from CWD: {cwd_default_gcs_creds}")
        else:
            print(f"[DEBUG] No GCS credentials file found. Tried:")
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
        default_drive_creds = os.path.join(base_dir, 'secrets', 'drive-service-account.json')
        cwd_default_drive_creds = os.path.join(os.getcwd(), 'secrets', 'drive-service-account.json')
        
        if os.path.exists(default_drive_creds):
            os.environ['GOOGLE_DRIVE_CREDENTIALS'] = default_drive_creds
            print(f"[DEBUG] Using default Drive credentials from: {default_drive_creds}")
        elif os.path.exists(cwd_default_drive_creds):
            os.environ['GOOGLE_DRIVE_CREDENTIALS'] = cwd_default_drive_creds
            print(f"[DEBUG] Using default Drive credentials from CWD: {cwd_default_drive_creds}")
        else:
            print(f"[DEBUG] No Drive credentials file found. Tried:")
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