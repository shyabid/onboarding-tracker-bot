# 🤖 Onboarding Tracker Bot

A comprehensive Discord bot for tracking onboarding roles with detailed analytics, reporting, and data export capabilities.

## ✨ Features

### 📊 Role Tracking
- **Automatic Detection**: Monitors role additions and removals in real-time
- **Flexible Configuration**: Track any roles you want with custom categories
- **Source Tracking**: Identifies where role changes come from
- **Member Activity**: Tracks individual user progression

### 📈 Advanced Analytics & Reporting
- **🔥 Interactive Dashboard**: Advanced analytics with buttons and real-time navigation
- **📊 Live Dashboard**: Real-time monitoring with auto-refresh capabilities
- **📅 Multi-Period Analysis**: Daily, weekly, and monthly insights
- **💡 Intelligent Insights**: AI-generated key findings and trends
- **📈 Performance Metrics**: Visual progress bars and success rates
- **👥 User Analytics**: Detailed user behavior analysis and leaderboards

### 📋 Analytics Include
- Total role additions and removals
- Net changes (gains vs losses) per role
- Top users gaining/losing roles
- Source breakdown (manual vs automatic changes)
- User activity statistics
- Role popularity metrics

### 💾 Data Export
- **Excel Export**: Comprehensive spreadsheets with multiple worksheets
- **CSV Export**: Individual CSV files for each data type
- **Formatted Reports**: Ready-to-share Discord messages

## 🚀 Quick Start

### 1. Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Run setup script
python setup.py

# Configure your bot token in config.py
```

### 2. Discord Bot Setup
1. Create a Discord application at https://discord.com/developers/applications
2. Create a bot user and copy the token
3. Invite the bot with these permissions:
   - Read Messages
   - Send Messages
   - Use Slash Commands
   - View Channels
   - Manage Roles

### 3. Run the Bot
```bash
python bot.py
```

### 4. Configure the Bot
Use `/tracker info` to see all available commands and get started with:
1. `/tracker config` - Configure onboarding detection settings
2. `/tracker role track <role>` - Add roles you want to track
3. `/tracker status` - View current tracking status

## 📝 Commands

All commands are organized under the main `/tracker` command group with subcommands:

### Configuration
- `/tracker config [detection_hours] [min_roles]` - Configure onboarding detection settings
- `/tracker status` - View current onboarding tracking status
- `/tracker info` - Display bot information and available commands

### Role Management
- `/tracker role track <role> [category]` - Add a role to tracking
- `/tracker role untrack <role>` - Remove a role from tracking
- `/tracker role list` - List all tracked roles

### Advanced Reports
- `/tracker report advanced` - 🔥 **Interactive analytics dashboard with buttons**
- `/tracker dashboard` - 📊 **Live real-time dashboard with auto-refresh**
- `/tracker report daily` - Generate daily onboarding report
- `/tracker report weekly` - Generate weekly onboarding report
- `/tracker report monthly` - Generate monthly onboarding report
- `/tracker report full` - Generate all reports at once

### Data Export
- `/tracker export excel [period]` - Export data to Excel file
  - Periods: daily, weekly, monthly, or all

### User Statistics
- `/tracker user stats <user>` - Get detailed stats for a specific user

## 📊 Advanced Features Preview

### 🔥 Interactive Analytics Dashboard
The new advanced dashboard includes:
- **📊 Overview Stats**: Total events, roles, users, and activity metrics
- **📈 Performance Metrics**: Success rates, efficiency scores, and activity levels
- **💡 Intelligent Insights**: AI-generated key findings and trend analysis
- **🎯 Interactive Buttons**: Navigate between different views seamlessly
- **📅 Period Selector**: Switch between daily, weekly, monthly analysis
- **👥 User Analytics**: Detailed user behavior and leaderboards

### 📊 Live Dashboard Features
Real-time monitoring includes:
- **🔴 Live Metrics**: Current monitoring status and recent activity
- **📅 Today's Performance**: Current day statistics and trends
- **⚙️ System Health**: Bot status and configuration monitoring
- **⚡ Recent Activity**: Live feed of the latest role changes
- **📊 Performance Bars**: Visual indicators with progress bars
- **🔄 Auto-Refresh**: Keep data updated with refresh button

### Enhanced Report Sample
```
📊 Advanced Onboarding Analytics Dashboard
Comprehensive tracking insights for **Your Server**

