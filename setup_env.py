import os
from cryptography.fernet import Fernet

print("🔧 Setting up environment...")

# 1. Generate Fernet Key
fernet_key = Fernet.generate_key().decode()
print(f"✅ Generated FERNET_KEY: {fernet_key}")

# 2. Ask user for required values
admin_key = input("Enter ADMIN_KEY (your private password): ").strip()
client_id = input("Enter Google OAUTH_CLIENT_ID: ").strip()
client_secret = input("Enter Google OAUTH_CLIENT_SECRET: ").strip()

# 3. Save to .env file
with open(".env", "w") as f:
    f.write(f"FERNET_KEY={fernet_key}\n")
    f.write(f"ADMIN_KEY={admin_key}\n")
    f.write(f"OAUTH_CLIENT_ID={client_id}\n")
    f.write(f"OAUTH_CLIENT_SECRET={client_secret}\n")

print("\n📄 Saved to .env file!")
print("➡️ .env content:")
print("--------------------------------")
print(open(".env").read())
print("--------------------------------")

print("\n🔄 Exporting variables into current session...")

# (Windows PowerShell environment variables)
os.system(f"$env:FERNET_KEY='{fernet_key}'")
os.system(f"$env:ADMIN_KEY='{admin_key}'")
os.system(f"$env:OAUTH_CLIENT_ID='{client_id}'")
os.system(f"$env:OAUTH_CLIENT_SECRET='{client_secret}'")

print("🎉 Setup complete! Now run:")
print("\n➡ uvicorn main:app --reload --port 8000")
print("➡ Then run python admin_oauth.py")

