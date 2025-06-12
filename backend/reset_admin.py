#!/usr/bin/env python3
"""
Open WebUI Admin Reset Tool
Skrypt do resetowania administratora w Open WebUI Backend
"""

import os
import sys
import sqlite3
import shutil
import getpass
from pathlib import Path
from datetime import datetime
import uuid
import time

# Add the current directory to Python path to import Open WebUI modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from open_webui.utils.auth import get_password_hash
from open_webui.env import DATA_DIR, DATABASE_URL


class AdminResetTool:
    def __init__(self):
        self.data_dir = Path(DATA_DIR)
        self.db_path = self.data_dir / "webui.db"
        self.backup_path = self.data_dir / f"webui_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        
    def print_header(self):
        print("=" * 60)
        print("🔧 Open WebUI Admin Reset Tool")
        print("=" * 60)
        print(f"📁 Data Directory: {self.data_dir}")
        print(f"🗄️  Database: {self.db_path}")
        print(f"📦 Backup will be saved to: {self.backup_path}")
        print("=" * 60)
        
    def check_database_exists(self):
        """Check if database exists"""
        return self.db_path.exists()
        
    def backup_database(self):
        """Create backup of current database"""
        if not self.check_database_exists():
            print("❌ Database not found, no backup needed")
            return False
            
        try:
            shutil.copy2(self.db_path, self.backup_path)
            print(f"✅ Database backup created: {self.backup_path}")
            return True
        except Exception as e:
            print(f"❌ Failed to create backup: {e}")
            return False
            
    def get_database_info(self):
        """Get information about current database"""
        if not self.check_database_exists():
            return None
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get user count
            cursor.execute("SELECT COUNT(*) FROM user")
            user_count = cursor.fetchone()[0]
            
            # Get first user (admin)
            cursor.execute("SELECT id, name, email, role, created_at FROM user ORDER BY created_at ASC LIMIT 1")
            first_user = cursor.fetchone()
            
            # Get all admin users
            cursor.execute("SELECT id, name, email, created_at FROM user WHERE role = 'admin' ORDER BY created_at ASC")
            admin_users = cursor.fetchall()
            
            conn.close()
            
            return {
                "user_count": user_count,
                "first_user": first_user,
                "admin_users": admin_users
            }
        except Exception as e:
            print(f"❌ Error reading database: {e}")
            return None
            
    def print_database_info(self):
        """Print current database information"""
        info = self.get_database_info()
        if not info:
            print("📊 Database not found or empty")
            return
            
        print("📊 Current Database Status:")
        print(f"   👥 Total users: {info['user_count']}")
        
        if info['first_user']:
            print(f"   👑 First user (primary admin): {info['first_user'][1]} ({info['first_user'][2]})")
            
        if info['admin_users']:
            print(f"   🔧 Admin users ({len(info['admin_users'])}):")
            for admin in info['admin_users']:
                created = datetime.fromtimestamp(admin[3]).strftime("%Y-%m-%d %H:%M")
                print(f"      - {admin[1]} ({admin[2]}) - created: {created}")
        print()
        
    def option_1_full_reset(self):
        """Option 1: Complete database reset"""
        print("🔥 OPTION 1: Complete Database Reset")
        print("⚠️  WARNING: This will DELETE ALL data (users, chats, settings)")
        print("⚠️  The first person to register after reset will become admin")
        print()
        
        confirm = input("Type 'DELETE ALL DATA' to confirm: ")
        if confirm != "DELETE ALL DATA":
            print("❌ Reset cancelled")
            return False
            
        if self.check_database_exists():
            if self.backup_database():
                try:
                    os.remove(self.db_path)
                    print("✅ Database deleted successfully")
                    print("✅ Next startup will create a fresh database")
                    print("✅ First user to register will become admin")
                    return True
                except Exception as e:
                    print(f"❌ Failed to delete database: {e}")
                    return False
        else:
            print("✅ Database already doesn't exist")
            return True
            
    def option_2_reset_password(self):
        """Option 2: Reset admin password"""
        print("🔐 OPTION 2: Reset Admin Password")
        print("This will reset the password of the first user (primary admin)")
        print()
        
        info = self.get_database_info()
        if not info or not info['first_user']:
            print("❌ No users found in database")
            return False
            
        first_user = info['first_user']
        print(f"👑 Primary admin: {first_user[1]} ({first_user[2]})")
        print()
        
        new_password = getpass.getpass("Enter new password for admin: ")
        if len(new_password) < 4:
            print("❌ Password must be at least 4 characters long")
            return False
            
        confirm_password = getpass.getpass("Confirm new password: ")
        if new_password != confirm_password:
            print("❌ Passwords don't match")
            return False
            
        if not self.backup_database():
            return False
            
        try:
            hashed_password = get_password_hash(new_password)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Update password in auth table
            cursor.execute("UPDATE auth SET password = ? WHERE id = ?", (hashed_password, first_user[0]))
            
            conn.commit()
            conn.close()
            
            print("✅ Admin password reset successfully")
            print(f"✅ You can now login with:")
            print(f"   📧 Email: {first_user[2]}")
            print(f"   🔐 Password: {new_password}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to reset password: {e}")
            return False
            
    def option_3_add_new_admin(self):
        """Option 3: Add new admin user"""
        print("👤 OPTION 3: Add New Admin User")
        print("This will create a new admin user alongside existing users")
        print()
        
        email = input("Enter email for new admin: ").strip().lower()
        if not email or "@" not in email:
            print("❌ Invalid email address")
            return False
            
        name = input("Enter name for new admin: ").strip()
        if not name:
            print("❌ Name cannot be empty")
            return False
            
        password = getpass.getpass("Enter password for new admin: ")
        if len(password) < 4:
            print("❌ Password must be at least 4 characters long")
            return False
            
        confirm_password = getpass.getpass("Confirm password: ")
        if password != confirm_password:
            print("❌ Passwords don't match")
            return False
            
        # Check if email already exists
        if self.check_database_exists():
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM user WHERE email = ?", (email,))
                if cursor.fetchone():
                    print(f"❌ User with email {email} already exists")
                    conn.close()
                    return False
                conn.close()
            except Exception as e:
                print(f"❌ Error checking existing users: {e}")
                return False
                
        if not self.backup_database():
            return False
            
        try:
            user_id = str(uuid.uuid4())
            hashed_password = get_password_hash(password)
            current_time = int(time.time())
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Insert into auth table
            cursor.execute("""
                INSERT INTO auth (id, email, password, active)
                VALUES (?, ?, ?, ?)
            """, (user_id, email, hashed_password, True))
            
            # Insert into user table
            cursor.execute("""
                INSERT INTO user (id, name, email, role, profile_image_url, 
                                last_active_at, updated_at, created_at, api_key, settings, info, oauth_sub)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, name, email, "admin", "/user.png", 
                  current_time, current_time, current_time, None, None, None, None))
            
            conn.commit()
            conn.close()
            
            print("✅ New admin user created successfully")
            print(f"✅ Login credentials:")
            print(f"   📧 Email: {email}")
            print(f"   🔐 Password: {password}")
            print(f"   👤 Name: {name}")
            print(f"   🆔 Role: admin")
            return True
            
        except Exception as e:
            print(f"❌ Failed to create new admin: {e}")
            return False
            
    def show_menu(self):
        """Show main menu"""
        print("\n🎯 Choose reset option:")
        print("1️⃣  Complete reset (DELETE ALL DATA)")
        print("2️⃣  Reset admin password (keep all data)")
        print("3️⃣  Add new admin user (keep all data)")
        print("4️⃣  Show database info")
        print("5️⃣  Exit")
        print()
        
    def run(self):
        """Main program loop"""
        self.print_header()
        self.print_database_info()
        
        while True:
            self.show_menu()
            
            try:
                choice = input("Enter your choice (1-5): ").strip()
                
                if choice == "1":
                    if self.option_1_full_reset():
                        break
                elif choice == "2":
                    if self.option_2_reset_password():
                        break
                elif choice == "3":
                    if self.option_3_add_new_admin():
                        break
                elif choice == "4":
                    self.print_database_info()
                elif choice == "5":
                    print("👋 Goodbye!")
                    break
                else:
                    print("❌ Invalid choice. Please enter 1-5.")
                    
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Unexpected error: {e}")


if __name__ == "__main__":
    tool = AdminResetTool()
    tool.run() 