🎯 Overview Stats
Total Events: 1,247
Roles Added: 1,089 ✅
Roles Removed: 158 ❌
Net Change: +931 📈
Active Users: 234
Roles Tracked: 12

📈 Performance Metrics
Success Rate: 87.3%
Avg Roles/User: 4.7
Activity Score: 89/100
Efficiency: 85.5%

💡 Key Insights
• Strong growth in daily period - 45 net role additions
• 'Member' is the most popular role with 123 additions
• Automated onboarding is working - 89 completions detected
• High user engagement in weekly - 3.2 events per user

[📊 Overview] [📅 Daily] [📆 Weekly] [📋 Monthly] [👥 Users]
```

## 🗃️ Database Schema

The bot uses SQLite with three main tables:

### role_events
Tracks all role addition/removal events:
- `user_id`, `username`, `role_id`, `role_name`
- `event_type` (added/removed), `timestamp`
- `source_channel`, `source_type`

### user_metadata
Stores user statistics:
- `total_roles_gained`, `total_roles_lost`
- `join_date`, `first_role_date`, `last_activity`

### tracked_roles
Configuration of which roles to monitor:
- `role_id`, `role_name`, `category`
- `is_active` status

## 📁 File Structure

```
onboarding-tracker-bot/
├── bot.py              # Main bot file
├── config.py           # Configuration
├── database.py         # Database operations
├── reports.py          # Report generation
├── setup.py           # Setup script
├── requirements.txt   # Dependencies
├── cogs/
│   ├── __init__.py
│   └── tracker.py     # Main tracking cog
└── onboarding_tracker.db  # SQLite database (created automatically)
```

## ⚙️ Configuration

### config.py
```python
token = "your_discord_bot_token_here"
cogs = ["cogs.tracker"]
```

### Role Categories
When adding roles to tracking, you can specify categories:
- `onboarding` - New member roles
- `progression` - Level/experience roles  
- `engagement` - Activity-based roles
- `staff` - Moderation/helper roles
- `event` - Temporary event roles

## 🔧 Advanced Usage

### Custom Time Periods
The bot supports custom date ranges for reports (when using the API directly):
```python
# Get events for last 7 days
events = await db.get_role_events(guild_id, start_date, end_date)
```

### Source Tracking
The bot automatically detects different sources of role changes:
- `role_update` - Direct role assignments
- `reaction_role` - Reaction role bots
- `level_up` - Leveling bots
- `verification` - Verification systems
- `manual` - Manual assignments by staff

### Export Formats
- **Excel**: Multi-sheet workbooks with summary, role changes, user activity, and raw events
- **CSV**: Individual files for different data types
- **JSON**: Raw data for integration with other systems

## 🛠️ Troubleshooting

### Common Issues

**Bot not tracking roles:**
- Ensure the bot has "Manage Roles" permission
- Check that roles are added to tracking with `/track_role`
- Verify the bot can see the channels where roles are assigned

**No data in reports:**
- Add roles to tracking first with `/track_role`
- Wait for role changes to occur after setup
- Check that the bot is online and responding

**Permission errors:**
- Role management commands require "Manage Roles" permission
- Export commands require "Manage Server" permission
- Regular users can view reports but not export data

### Database Issues
```bash
# Reset database (WARNING: Deletes all data)
rm onboarding_tracker.db
python setup.py
```

## 🤝 Contributing

Feel free to submit issues and enhancement requests!

## 📄 License

This project is open source and available under the MIT License.

## 🎯 Roadmap

- [ ] Web dashboard for advanced analytics
- [ ] Integration with popular leveling bots
- [ ] Automated weekly summary posts
- [ ] Role prediction based on user activity
- [ ] Custom report scheduling
- [ ] Multi-server support
- [ ] API endpoints for external integrations
