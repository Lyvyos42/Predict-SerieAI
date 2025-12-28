#!/usr/bin/env python3
"""
Check admin status for a Telegram bot
"""

import os
import sys

# Load the same config as bot.py
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_USER_ID = os.environ.get("ADMIN_USER_ID", "")
INVITE_ONLY = os.environ.get("INVITE_ONLY", "true").lower() == "true"

print("🔍 ADMIN STATUS CHECKER")
print("=" * 50)

# Check environment
print(f"✅ BOT_TOKEN: {'Set' if BOT_TOKEN else '❌ NOT SET!'}")
print(f"📋 ADMIN_USER_ID: '{ADMIN_USER_ID}'")
print(f"🔒 INVITE_ONLY: {INVITE_ONLY}")

# Parse admin IDs
admin_ids = []
for admin_id in ADMIN_USER_ID.split(","):
    admin_id = admin_id.strip()
    if admin_id and admin_id.isdigit():
        admin_ids.append(int(admin_id))

print(f"\n📊 Parsed Admin IDs: {admin_ids}")
print(f"👥 Count: {len(admin_ids)}")

# Simulate user storage
class SimpleUserStorage:
    def __init__(self):
        self.allowed_users = set()
        for admin_id in admin_ids:
            self.allowed_users.add(admin_id)
    
    def list_admins(self):
        return list(self.allowed_users)

storage = SimpleUserStorage()
print(f"\n✅ Admins in storage: {storage.list_admins()}")

# Test some user IDs
test_users = [123456789, 987654321, 111111111]
print("\n🧪 Test User Access:")
for user_id in test_users:
    if user_id in storage.allowed_users:
        print(f"  User {user_id}: ✅ ADMIN")
    else:
        print(f"  User {user_id}: ❌ NOT ADMIN")

print("\n💡 To add admins:")
print("export ADMIN_USER_ID=\"123456789,987654321\"")
print("Then restart your bot.")