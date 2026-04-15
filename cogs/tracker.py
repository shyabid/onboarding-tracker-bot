from discord.ext import commands, tasks
import discord
from discord import app_commands
from database import Database
from reports import ReportGenerator
from datetime import datetime, timezone, timedelta
import asyncio
import os
import traceback
from typing import Optional, Set, Dict

class HelpView(discord.ui.View):
    """Interactive help system with multiple pages"""
    
    def __init__(self, interaction_user: discord.Member):
        super().__init__(timeout=300)
        self.interaction_user = interaction_user
        self.current_page = "getting_started"
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensure only the command user can use the buttons"""
        return interaction.user.id == self.interaction_user.id
    
    def create_getting_started_embed(self) -> discord.Embed:
        """Create the getting started page"""
        embed = discord.Embed(
            title="Getting Started with Onboarding Tracker",
            description="Welcome to the comprehensive onboarding tracking system. This guide will help you get up and running quickly.",
            color=0x2ecc71
        )
        
        embed.add_field(
            name="What is Onboarding Tracking?",
            value="This bot automatically tracks when users receive roles in your server, helping you monitor onboarding progress, member engagement, and role distribution patterns.",
            inline=False
        )
        
        embed.add_field(
            name="Basic Setup",
            value="**1.** The bot starts tracking automatically when added to your server\n"
                  "**2.** All role changes are logged in real-time\n"
                  "**3.** Use `/tracker status` to see current tracking status\n"
                  "**4.** Generate your first report with `/tracker report basic`",
            inline=False
        )
        
        embed.add_field(
            name="Quick Commands to Try",
            value="`/tracker status` - View system status\n"
                  "`/tracker report basic` - Generate a basic report\n"
                  "`/tracker dashboard` - View live dashboard\n"
                  "`/tracker analytics dashboard` - View visual analytics",
            inline=False
        )
        
        embed.add_field(
            name="Key Features",
            value="**Automatic Detection:** Identifies onboarding completion\n"
                  "**Real-time Tracking:** Monitors all role changes instantly\n"
                  "**Visual Analytics:** Comprehensive graphs and charts\n"
                  "**Smart Reporting:** Daily, weekly, and monthly insights\n"
                  "**Export Options:** Excel and CSV exports available",
            inline=False
        )
        
        embed.set_footer(text="Use the buttons below to explore specific features • Page 1/3")
        return embed
    
    def create_tracking_embed(self) -> discord.Embed:
        """Create the tracking features page"""
        embed = discord.Embed(
            title="Role Tracking Features",
            description="Comprehensive role change monitoring and onboarding detection capabilities.",
            color=0x2ecc71
        )
        
        embed.add_field(
            name="Automatic Role Tracking",
            value="**Role Additions:** Tracks when users receive new roles\n"
                  "**Role Removals:** Monitors when roles are taken away\n"
                  "**Source Detection:** Identifies manual vs automated assignments\n"
                  "**Timing Analysis:** Records precise timestamps for all changes",
            inline=False
        )
        
        embed.add_field(
            name="Onboarding Detection",
            value="**Smart Detection:** Automatically identifies new member onboarding\n"
                  "**Completion Tracking:** Detects when onboarding is finished\n"
                  "**Time Analysis:** Measures how long onboarding takes\n"
                  "**Success Metrics:** Tracks onboarding completion rates",
            inline=False
        )
        
        embed.add_field(
            name="Tracking Commands",
            value="`/tracker status` - Current tracking status and statistics\n"
                  "`/tracker user stats <member>` - Individual user tracking history\n"
                  "`/tracker export excel` - Export data for analysis",
            inline=False
        )
        
        embed.set_footer(text="All role changes are tracked automatically • Page 2/3")
        return embed
    
    def create_analytics_embed(self) -> discord.Embed:
        """Create the analytics page"""
        embed = discord.Embed(
            title="Visual Analytics & Charts",
            description="Comprehensive visual analytics with interactive charts and graphs.",
            color=0x2ecc71
        )
        
        embed.add_field(
            name="Analytics Dashboard",
            value="**Comprehensive Dashboard:** Multi-panel overview with key metrics\n"
                  "**Real-time Updates:** Live data visualization\n"
                  "**Interactive Elements:** Clickable charts and filters\n"
                  "**Professional Design:** Clean, easy-to-understand visualizations",
            inline=False
        )
        
        embed.add_field(
            name="Available Chart Types",
            value="**Activity Timeline:** Role changes over time with trend lines\n"
                  "**Role Distribution:** Pie charts showing role popularity\n"
                  "**User Activity Heatmap:** Activity patterns by day and hour\n"
                  "**Growth Trends:** Cumulative growth analysis\n"
                  "**Source Analysis:** Breakdown of role assignment sources",
            inline=False
        )
        
        embed.add_field(
            name="Analytics Commands",
            value="`/tracker analytics dashboard` - Full analytics dashboard\n"
                  "`/tracker analytics timeline` - Activity timeline chart\n"
                  "`/tracker analytics distribution` - Role distribution chart\n"
                  "`/tracker analytics heatmap` - User activity heatmap\n"
                  "`/tracker analytics trends` - Growth trend analysis",
            inline=False
        )
        
        embed.set_footer(text="All charts generated with real-time data • Page 3/3")
        return embed
    
    @discord.ui.button(label="Getting Started", style=discord.ButtonStyle.success, row=0)
    async def getting_started_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = "getting_started"
        embed = self.create_getting_started_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="Tracking", style=discord.ButtonStyle.primary, row=0)
    async def tracking_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = "tracking"
        embed = self.create_tracking_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="Analytics", style=discord.ButtonStyle.primary, row=0)
    async def analytics_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = "analytics"
        embed = self.create_analytics_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

class LiveDashboardView(discord.ui.View):
    """Live dashboard view with real-time update buttons"""
    
    def __init__(self, tracker_cog, guild_id: int):
        super().__init__(timeout=300)
        self.tracker_cog = tracker_cog
        self.guild_id = guild_id
        
    @discord.ui.button(label="Refresh Status", style=discord.ButtonStyle.primary, row=0)
    async def refresh_status(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Refresh the current status display"""
        await interaction.response.defer()
        
        try:
            recent_joiners_count = len(self.tracker_cog.recent_joins)
            total_events = len(await self.tracker_cog.db.get_role_events(self.guild_id))
            
            last_hour = datetime.now(timezone.utc) - timedelta(hours=1)
            recent_events = await self.tracker_cog.db.get_role_events(self.guild_id, last_hour)
            recent_activity = len(recent_events)
            
            embed = discord.Embed(
                title="Live Dashboard - Status Refreshed",
                description=f"Updated at <t:{int(datetime.now().timestamp())}:T>",
                color=0x2ecc71
            )
            
            embed.add_field(
                name="Current Activity",
                value=f"**Monitoring:** {recent_joiners_count} new members\n"
                      f"**Total Events:** {total_events:,}\n"
                      f"**Last Hour:** {recent_activity} events\n"
                      f"**Status:** {'Active' if recent_activity > 0 else 'Quiet'}",
                inline=True
            )
            
            await interaction.edit_original_response(embed=embed, view=self)
        except Exception as e:
            await interaction.followup.send(f"Error refreshing status: {str(e)}", ephemeral=True)
    
    @discord.ui.button(label="View Analytics", style=discord.ButtonStyle.success, row=0)
    async def view_analytics(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Quick access to analytics dashboard"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            embed, file = await self.tracker_cog.reporter.create_enhanced_report_embed(
                self.guild_id, interaction.guild.name, "dashboard"
            )
            await interaction.followup.send(embed=embed, file=file, ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Error loading analytics: {str(e)}", ephemeral=True)

class Tracker(commands.Cog):
    """Dynamic onboarding role tracker with comprehensive reporting and analytics."""

    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
        self.reporter = ReportGenerator(self.db)
        
        # Track members who just joined (for onboarding detection)
        self.recent_joins: Dict[int, datetime] = {}
        
        # Configurable settings for onboarding detection
        self.onboarding_detection_window = timedelta(hours=24)
        self.min_roles_for_completion = 1
        
    async def cog_load(self):
        """Initialize database when cog loads"""
        await self.db.init_db()
        print("✅ Dynamic Onboarding Tracker initialized")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Track when new members join the server"""
        try:
            self.recent_joins[member.id] = datetime.now(timezone.utc)

            await self.db.record_member_join(
                user_id=member.id,
                username=str(member),
                guild_id=member.guild.id,
                join_time=datetime.now(timezone.utc)
            )
        except Exception:
            print(f"[tracker] on_member_join failed for {member.id} in guild {member.guild.id}:")
            traceback.print_exc()

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        """Track role changes and detect onboarding completion"""
        try:
            if before.roles == after.roles:
                return

            added_roles = set(after.roles) - set(before.roles)
            removed_roles = set(before.roles) - set(after.roles)

            is_recent_joiner = after.id in self.recent_joins
            join_time = self.recent_joins.get(after.id) if is_recent_joiner else None

            onboarding_completion = False
            time_since_join = None
            if is_recent_joiner and join_time:
                time_since_join = datetime.now(timezone.utc) - join_time
                if time_since_join <= self.onboarding_detection_window:
                    non_everyone_roles = [r for r in after.roles if r.name != "@everyone"]
                    if len(non_everyone_roles) >= self.min_roles_for_completion:
                        onboarding_completion = True

            # Track added roles
            for role in added_roles:
                if role.name == "@everyone":
                    continue

                source_type = "manual_assign"
                source_info = {}

                if onboarding_completion:
                    source_type = "onboarding_completion"
                    source_info = {
                        "join_time": join_time.isoformat() if join_time else None,
                        "time_to_complete": str(time_since_join) if time_since_join else None,
                        "total_roles_gained": len(added_roles)
                    }

                    if after.id in self.recent_joins:
                        del self.recent_joins[after.id]

                await self.db.add_role_event(
                    user_id=after.id,
                    username=str(after),
                    role_id=role.id,
                    role_name=role.name,
                    event_type='added',
                    guild_id=after.guild.id,
                    source_type=source_type,
                    source_info=source_info
                )

            # Track removed roles
            for role in removed_roles:
                if role.name == "@everyone":
                    continue

                await self.db.add_role_event(
                    user_id=after.id,
                    username=str(after),
                    role_id=role.id,
                    role_name=role.name,
                    event_type='removed',
                    guild_id=after.guild.id,
                    source_type="role_removal"
                )
        except Exception:
            print(f"[tracker] on_member_update failed for {after.id} in guild {after.guild.id}:")
            traceback.print_exc()

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Clean up tracking when members leave"""
        try:
            if member.id in self.recent_joins:
                del self.recent_joins[member.id]

            await self.db.record_member_leave(
                user_id=member.id,
                guild_id=member.guild.id,
                leave_time=datetime.now(timezone.utc)
            )
        except Exception:
            print(f"[tracker] on_member_remove failed for {member.id} in guild {member.guild.id}:")
            traceback.print_exc()

    # Create command groups
    tracker_group = app_commands.Group(name="tracker", description="Onboarding role tracking and analytics")
    
    @tracker_group.command(name="config", description="Configure onboarding detection settings")
    @app_commands.describe(
        detection_hours="Hours to monitor new members for onboarding (default: 24)",
        min_roles="Minimum roles needed to consider onboarding complete (default: 1)"
    )
    async def config(self, interaction: discord.Interaction, 
                    detection_hours: int = None, min_roles: int = None):
        """Configure onboarding detection settings"""
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("You need 'Manage Server' permission to use this command.", ephemeral=True)
            return

        settings = {}
        if detection_hours is not None:
            if detection_hours < 1 or detection_hours > 168:
                await interaction.response.send_message("Detection hours must be between 1 and 168 (1 week).", ephemeral=True)
                return
            settings['detection_window_hours'] = detection_hours
            self.onboarding_detection_window = timedelta(hours=detection_hours)

        if min_roles is not None:
            if min_roles < 1 or min_roles > 10:
                await interaction.response.send_message("Minimum roles must be between 1 and 10.", ephemeral=True)
                return
            settings['min_roles_for_completion'] = min_roles
            self.min_roles_for_completion = min_roles

        if settings:
            await self.db.update_guild_settings(interaction.guild_id, settings)
            
        embed = discord.Embed(title="Onboarding Detection Settings", color=0x2ecc71)
        embed.add_field(name="Detection Window", value=f"{int(self.onboarding_detection_window.total_seconds() // 3600)} hours", inline=True)
        embed.add_field(name="Min Roles for Completion", value=self.min_roles_for_completion, inline=True)
        
        if settings:
            embed.description = "Settings updated successfully"
        
        await interaction.response.send_message(embed=embed)

    @tracker_group.command(name="status", description="View current onboarding tracking status")
    async def status(self, interaction: discord.Interaction):
        """View current onboarding tracking status"""
        recent_joiners_count = len(self.recent_joins)
        total_events = len(await self.db.get_role_events(interaction.guild_id))
        
        yesterday = datetime.now(timezone.utc) - timedelta(hours=24)
        recent_events = await self.db.get_role_events(interaction.guild_id, yesterday)
        onboarding_completions = len([e for e in recent_events if e.get('source_type') == 'onboarding_completion'])
        
        embed = discord.Embed(title="Onboarding Tracking Status", color=0x2ecc71)
        embed.add_field(name="Monitoring New Members", value=recent_joiners_count, inline=True)
        embed.add_field(name="Total Events Tracked", value=total_events, inline=True)
        embed.add_field(name="Completions (24h)", value=onboarding_completions, inline=True)
        
        embed.add_field(name="Detection Window", 
                       value=f"{int(self.onboarding_detection_window.total_seconds() // 3600)} hours", 
                       inline=True)
        embed.add_field(name="Min Roles Required", value=self.min_roles_for_completion, inline=True)
        embed.add_field(name="Status", value="Active", inline=True)
        
        if self.recent_joins:
            recent_list = []
            for user_id, join_time in list(self.recent_joins.items())[:5]:
                user = interaction.guild.get_member(user_id)
                if user:
                    time_ago = datetime.now(timezone.utc) - join_time
                    hours = int(time_ago.total_seconds() // 3600)
                    recent_list.append(f"• {user.mention} ({hours}h ago)")
            
            if recent_list:
                embed.add_field(name="Recently Joined (Monitoring)", 
                               value="\n".join(recent_list), inline=False)
        
        await interaction.response.send_message(embed=embed)

    # Report subgroup
    report_group = app_commands.Group(name="report", description="Generate analytics reports", parent=tracker_group)
    
    @report_group.command(name="basic", description="Generate basic summary report")
    async def basic_report(self, interaction: discord.Interaction):
        """Generate a basic summary report"""
        await interaction.response.defer()
        
        try:
            report = await self.reporter.generate_comprehensive_report(
                interaction.guild_id, 'all'
            )
            
            embed = discord.Embed(
                title="Basic Onboarding Report",
                description=f"Summary analytics for **{interaction.guild.name}**",
                color=0x2ecc71,
                timestamp=datetime.now(timezone.utc)
            )
            
            total_events = sum(period['summary'].get('total_events', 0) 
                             for period in report['periods'].values())
            total_added = sum(period['summary'].get('roles_added', 0) 
                            for period in report['periods'].values())
            total_removed = sum(period['summary'].get('roles_removed', 0) 
                              for period in report['periods'].values())
            unique_users = len(set(
                user_id for period in report['periods'].values()
                for user_id in period.get('user_activity', {}).keys()
            ))
            
            embed.add_field(
                name="Overall Statistics",
                value=f"**Total Events:** {total_events:,}\n"
                      f"**Roles Added:** {total_added:,}\n"
                      f"**Roles Removed:** {total_removed:,}\n"
                      f"**Net Growth:** {total_added - total_removed:+,}\n"
                      f"**Active Users:** {unique_users:,}",
                inline=True
            )
            
            period_text = ""
            for period_name, period_data in report['periods'].items():
                summary = period_data['summary']
                period_text += f"**{period_name.title()}:** {summary.get('total_events', 0)} events, "
                period_text += f"+{summary.get('roles_added', 0)} roles\n"
            
            if period_text:
                embed.add_field(
                    name="Period Breakdown",
                    value=period_text,
                    inline=True
                )
            
            embed.set_footer(text="Use /tracker analytics dashboard for visual analytics")
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send(f"Error generating report: {str(e)}")

    @report_group.command(name="advanced", description="Generate advanced interactive report")
    async def advanced_report(self, interaction: discord.Interaction):
        """Generate an advanced interactive report with detailed analytics"""
        await interaction.response.defer()
        
        try:
            embed, view = await self.reporter.create_advanced_report_embed(
                interaction.guild_id, interaction.guild.name, 'all'
            )
            await interaction.followup.send(embed=embed, view=view)
        except Exception as e:
            await interaction.followup.send(f"Error generating advanced report: {str(e)}")

    @report_group.command(name="daily", description="Generate daily onboarding report")
    async def daily_report(self, interaction: discord.Interaction):
        """Generate a daily onboarding report"""
        await interaction.response.defer()
        
        report = await self.reporter.generate_comprehensive_report(
            interaction.guild_id, 'daily'
        )
        
        if 'daily' in report['periods']:
            message = self.reporter.format_report_message(report['periods']['daily'])
            await interaction.followup.send(message)
        else:
            await interaction.followup.send("No daily data available.")

    @report_group.command(name="weekly", description="Generate weekly onboarding report")
    async def weekly_report(self, interaction: discord.Interaction):
        """Generate a weekly onboarding report"""
        await interaction.response.defer()
        
        report = await self.reporter.generate_comprehensive_report(
            interaction.guild_id, 'weekly'
        )
        
        if 'weekly' in report['periods']:
            message = self.reporter.format_report_message(report['periods']['weekly'])
            await interaction.followup.send(message)
        else:
            await interaction.followup.send("No weekly data available.")

    @report_group.command(name="monthly", description="Generate monthly onboarding report")
    async def monthly_report(self, interaction: discord.Interaction):
        """Generate a monthly onboarding report"""
        await interaction.response.defer()
        
        report = await self.reporter.generate_comprehensive_report(
            interaction.guild_id, 'monthly'
        )
        
        if 'monthly' in report['periods']:
            message = self.reporter.format_report_message(report['periods']['monthly'])
            await interaction.followup.send(message)
        else:
            await interaction.followup.send("No monthly data available.")

    # Analytics subgroup
    analytics_group = app_commands.Group(name="analytics", description="Visual analytics and charts", parent=tracker_group)
    
    @analytics_group.command(name="dashboard", description="Generate comprehensive analytics dashboard")
    async def analytics_dashboard(self, interaction: discord.Interaction):
        """Generate a comprehensive analytics dashboard with charts"""
        await interaction.response.defer()
        
        try:
            embed, file = await self.reporter.create_enhanced_report_embed(
                interaction.guild_id, interaction.guild.name, "dashboard"
            )
            await interaction.followup.send(embed=embed, file=file)
        except Exception as e:
            await interaction.followup.send(f"Error generating dashboard: {str(e)}")
    
    @analytics_group.command(name="timeline", description="Generate activity timeline chart")
    @app_commands.describe(days="Number of days to analyze (default: 7)")
    async def analytics_timeline(self, interaction: discord.Interaction, days: int = 7):
        """Generate an activity timeline chart"""
        if days < 1 or days > 90:
            await interaction.response.send_message("Days must be between 1 and 90.", ephemeral=True)
            return
            
        await interaction.response.defer()
        
        try:
            embed, file = await self.reporter.create_enhanced_report_embed(
                interaction.guild_id, interaction.guild.name, "timeline"
            )
            await interaction.followup.send(embed=embed, file=file)
        except Exception as e:
            await interaction.followup.send(f"Error generating timeline: {str(e)}")
    
    @analytics_group.command(name="distribution", description="Generate role distribution chart")
    @app_commands.describe(days="Number of days to analyze (default: 30)")
    async def analytics_distribution(self, interaction: discord.Interaction, days: int = 30):
        """Generate a role distribution pie chart"""
        if days < 1 or days > 90:
            await interaction.response.send_message("Days must be between 1 and 90.", ephemeral=True)
            return
            
        await interaction.response.defer()
        
        try:
            embed, file = await self.reporter.create_enhanced_report_embed(
                interaction.guild_id, interaction.guild.name, "distribution"
            )
            await interaction.followup.send(embed=embed, file=file)
        except Exception as e:
            await interaction.followup.send(f"Error generating distribution chart: {str(e)}")

    @analytics_group.command(name="heatmap", description="Generate user activity heatmap")
    @app_commands.describe(days="Number of days to analyze (default: 30)")
    async def analytics_heatmap(self, interaction: discord.Interaction, days: int = 30):
        """Generate a user activity heatmap showing patterns by day and hour"""
        if days < 1 or days > 90:
            await interaction.response.send_message("Days must be between 1 and 90.", ephemeral=True)
            return
            
        await interaction.response.defer()
        
        try:
            embed, file = await self.reporter.create_enhanced_report_embed(
                interaction.guild_id, interaction.guild.name, "heatmap"
            )
            await interaction.followup.send(embed=embed, file=file)
        except Exception as e:
            await interaction.followup.send(f"Error generating heatmap: {str(e)}")

    @analytics_group.command(name="trends", description="Generate growth trend analysis")
    @app_commands.describe(days="Number of days to analyze (default: 30)")
    async def analytics_trends(self, interaction: discord.Interaction, days: int = 30):
        """Generate a growth trend analysis chart"""
        if days < 1 or days > 90:
            await interaction.response.send_message("Days must be between 1 and 90.", ephemeral=True)
            return
            
        await interaction.response.defer()
        
        try:
            embed, file = await self.reporter.create_enhanced_report_embed(
                interaction.guild_id, interaction.guild.name, "trends"
            )
            await interaction.followup.send(embed=embed, file=file)
        except Exception as e:
            await interaction.followup.send(f"Error generating trends chart: {str(e)}")

    # Dashboard command (standalone)
    @tracker_group.command(name="dashboard", description="Live activity dashboard with real-time metrics")
    async def dashboard(self, interaction: discord.Interaction):
        """Display a live dashboard with real-time tracking metrics"""
        await interaction.response.defer()
        
        try:
            embed = discord.Embed(
                title="Live Onboarding Dashboard",
                description=f"Real-time tracking metrics for **{interaction.guild.name}**",
                color=0x2ecc71,
                timestamp=datetime.now(timezone.utc)
            )
            
            recent_joiners_count = len(self.recent_joins)
            total_events = len(await self.db.get_role_events(interaction.guild_id))
            
            last_hour = datetime.now(timezone.utc) - timedelta(hours=1)
            recent_events = await self.db.get_role_events(interaction.guild_id, last_hour)
            recent_activity = len(recent_events)
            
            embed.add_field(
                name="System Status",
                value=f"**Detection Window:** {int(self.onboarding_detection_window.total_seconds() // 3600)}h\n"
                      f"**Min Roles Required:** {self.min_roles_for_completion}\n"
                      f"**Database Status:** Connected\n"
                      f"**Auto-Detection:** Active",
                inline=True
            )
            
            embed.add_field(
                name="Current Activity",
                value=f"**Monitoring:** {recent_joiners_count} new members\n"
                      f"**Total Events:** {total_events:,}\n"
                      f"**Last Hour:** {recent_activity} events\n"
                      f"**Status:** {'Active' if recent_activity > 0 else 'Quiet'}",
                inline=True
            )
            
            embed.set_footer(text="Dashboard updates in real-time • Use buttons for interactivity")
            
            view = LiveDashboardView(self, interaction.guild_id)
            await interaction.followup.send(embed=embed, view=view)
            
        except Exception as e:
            await interaction.followup.send(f"Error loading dashboard: {str(e)}")

    # Export subgroup
    export_group = app_commands.Group(name="export", description="Export tracking data", parent=tracker_group)
    
    @export_group.command(name="excel", description="Export data to Excel file")
    @app_commands.describe(period="Report period to export")
    @app_commands.choices(period=[
        app_commands.Choice(name="Daily", value="daily"),
        app_commands.Choice(name="Weekly", value="weekly"),
        app_commands.Choice(name="Monthly", value="monthly"),
        app_commands.Choice(name="All periods", value="all")
    ])
    async def export_excel(self, interaction: discord.Interaction, 
                          period: app_commands.Choice[str] = None):
        """Export tracking data to Excel format"""
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("You need 'Manage Server' permission to export data.", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        report_type = period.value if period else 'all'
        excel_data = await self.reporter.export_to_excel(interaction.guild_id, report_type)
        
        filename = f"onboarding_report_{report_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        file = discord.File(fp=excel_data, filename=filename)
        
        await interaction.followup.send(
            f"**Onboarding Report Export**\n"
            f"Period: {report_type.title()}\n"
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC",
            file=file,
            ephemeral=True
        )

    # User subgroup
    user_group = app_commands.Group(name="user", description="User statistics and information", parent=tracker_group)
    
    @user_group.command(name="stats", description="Get statistics for a specific user")
    @app_commands.describe(user="The user to get statistics for")
    async def user_stats(self, interaction: discord.Interaction, user: discord.Member):
        """Get detailed statistics for a specific user"""
        stats = await self.db.get_user_stats(user.id)

        if not stats:
            await interaction.response.send_message(
                f"No tracking data found for {user.mention}."
            )
            return

        embed = discord.Embed(
            title=f"User Statistics: {user.display_name}",
            color=0x2ecc71
        )

        roles_added = stats.get('roles_added', 0) or 0
        roles_removed = stats.get('roles_removed', 0) or 0

        embed.add_field(name="Total Role Events", value=stats.get('total_events', 0) or 0, inline=True)
        embed.add_field(name="Roles Added", value=roles_added, inline=True)
        embed.add_field(name="Roles Removed", value=roles_removed, inline=True)
        embed.add_field(name="Net Role Changes", value=roles_added - roles_removed, inline=True)
        embed.add_field(name="Unique Roles", value=stats.get('unique_roles', 0) or 0, inline=True)
        embed.add_field(name="Onboarding Events", value=stats.get('onboarding_events', 0) or 0, inline=True)

        def _to_ts(value):
            """Parse the various stored timestamp shapes into a unix timestamp."""
            if not value:
                return None
            if isinstance(value, datetime):
                dt = value
            else:
                try:
                    dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
                except ValueError:
                    return None
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return int(dt.timestamp())

        first_ts = _to_ts(stats.get('first_role_date'))
        if first_ts:
            embed.add_field(name="First Role Date", value=f"<t:{first_ts}:F>", inline=False)

        last_ts = _to_ts(stats.get('last_activity'))
        if last_ts:
            embed.add_field(name="Last Activity", value=f"<t:{last_ts}:R>", inline=False)

        await interaction.response.send_message(embed=embed)

    @tracker_group.command(name="help", description="Comprehensive help system for all features")
    @app_commands.describe(topic="Specific help topic to view")
    @app_commands.choices(topic=[
        app_commands.Choice(name="Getting Started", value="getting_started"),
        app_commands.Choice(name="Tracking Features", value="tracking"),
        app_commands.Choice(name="Analytics", value="analytics")
    ])
    async def help_command(self, interaction: discord.Interaction, 
                          topic: app_commands.Choice[str] = None):
        """Display comprehensive help system"""
        view = HelpView(interaction.user)
        
        if topic and topic.value in ["getting_started", "tracking", "analytics"]:
            if topic.value == "getting_started":
                embed = view.create_getting_started_embed()
            elif topic.value == "tracking":
                embed = view.create_tracking_embed()
            elif topic.value == "analytics":
                embed = view.create_analytics_embed()
            view.current_page = topic.value
        else:
            embed = view.create_getting_started_embed()
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=False)

    @tracker_group.command(name="info", description="Show information about the tracking system")
    async def tracker_info(self, interaction: discord.Interaction):
        """Display information about the tracking system"""
        tracked_roles = await self.db.get_tracked_roles(interaction.guild_id)
        total_events = len(await self.db.get_role_events(interaction.guild_id))
        recent_joiners = len(self.recent_joins)
        
        embed = discord.Embed(
            title="Dynamic Onboarding Tracker",
            description="Automatically detects and tracks onboarding completion",
            color=0x2ecc71
        )
        
        embed.add_field(name="Tracked Roles", value=len(tracked_roles), inline=True)
        embed.add_field(name="Total Events", value=total_events, inline=True)
        embed.add_field(name="Monitoring", value=f"{recent_joiners} new members", inline=True)
        
        embed.add_field(
            name="Quick Commands",
            value="`/tracker help` - Comprehensive help system\n"
                  "`/tracker status` - Current system status\n"
                  "`/tracker dashboard` - Live activity dashboard\n"
                  "`/tracker analytics dashboard` - Visual analytics\n"
                  "`/tracker report basic` - Basic summary report",
            inline=False
        )
        
        embed.add_field(
            name="How It Works",
            value="**1. Automatic Detection:** Monitors new members for role changes\n"
                  "**2. Smart Tracking:** Identifies onboarding completion automatically\n"
                  "**3. Comprehensive Analytics:** Tracks sources, timing, and patterns\n"
                  "**4. Visual Reports:** Generates charts and graphs for insights",
            inline=False
        )
        
        embed.set_footer(text="Use /tracker help for detailed documentation")
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    """Setup function required by discord.py cog loading"""
    await bot.add_cog(Tracker(bot))
