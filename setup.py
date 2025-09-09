#!/usr/bin/env python3
"""
Setup script for Onboarding Tracker Bot
This script helps configure the bot and set up initial tracking roles.
"""

import asyncio
import aiosqlite
from database import Database
import sys

async def setup_database():
    """Initialize the database with tables"""
    print("🔧 Setting up database...")
    db = Database()
    await db.init_db()
    print("✅ Database initialized successfully!")

async def add_sample_roles():
    """Add some common onboarding roles to track"""
    db = Database()
    
    # Sample roles commonly used for onboarding
    sample_roles = [
    ]
    
    print("\n📋 Sample roles you might want to track:")
    for i, role in enumerate(sample_roles, 1):
        print(f"{i}. {role['name']} ({role['category']})")
    
    print("\nNote: You'll need to use Discord slash commands to actually add roles to tracking.")
    print("These are just examples of what you might track.")

def print_setup_instructions():
    """Print setup instructions for the user"""
    print("\n" + "="*60)
    print("🤖 ONBOARDING TRACKER BOT SETUP COMPLETE!")
    print("="*60)
    
    print("\n📝 NEXT STEPS:")
    print("1. Add your Discord bot token to config.py")
    print("2. Invite your bot to your Discord server with these permissions:")
    print("   - Read Messages")
    print("   - Send Messages")
    print("   - Use Slash Commands")
    print("   - View Channels")
    print("   - Manage Roles (for tracking role changes)")
    
    print("\n🚀 GETTING STARTED:")
    print("1. Run the bot: python bot.py")
    print("2. Use /tracker info to see available commands")
    print("3. Use /tracker enable to enable tracking for your server")
    print("4. Use /tracker config to configure detection settings")
    print("5. Use /tracker role track to add roles you want to track")
    print("6. Use /tracker report daily, weekly, or monthly to see analytics")
    
    print("\n📊 FEATURES:")
    print("✅ Automatic onboarding detection")
    print("✅ Dynamic role tracking")
    print("✅ Daily, weekly, and monthly reports")
    print("✅ Excel export functionality")
    print("✅ User statistics and analytics")
    print("✅ Source tracking (where users come from)")
    print("✅ Net gain/loss calculations")
    print("✅ Enable/disable per server")
    
    print("\n🔧 CONFIGURATION:")
    print("- Use /tracker enable to enable tracking for your server")
    print("- Use /tracker config to configure onboarding detection")
    print("- Use /tracker role track to add roles to monitoring")
    print("- Use /tracker role untrack to remove roles from monitoring")
    print("- Use /tracker role list to see what's being tracked")
    
    print("\n📈 REPORTS INCLUDE:")
    print("- Total role additions and removals")
    print("- Net changes per role")
    print("- Top users gaining/losing roles")
    print("- Source breakdown (where changes come from)")
    print("- User activity analytics")
    
    print("\n" + "="*60)

async def main():
    """Main setup function"""
    print("🤖 Onboarding Tracker Bot Setup")
    print("="*40)
    
    try:
        await setup_database()
        await add_sample_roles()
        print_setup_instructions()
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
