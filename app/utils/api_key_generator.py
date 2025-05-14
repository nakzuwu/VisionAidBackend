import secrets

def generate_api_key():
    return secrets.token_hex(32)  # 64 karakter hex