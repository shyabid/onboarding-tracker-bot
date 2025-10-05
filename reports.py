#!/usr/bin/env python3

import pandas as pd
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
import io
import discord
import asyncio
import math
from database import Database

# Configure matplotlib backend before importing pyplot
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.io as pio
from PIL import Image
import base64

class ReportGenerator:
    def __init__(self, database: Database):
        self.db = database
    
    def _get_date_ranges(self, report_type: str = 'all') -> Dict[str, tuple]:
        """Get date ranges for different report periods"""
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        ranges = {}
        
        if report_type in ['daily', 'all']:
            ranges['daily'] = (today_start, now)
        
        if report_type in ['weekly', 'all']:
            week_start = today_start - timedelta(days=today_start.weekday())
            ranges['weekly'] = (week_start, now)
        
        if report_type in ['monthly', 'all']:
            month_start = today_start.replace(day=1)
            ranges['monthly'] = (month_start, now)
        
        return ranges
    
    async def generate_comprehensive_report(self, guild_id: int, 
                                          report_type: str = 'all') -> Dict[str, Any]:
        """Generate a comprehensive report with daily, weekly, and monthly data"""
        date_ranges = self._get_date_ranges(report_type)
        report = {
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'guild_id': guild_id,
            'periods': {}
        }
        
        for period, (start_date, end_date) in date_ranges.items():
            period_data = await self._generate_period_report(
                guild_id, start_date, end_date, period
            )
            report['periods'][period] = period_data
        
        return report
    
    async def _generate_period_report(self, guild_id: int, start_date: datetime,
                                    end_date: datetime, period_name: str) -> Dict[str, Any]:
        """Generate report for a specific time period"""
        # Get summary statistics
        summary = await self.db.get_summary_stats(guild_id, start_date, end_date)
        
        # Get detailed events
        events = await self.db.get_role_events(guild_id, start_date, end_date)
        
        # Calculate additional metrics
        net_changes = {}
        user_activity = {}
        source_breakdown = {}
        
        for event in events:
            role_name = event['role_name']
            user_id = event['user_id']
            source_type = event['source_type'] or 'unknown'
            
            # Net changes per role
            if role_name not in net_changes:
                net_changes[role_name] = {'added': 0, 'removed': 0}
            net_changes[role_name][event['event_type']] += 1
            
            # User activity
            if user_id not in user_activity:
                user_activity[user_id] = {
                    'username': event['username'],
                    'roles_added': 0,
                    'roles_removed': 0,
                    'events': []
                }
            user_activity[user_id][f"roles_{event['event_type']}"] += 1
            user_activity[user_id]['events'].append({
                'role': role_name,
                'action': event['event_type'],
                'timestamp': event['timestamp']
            })
            
            # Source breakdown
            if source_type not in source_breakdown:
                source_breakdown[source_type] = {'added': 0, 'removed': 0}
            source_breakdown[source_type][event['event_type']] += 1
        
        # Calculate net changes
        for role_data in net_changes.values():
            role_data['net'] = role_data['added'] - role_data['removed']
        
        return {
            'period': period_name,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'summary': summary,
            'net_changes_by_role': net_changes,
            'user_activity': user_activity,
            'source_breakdown': source_breakdown,
            'top_gainers': self._get_top_users(user_activity, 'roles_added'),
            'top_losers': self._get_top_users(user_activity, 'roles_removed'),
            'raw_events': events[:50]  # Limit to recent 50 events for the report
        }
    
    def _get_top_users(self, user_activity: Dict, metric: str, limit: int = 10) -> List[Dict]:
        """Get top users by a specific metric"""
        sorted_users = sorted(
            user_activity.items(),
            key=lambda x: x[1][metric],
            reverse=True
        )
        
        return [
            {
                'user_id': user_id,
                'username': data['username'],
                'count': data[metric]
            }
            for user_id, data in sorted_users[:limit]
            if data[metric] > 0
        ]
    
    async def export_to_excel(self, guild_id: int, report_type: str = 'all') -> io.BytesIO:
        """Export report data to Excel format"""
        report = await self.generate_comprehensive_report(guild_id, report_type)
        
        # Create Excel writer
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            
            # Summary sheet
            summary_data = []
            for period, data in report['periods'].items():
                summary_data.append({
                    'Period': period.title(),
                    'Start Date': data['start_date'][:10],
                    'End Date': data['end_date'][:10],
                    'Total Events': data['summary']['total_events'],
                    'Roles Added': data['summary']['roles_added'],
                    'Roles Removed': data['summary']['roles_removed'],
                    'Net Change': data['summary']['roles_added'] - data['summary']['roles_removed'],
                    'Unique Users': data['summary']['unique_users'],
                    'Roles Affected': data['summary']['roles_affected']
                })
            
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Detailed sheets for each period
            for period, data in report['periods'].items():
                # Role changes sheet
                role_changes = []
                for role, changes in data['net_changes_by_role'].items():
                    role_changes.append({
                        'Role': role,
                        'Added': changes['added'],
                        'Removed': changes['removed'],
                        'Net Change': changes['net']
                    })
                
                if role_changes:
                    role_df = pd.DataFrame(role_changes)
                    role_df.to_excel(writer, sheet_name=f'{period.title()} Roles', index=False)
                
                # User activity sheet
                user_data = []
                for user_id, activity in data['user_activity'].items():
                    user_data.append({
                        'User ID': user_id,
                        'Username': activity['username'],
                        'Roles Added': activity['roles_added'],
                        'Roles Removed': activity['roles_removed'],
                        'Net Change': activity['roles_added'] - activity['roles_removed']
                    })
                
                if user_data:
                    user_df = pd.DataFrame(user_data)
                    user_df.to_excel(writer, sheet_name=f'{period.title()} Users', index=False)
                
                # Events sheet
                if data['raw_events']:
                    events_df = pd.DataFrame(data['raw_events'])
                    events_df.to_excel(writer, sheet_name=f'{period.title()} Events', index=False)
        
        output.seek(0)
        return output
    
    async def export_to_csv(self, guild_id: int, report_type: str = 'all') -> Dict[str, io.StringIO]:
        """Export report data to CSV format"""
        report = await self.generate_comprehensive_report(guild_id, report_type)
        csv_files = {}
        
        for period, data in report['periods'].items():
            # Events CSV
            if data['raw_events']:
                events_df = pd.DataFrame(data['raw_events'])
                csv_buffer = io.StringIO()
                events_df.to_csv(csv_buffer, index=False)
                csv_buffer.seek(0)
                csv_files[f'{period}_events.csv'] = csv_buffer
            
            # Role changes CSV
            role_changes = []
            for role, changes in data['net_changes_by_role'].items():
                role_changes.append({
                    'Role': role,
                    'Added': changes['added'],
                    'Removed': changes['removed'],
                    'Net Change': changes['net']
                })
            
            if role_changes:
                role_df = pd.DataFrame(role_changes)
                csv_buffer = io.StringIO()
                role_df.to_csv(csv_buffer, index=False)
                csv_buffer.seek(0)
                csv_files[f'{period}_roles.csv'] = csv_buffer
        
        return csv_files
    
    def format_report_message(self, period_data: Dict[str, Any], 
                            max_roles: int = 10) -> str:
        """Format report data into a Discord message"""
        summary = period_data['summary']
        period = period_data['period'].title()
        
        message = f"📊 **{period} Onboarding Report**\n"
        message += f"*{period_data['start_date'][:10]} to {period_data['end_date'][:10]}*\n\n"
        
        # Summary statistics with None checks
        total_events = summary.get('total_events') or 0
        roles_added = summary.get('roles_added') or 0
        roles_removed = summary.get('roles_removed') or 0
        unique_users = summary.get('unique_users') or 0
        roles_affected = summary.get('roles_affected') or 0
        
        message += "**📈 Summary:**\n"
        message += f"• Total Events: {total_events}\n"
        message += f"• Roles Added: {roles_added} ✅\n"
        message += f"• Roles Removed: {roles_removed} ❌\n"
        net_change = roles_added - roles_removed
        net_emoji = "📈" if net_change > 0 else "📉" if net_change < 0 else "➖"
        message += f"• Net Change: {net_change} {net_emoji}\n"
        message += f"• Unique Users: {unique_users}\n"
        message += f"• Roles Affected: {roles_affected}\n\n"
        
        # Top role changes
        if period_data['net_changes_by_role']:
            message += "**🏆 Top Role Changes:**\n"
            sorted_roles = sorted(
                period_data['net_changes_by_role'].items(),
                key=lambda x: abs(x[1]['net']),
                reverse=True
            )
            
            for i, (role_name, changes) in enumerate(sorted_roles[:max_roles]):
                net = changes['net']
                if net != 0:
                    direction = "+" if net > 0 else ""
                    emoji = "📈" if net > 0 else "📉"
                    message += f"• {role_name}: {direction}{net} {emoji} "
                    message += f"({changes['added']}➕ | {changes['removed']}➖)\n"
        
        # Source breakdown
        if period_data['source_breakdown']:
            message += "\n**🌐 Source Breakdown:**\n"
            for source, counts in period_data['source_breakdown'].items():
                total = counts['added'] + counts['removed']
                if total > 0:
                    message += f"• {source.title()}: {total} events "
                    message += f"({counts['added']}➕ | {counts['removed']}➖)\n"
        
        # Top gainers and losers
        if period_data['top_gainers']:
            message += "\n**🎉 Top Gainers:**\n"
            for user in period_data['top_gainers'][:5]:
                message += f"• {user['username']}: +{user['count']} roles\n"
        
        if period_data['top_losers']:
            message += "\n**😔 Most Roles Lost:**\n"
            for user in period_data['top_losers'][:5]:
                message += f"• {user['username']}: -{user['count']} roles\n"
        
        return message
    
    async def create_advanced_report_embed(self, guild_id: int, guild_name: str = None, 
                                         report_type: str = 'all') -> tuple[discord.Embed, discord.ui.View]:
        """Create an advanced report with embeds and interactive buttons"""
        report = await self.generate_comprehensive_report(guild_id, report_type)
        
        # Create main embed
        embed = discord.Embed(
            title="📊 Advanced Onboarding Analytics Dashboard",
            description=f"Comprehensive tracking insights for **{guild_name or 'Server'}**",
            color=0x2ecc71,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Add overview statistics
        total_events = 0
        total_added = 0
        total_removed = 0
        total_users = set()
        total_roles = set()
        
        for period_data in report['periods'].values():
            summary = period_data['summary']
            total_events += summary.get('total_events', 0)
            total_added += summary.get('roles_added', 0)
            total_removed += summary.get('roles_removed', 0)
            
            # Collect unique users and roles
            for user_id in period_data['user_activity'].keys():
                total_users.add(user_id)
            for role_name in period_data['net_changes_by_role'].keys():
                total_roles.add(role_name)
        
        # Overview section
        net_change = total_added - total_removed
        net_emoji = "📈" if net_change > 0 else "📉" if net_change < 0 else "➖"
        
        embed.add_field(
            name="🎯 Overview Stats",
            value=f"**Total Events:** {total_events:,}\n"
                  f"**Roles Added:** {total_added:,} ✅\n"
                  f"**Roles Removed:** {total_removed:,} ❌\n"
                  f"**Net Change:** {net_change:,} {net_emoji}\n"
                  f"**Active Users:** {len(total_users):,}\n"
                  f"**Roles Tracked:** {len(total_roles):,}",
            inline=True
        )
        
        # Performance metrics
        if total_events > 0:
            success_rate = (total_added / total_events) * 100
            avg_roles_per_user = total_added / len(total_users) if total_users else 0
            
            embed.add_field(
                name="📈 Performance Metrics",
                value=f"**Success Rate:** {success_rate:.1f}%\n"
                      f"**Avg Roles/User:** {avg_roles_per_user:.1f}\n"
                      f"**Activity Score:** {min(100, (total_events / 10)):.0f}/100\n"
                      f"**Efficiency:** {((total_added - total_removed) / max(1, total_added)) * 100:.1f}%",
                inline=True
            )
        
        # Period comparison
        periods = ['daily', 'weekly', 'monthly']
        period_stats = []
        for period in periods:
            if period in report['periods']:
                data = report['periods'][period]
                summary = data['summary']
                period_stats.append({
                    'name': period.title(),
                    'events': summary.get('total_events', 0),
                    'added': summary.get('roles_added', 0),
                    'users': summary.get('unique_users', 0)
                })
        
        if period_stats:
            comparison_text = ""
            for stat in period_stats:
                comparison_text += f"**{stat['name']}:** {stat['events']} events, {stat['added']} roles, {stat['users']} users\n"
            
            embed.add_field(
                name="📅 Period Comparison",
                value=comparison_text,
                inline=False
            )
        
        # Top insights
        insights = await self._generate_insights(report)
        if insights:
            embed.add_field(
                name="💡 Key Insights",
                value="\n".join([f"• {insight}" for insight in insights[:5]]),
                inline=False
            )
        
        # Create interactive view
        view = AdvancedReportView(self, guild_id, report)
        
        embed.set_footer(
            text="Use the buttons below to explore detailed analytics",
            icon_url="https://cdn.discordapp.com/emojis/741614680652046396.png"
        )
        
        return embed, view
    
    async def _generate_insights(self, report: Dict[str, Any]) -> List[str]:
        """Generate intelligent insights from the report data"""
        insights = []
        
        for period_name, period_data in report['periods'].items():
            summary = period_data['summary']
            
            # Activity insights
            total_events = summary.get('total_events', 0)
            if total_events > 0:
                roles_added = summary.get('roles_added', 0)
                roles_removed = summary.get('roles_removed', 0)
                
                if roles_added > roles_removed * 2:
                    insights.append(f"Strong growth in {period_name} period - {roles_added - roles_removed} net role additions")
                
                if roles_removed > roles_added:
                    insights.append(f"Negative trend in {period_name} - more roles removed than added")
                
                # User engagement
                unique_users = summary.get('unique_users', 0)
                if unique_users > 0:
                    engagement_rate = total_events / unique_users
                    if engagement_rate > 3:
                        insights.append(f"High user engagement in {period_name} - {engagement_rate:.1f} events per user")
            
            # Top role insights
            if period_data['net_changes_by_role']:
                top_role = max(period_data['net_changes_by_role'].items(), 
                             key=lambda x: x[1]['added'])
                if top_role[1]['added'] > 5:
                    insights.append(f"'{top_role[0]}' is the most popular role with {top_role[1]['added']} additions")
            
            # Source insights
            if period_data['source_breakdown']:
                onboarding_events = period_data['source_breakdown'].get('onboarding_completion', {})
                if onboarding_events.get('added', 0) > 0:
                    insights.append(f"Automated onboarding is working - {onboarding_events['added']} completions detected")
        
        return insights[:10]  # Limit to top 10 insights
    
    def create_detailed_period_embed(self, period_data: Dict[str, Any], 
                                   guild_name: str = None) -> discord.Embed:
        """Create a detailed embed for a specific period"""
        period = period_data['period'].title()
        summary = period_data['summary']
        
        embed = discord.Embed(
            title=f"📊 {period} Detailed Report",
            description=f"In-depth analysis for {guild_name or 'Server'}",
            color=0x3498db,
            timestamp=datetime.fromisoformat(period_data['end_date'].replace('Z', '+00:00'))
        )
        
        # Time range
        start_date = datetime.fromisoformat(period_data['start_date'].replace('Z', '+00:00'))
        end_date = datetime.fromisoformat(period_data['end_date'].replace('Z', '+00:00'))
        
        embed.add_field(
            name="📅 Time Range",
            value=f"**From:** <t:{int(start_date.timestamp())}:F>\n"
                  f"**To:** <t:{int(end_date.timestamp())}:F>\n"
                  f"**Duration:** {(end_date - start_date).days} days",
            inline=False
        )
        
        # Summary stats
        total_events = summary.get('total_events', 0)
        roles_added = summary.get('roles_added', 0)
        roles_removed = summary.get('roles_removed', 0)
        unique_users = summary.get('unique_users', 0)
        roles_affected = summary.get('roles_affected', 0)
        
        embed.add_field(
            name="📈 Summary Statistics",
            value=f"**Total Events:** {total_events:,}\n"
                  f"**Roles Added:** {roles_added:,} ✅\n"
                  f"**Roles Removed:** {roles_removed:,} ❌\n"
                  f"**Net Change:** {roles_added - roles_removed:,}\n"
                  f"**Unique Users:** {unique_users:,}\n"
                  f"**Roles Affected:** {roles_affected:,}",
            inline=True
        )
        
        # Top role changes
        if period_data['net_changes_by_role']:
            sorted_roles = sorted(
                period_data['net_changes_by_role'].items(),
                key=lambda x: x[1]['added'],
                reverse=True
            )
            
            top_roles_text = ""
            for i, (role_name, changes) in enumerate(sorted_roles[:8]):
                if changes['added'] > 0 or changes['removed'] > 0:
                    net = changes['added'] - changes['removed']
                    direction = "📈" if net > 0 else "📉" if net < 0 else "➖"
                    top_roles_text += f"{direction} **{role_name}**: +{changes['added']} -{changes['removed']} (net: {net:+})\n"
            
            if top_roles_text:
                embed.add_field(
                    name="🏆 Top Role Changes",
                    value=top_roles_text,
                    inline=True
                )
        
        # User activity leaderboard
        if period_data['top_gainers']:
            gainers_text = ""
            for i, user in enumerate(period_data['top_gainers'][:5]):
                medal = ["🏆", "🏆", "🏆", "🏅", "🏅"][i] if i < 5 else "•"
                gainers_text += f"{medal} **{user['username']}**: +{user['count']} roles\n"
            
            embed.add_field(
                name="🎉 Top Role Gainers",
                value=gainers_text,
                inline=True
            )
        
        # Source breakdown with visual indicators
        if period_data['source_breakdown']:
            source_text = ""
            for source, counts in period_data['source_breakdown'].items():
                total = counts['added'] + counts['removed']
                if total > 0:
                    source_emoji = {
                        'onboarding_completion': '🎯',
                        'manual_assign': '👤',
                        'role_removal': '❌',
                        'unknown': '❓'
                    }.get(source, '📋')
                    
                    percentage = (counts['added'] / max(1, counts['added'] + counts['removed'])) * 100
                    source_text += f"{source_emoji} **{source.replace('_', ' ').title()}**: {total} events ({percentage:.0f}% positive)\n"
            
            if source_text:
                embed.add_field(
                    name="🌐 Activity Sources",
                    value=source_text,
                    inline=False
                )
        
        # Performance indicators
        if total_events > 0:
            success_rate = (roles_added / total_events) * 100
            activity_density = total_events / max(1, (end_date - start_date).days)
            
            # Create performance bar
            performance_bars = {
                'Success Rate': (success_rate, '%'),
                'Activity Density': (min(100, activity_density * 10), ' events/day'),
                'User Engagement': (min(100, (total_events / max(1, unique_users)) * 20), ' avg events/user')
            }
            
            performance_text = ""
            for metric, (value, unit) in performance_bars.items():
                bar_length = 10
                filled = int((value / 100) * bar_length)
                bar = "█" * filled + "░" * (bar_length - filled)
                performance_text += f"**{metric}:** {bar} {value:.1f}{unit}\n"
            
            embed.add_field(
                name="⚡ Performance Indicators",
                value=performance_text,
                inline=False
            )
        
        return embed
    
    def create_user_analytics_embed(self, period_data: Dict[str, Any], 
                                  guild_name: str = None) -> discord.Embed:
        """Create an embed focused on user analytics"""
        embed = discord.Embed(
            title="👥 User Analytics Dashboard",
            description=f"User behavior insights for {guild_name or 'Server'}",
            color=0xe74c3c
        )
        
        user_activity = period_data['user_activity']
        
        if not user_activity:
            embed.add_field(
                name="No Data",
                value="No user activity recorded for this period.",
                inline=False
            )
            return embed
        
        # User statistics
        total_users = len(user_activity)
        active_users = len([u for u in user_activity.values() if u['roles_added'] > 0])
        power_users = len([u for u in user_activity.values() if u['roles_added'] >= 3])
        
        embed.add_field(
            name="📊 User Overview",
            value=f"**Total Users:** {total_users:,}\n"
                  f"**Active Users:** {active_users:,}\n"
                  f"**Power Users:** {power_users:,} (3+ roles)\n"
                  f"**Activity Rate:** {(active_users/total_users)*100:.1f}%",
            inline=True
        )
        
        # Distribution analysis
        role_counts = [u['roles_added'] for u in user_activity.values()]
        if role_counts:
            avg_roles = sum(role_counts) / len(role_counts)
            max_roles = max(role_counts)
            
            # Create distribution
            distribution = {}
            for count in role_counts:
                if count == 0:
                    distribution['0'] = distribution.get('0', 0) + 1
                elif count <= 2:
                    distribution['1-2'] = distribution.get('1-2', 0) + 1
                elif count <= 5:
                    distribution['3-5'] = distribution.get('3-5', 0) + 1
                else:
                    distribution['6+'] = distribution.get('6+', 0) + 1
            
            embed.add_field(
                name="📈 Role Distribution",
                value=f"**Average:** {avg_roles:.1f} roles/user\n"
                      f"**Maximum:** {max_roles} roles\n"
                      f"**0 roles:** {distribution.get('0', 0)} users\n"
                      f"**1-2 roles:** {distribution.get('1-2', 0)} users\n"
                      f"**3-5 roles:** {distribution.get('3-5', 0)} users\n"
                      f"**6+ roles:** {distribution.get('6+', 0)} users",
                inline=True
            )
        
        # Top performers
        if period_data['top_gainers']:
            top_text = ""
            for i, user in enumerate(period_data['top_gainers'][:8]):
                medal = ["🏆", "🏆", "🏆"][i] if i < 3 else "🏅"
                top_text += f"{medal} **{user['username']}** - {user['count']} roles\n"
            
            embed.add_field(
                name="🏆 Top Performers",
                value=top_text,
                inline=False
            )
        
        # Recent activity timeline
        recent_events = period_data.get('raw_events', [])[:10]
        if recent_events:
            timeline_text = ""
            for event in recent_events:
                timestamp = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
                action_emoji = "✅" if event['event_type'] == 'added' else "❌"
                timeline_text += f"{action_emoji} **{event['username']}** {event['event_type']} **{event['role_name']}** <t:{int(timestamp.timestamp())}:R>\n"
            
            embed.add_field(
                name="⏰ Recent Activity",
                value=timeline_text,
                inline=False
            )
        
        return embed
    
    # ==================== GRAPH GENERATION METHODS ====================
    
    def _configure_matplotlib(self):
        """Configure matplotlib for consistent styling"""
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
        plt.rcParams.update({
            'figure.facecolor': 'white',
            'axes.facecolor': 'white',
            'axes.edgecolor': 'gray',
            'axes.linewidth': 0.8,
            'grid.alpha': 0.3,
            'font.size': 10,
            'axes.titlesize': 12,
            'axes.labelsize': 10,
            'xtick.labelsize': 9,
            'ytick.labelsize': 9
        })
    
    async def generate_activity_timeline_chart(self, guild_id: int, days: int = 7) -> io.BytesIO:
        """Generate a timeline chart showing activity over the specified period"""
        self._configure_matplotlib()
        
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        # Get events for the period
        events = await self.db.get_role_events(guild_id, start_date, end_date)
        
        if not events:
            # Create empty chart
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.text(0.5, 0.5, 'No activity data available', 
                   horizontalalignment='center', verticalalignment='center', transform=ax.transAxes)
            ax.set_title(f'Activity Timeline - Last {days} Days')
        else:
            # Convert to DataFrame
            df = pd.DataFrame(events)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['date'] = df['timestamp'].dt.date
            
            # Group by date and event type
            daily_stats = df.groupby(['date', 'event_type']).size().unstack(fill_value=0)
            
            # Create the plot
            fig, ax = plt.subplots(figsize=(12, 6))
            
            if 'added' in daily_stats.columns:
                ax.bar(daily_stats.index, daily_stats['added'], 
                      label='Roles Added', color='#2ecc71', alpha=0.8)
            if 'removed' in daily_stats.columns:
                ax.bar(daily_stats.index, -daily_stats['removed'], 
                      label='Roles Removed', color='#e74c3c', alpha=0.8)
            
            ax.axhline(y=0, color='black', linestyle='-', alpha=0.3)
            ax.set_title(f'Role Activity Timeline - Last {days} Days')
            ax.set_xlabel('Date')
            ax.set_ylabel('Number of Role Changes')
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            # Format x-axis
            ax.tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        
        # Save to BytesIO
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        plt.close()
        
        return buffer
    
    async def generate_role_distribution_chart(self, guild_id: int, days: int = 30) -> io.BytesIO:
        """Generate a pie chart showing role addition distribution"""
        self._configure_matplotlib()
        
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        events = await self.db.get_role_events(guild_id, start_date, end_date)
        
        if not events:
            fig, ax = plt.subplots(figsize=(10, 8))
            ax.text(0.5, 0.5, 'No role data available', 
                   horizontalalignment='center', verticalalignment='center', transform=ax.transAxes)
            ax.set_title(f'Role Distribution - Last {days} Days')
        else:
            # Filter for added roles only
            df = pd.DataFrame(events)
            added_roles = df[df['event_type'] == 'added']
            
            if added_roles.empty:
                fig, ax = plt.subplots(figsize=(10, 8))
                ax.text(0.5, 0.5, 'No roles added in this period', 
                       horizontalalignment='center', verticalalignment='center', transform=ax.transAxes)
                ax.set_title(f'Role Distribution - Last {days} Days')
            else:
                role_counts = added_roles['role_name'].value_counts()
                
                # Limit to top 10 roles for readability
                if len(role_counts) > 10:
                    top_roles = role_counts.head(9)
                    others_count = role_counts.tail(len(role_counts) - 9).sum()
                    role_counts = pd.concat([top_roles, pd.Series([others_count], index=['Others'])])
                
                fig, ax = plt.subplots(figsize=(10, 8))
                colors = plt.cm.Set3(range(len(role_counts)))
                
                wedges, texts, autotexts = ax.pie(role_counts.values, labels=role_counts.index, 
                                                 autopct='%1.1f%%', colors=colors, startangle=90)
                
                ax.set_title(f'Role Addition Distribution - Last {days} Days')
                
                # Improve text readability
                for autotext in autotexts:
                    autotext.set_color('black')
                    autotext.set_fontsize(9)
                    autotext.set_weight('bold')
        
        plt.tight_layout()
        
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        plt.close()
        
        return buffer
    
    async def generate_user_activity_heatmap(self, guild_id: int, days: int = 30) -> io.BytesIO:
        """Generate a heatmap showing user activity patterns"""
        self._configure_matplotlib()
        
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        events = await self.db.get_role_events(guild_id, start_date, end_date)
        
        if not events:
            fig, ax = plt.subplots(figsize=(12, 8))
            ax.text(0.5, 0.5, 'No activity data available', 
                   horizontalalignment='center', verticalalignment='center', transform=ax.transAxes)
            ax.set_title(f'User Activity Heatmap - Last {days} Days')
        else:
            df = pd.DataFrame(events)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['hour'] = df['timestamp'].dt.hour
            df['weekday'] = df['timestamp'].dt.day_name()
            
            # Create pivot table for heatmap
            heatmap_data = df.groupby(['weekday', 'hour']).size().unstack(fill_value=0)
            
            # Ensure all weekdays are present
            weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            heatmap_data = heatmap_data.reindex(weekdays, fill_value=0)
            
            # Ensure all hours are present
            all_hours = list(range(24))
            heatmap_data = heatmap_data.reindex(columns=all_hours, fill_value=0)
            
            fig, ax = plt.subplots(figsize=(12, 8))
            sns.heatmap(heatmap_data, annot=True, fmt='d', cmap='YlOrRd', 
                       cbar_kws={'label': 'Number of Events'}, ax=ax)
            
            ax.set_title(f'User Activity Heatmap - Last {days} Days')
            ax.set_xlabel('Hour of Day')
            ax.set_ylabel('Day of Week')
        
        plt.tight_layout()
        
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        plt.close()
        
        return buffer
    
    async def generate_trend_analysis_chart(self, guild_id: int, days: int = 30) -> io.BytesIO:
        """Generate a trend analysis chart showing growth patterns"""
        self._configure_matplotlib()
        
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        events = await self.db.get_role_events(guild_id, start_date, end_date)
        
        if not events:
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.text(0.5, 0.5, 'No trend data available', 
                   horizontalalignment='center', verticalalignment='center', transform=ax.transAxes)
            ax.set_title(f'Growth Trend Analysis - Last {days} Days')
        else:
            df = pd.DataFrame(events)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['date'] = df['timestamp'].dt.date
            
            # Calculate daily metrics
            daily_added = df[df['event_type'] == 'added'].groupby('date').size()
            daily_removed = df[df['event_type'] == 'removed'].groupby('date').size()
            
            # Create date range
            date_range = pd.date_range(start=start_date.date(), end=end_date.date(), freq='D')
            daily_added = daily_added.reindex(date_range, fill_value=0)
            daily_removed = daily_removed.reindex(date_range, fill_value=0)
            daily_net = daily_added - daily_removed
            
            # Calculate cumulative and moving averages
            cumulative_net = daily_net.cumsum()
            ma_7 = daily_net.rolling(window=7, center=True).mean()
            
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
            
            # Daily activity
            ax1.bar(date_range, daily_added, alpha=0.7, color='#2ecc71', label='Added')
            ax1.bar(date_range, -daily_removed, alpha=0.7, color='#e74c3c', label='Removed')
            ax1.plot(date_range, ma_7, color='#3498db', linewidth=2, label='7-day Average')
            ax1.axhline(y=0, color='black', linestyle='-', alpha=0.3)
            ax1.set_title('Daily Role Activity')
            ax1.set_ylabel('Role Changes')
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            # Cumulative growth
            ax2.plot(date_range, cumulative_net, color='#9b59b6', linewidth=2, marker='o', markersize=3)
            ax2.fill_between(date_range, cumulative_net, alpha=0.3, color='#9b59b6')
            ax2.axhline(y=0, color='black', linestyle='-', alpha=0.3)
            ax2.set_title('Cumulative Growth Trend')
            ax2.set_xlabel('Date')
            ax2.set_ylabel('Net Role Changes')
            ax2.grid(True, alpha=0.3)
            
            # Format x-axis
            for ax in [ax1, ax2]:
                ax.tick_params(axis='x', rotation=45)
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        
        plt.tight_layout()
        
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        plt.close()
        
        return buffer
    
    async def generate_comprehensive_dashboard(self, guild_id: int, guild_name: str = None) -> io.BytesIO:
        """Generate a comprehensive dashboard with multiple analytics"""
        # Get data for different periods
        report = await self.generate_comprehensive_report(guild_id, 'all')
        
        fig = plt.figure(figsize=(16, 12))
        gs = fig.add_gridspec(3, 2, height_ratios=[1, 1, 1], width_ratios=[1, 1])
        
        # Configure style
        self._configure_matplotlib()
        
        # Title
        fig.suptitle(f'Onboarding Analytics Dashboard - {guild_name or "Server"}', 
                    fontsize=16, fontweight='bold', y=0.95)
        
        try:
            # 1. Activity Timeline (top left)
            ax1 = fig.add_subplot(gs[0, 0])
            if 'weekly' in report['periods'] and report['periods']['weekly']['raw_events']:
                events_df = pd.DataFrame(report['periods']['weekly']['raw_events'])
                events_df['timestamp'] = pd.to_datetime(events_df['timestamp'])
                events_df['date'] = events_df['timestamp'].dt.date
                daily_stats = events_df.groupby(['date', 'event_type']).size().unstack(fill_value=0)
                
                if 'added' in daily_stats.columns:
                    ax1.plot(daily_stats.index, daily_stats['added'], 
                            marker='o', color='#2ecc71', label='Added', linewidth=2)
                if 'removed' in daily_stats.columns:
                    ax1.plot(daily_stats.index, daily_stats['removed'], 
                            marker='s', color='#e74c3c', label='Removed', linewidth=2)
                
                ax1.set_title('Weekly Activity Trend')
                ax1.legend()
                ax1.grid(True, alpha=0.3)
            else:
                ax1.text(0.5, 0.5, 'No weekly data', ha='center', va='center')
                ax1.set_title('Weekly Activity Trend')
            
            # 2. Period Comparison (top right)
            ax2 = fig.add_subplot(gs[0, 1])
            periods_data = []
            for period_name, period_data in report['periods'].items():
                if period_data['summary']:
                    periods_data.append({
                        'Period': period_name.title(),
                        'Added': (period_data['summary'].get('roles_added', 0) or 0),
                        'Removed': (period_data['summary'].get('roles_removed', 0) or 0)
                    })
            
            if periods_data:
                periods_df = pd.DataFrame(periods_data)
                x = range(len(periods_df))
                width = 0.35
                ax2.bar([i - width/2 for i in x], periods_df['Added'], 
                       width, label='Added', color='#2ecc71', alpha=0.8)
                ax2.bar([i + width/2 for i in x], periods_df['Removed'], 
                       width, label='Removed', color='#e74c3c', alpha=0.8)
                ax2.set_xticks(x)
                ax2.set_xticklabels(periods_df['Period'])
                ax2.set_title('Period Comparison')
                ax2.legend()
                ax2.grid(True, alpha=0.3)
            else:
                ax2.text(0.5, 0.5, 'No period data', ha='center', va='center')
                ax2.set_title('Period Comparison')
            
            # 3. Top Roles (middle left)
            ax3 = fig.add_subplot(gs[1, 0])
            if 'monthly' in report['periods'] and report['periods']['monthly']['net_changes_by_role']:
                role_changes = report['periods']['monthly']['net_changes_by_role']
                sorted_roles = sorted(role_changes.items(), 
                                    key=lambda x: x[1]['added'], reverse=True)[:8]
                
                if sorted_roles:
                    roles, changes = zip(*sorted_roles)
                    values = [change['added'] for change in changes]
                    
                    bars = ax3.barh(roles, values, color='#3498db', alpha=0.8)
                    ax3.set_title('Top Roles by Additions (Monthly)')
                    ax3.grid(True, alpha=0.3, axis='x')
                    
                    # Add value labels on bars
                    for bar, value in zip(bars, values):
                        if value > 0:
                            ax3.text(value + 0.1, bar.get_y() + bar.get_height()/2, 
                                   str(value), va='center', fontsize=9)
                else:
                    ax3.text(0.5, 0.5, 'No role data', ha='center', va='center')
                    ax3.set_title('Top Roles by Additions (Monthly)')
            else:
                ax3.text(0.5, 0.5, 'No role data', ha='center', va='center')
                ax3.set_title('Top Roles by Additions (Monthly)')
            
            # 4. User Activity Distribution (middle right)
            ax4 = fig.add_subplot(gs[1, 1])
            if 'weekly' in report['periods'] and report['periods']['weekly']['user_activity']:
                user_activity = report['periods']['weekly']['user_activity']
                activity_counts = [
                    (data.get('roles_added', 0) or 0) + (data.get('roles_removed', 0) or 0) 
                    for data in user_activity.values()
                ]
                
                if activity_counts and max(activity_counts) > 0:
                    ax4.hist(activity_counts, bins=min(10, len(set(activity_counts))), 
                           color='#9b59b6', alpha=0.7, edgecolor='black')
                    ax4.set_title('User Activity Distribution')
                    ax4.set_xlabel('Total Role Changes')
                    ax4.set_ylabel('Number of Users')
                    ax4.grid(True, alpha=0.3)
                else:
                    ax4.text(0.5, 0.5, 'No user activity', ha='center', va='center')
                    ax4.set_title('User Activity Distribution')
            else:
                ax4.text(0.5, 0.5, 'No user activity', ha='center', va='center')
                ax4.set_title('User Activity Distribution')
            
            # 5. Source Breakdown (bottom span)
            ax5 = fig.add_subplot(gs[2, :])
            all_sources = {}
            for period_data in report['periods'].values():
                for source, counts in period_data.get('source_breakdown', {}).items():
                    if source not in all_sources:
                        all_sources[source] = {'added': 0, 'removed': 0}
                    all_sources[source]['added'] += (counts.get('added', 0) or 0)
                    all_sources[source]['removed'] += (counts.get('removed', 0) or 0)
            
            if all_sources:
                sources = list(all_sources.keys())
                added_counts = [all_sources[s]['added'] for s in sources]
                removed_counts = [all_sources[s]['removed'] for s in sources]
                
                x = range(len(sources))
                width = 0.35
                ax5.bar([i - width/2 for i in x], added_counts, 
                       width, label='Added', color='#2ecc71', alpha=0.8)
                ax5.bar([i + width/2 for i in x], removed_counts, 
                       width, label='Removed', color='#e74c3c', alpha=0.8)
                ax5.set_xticks(x)
                ax5.set_xticklabels([s.replace('_', ' ').title() for s in sources])
                ax5.set_title('Activity Sources Overview')
                ax5.legend()
                ax5.grid(True, alpha=0.3)
                ax5.tick_params(axis='x', rotation=45)
            else:
                ax5.text(0.5, 0.5, 'No source data available', ha='center', va='center')
                ax5.set_title('Activity Sources Overview')
            
        except Exception as e:
            # If there's an error with specific charts, create a simple summary
            ax_error = fig.add_subplot(gs[:, :])
            ax_error.text(0.5, 0.5, f'Dashboard generation error: {str(e)}', 
                         ha='center', va='center', fontsize=12)
            ax_error.set_title('Dashboard Error')
        
        plt.tight_layout()
        
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        plt.close()
        
        return buffer
    
    async def create_enhanced_report_embed(self, guild_id: int, guild_name: str = None, 
                                         chart_type: str = 'dashboard') -> tuple[discord.Embed, discord.File]:
        """Create an enhanced embed with graphs"""
        embed = discord.Embed(
            title="Advanced Analytics Dashboard",
            description=f"Comprehensive visual analytics for **{guild_name or 'Server'}**",
            color=0x2ecc71,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Generate the appropriate chart
        if chart_type == 'dashboard':
            chart_buffer = await self.generate_comprehensive_dashboard(guild_id, guild_name)
            filename = "dashboard.png"
            embed.set_image(url=f"attachment://{filename}")
        elif chart_type == 'timeline':
            chart_buffer = await self.generate_activity_timeline_chart(guild_id, 7)
            filename = "timeline.png"
            embed.set_image(url=f"attachment://{filename}")
        elif chart_type == 'distribution':
            chart_buffer = await self.generate_role_distribution_chart(guild_id, 30)
            filename = "distribution.png"
            embed.set_image(url=f"attachment://{filename}")
        elif chart_type == 'heatmap':
            chart_buffer = await self.generate_user_activity_heatmap(guild_id, 30)
            filename = "heatmap.png"
            embed.set_image(url=f"attachment://{filename}")
        elif chart_type == 'trends':
            chart_buffer = await self.generate_trend_analysis_chart(guild_id, 30)
            filename = "trends.png"
            embed.set_image(url=f"attachment://{filename}")
        else:
            chart_buffer = await self.generate_comprehensive_dashboard(guild_id, guild_name)
            filename = "dashboard.png"
            embed.set_image(url=f"attachment://{filename}")
        
        # Add summary statistics
        report = await self.generate_comprehensive_report(guild_id, 'all')
        
        total_events = sum(period['summary'].get('total_events', 0) 
                          for period in report['periods'].values())
        total_added = sum(period['summary'].get('roles_added', 0) 
                         for period in report['periods'].values())
        total_removed = sum(period['summary'].get('roles_removed', 0) 
                           for period in report['periods'].values())
        
        embed.add_field(
            name="Quick Stats",
            value=f"**Total Events:** {total_events:,}\n"
                  f"**Roles Added:** {total_added:,}\n"
                  f"**Roles Removed:** {total_removed:,}\n"
                  f"**Net Growth:** {total_added - total_removed:+,}",
            inline=True
        )
        
        embed.add_field(
            name="Chart Information",
            value=f"**Current:** {chart_type.title()}\n"
                  f"**Generated:** <t:{int(datetime.now().timestamp())}:R>\n"
                  f"**Resolution:** High (150 DPI)\n"
                  f"**Format:** PNG",
            inline=True
        )
        
        embed.set_footer(text="Use the buttons below to switch between different chart types")
        
        file = discord.File(chart_buffer, filename=filename)
        return embed, file


class AdvancedReportView(discord.ui.View):
    """Interactive view for advanced reports with buttons and navigation"""
    
    def __init__(self, reporter: ReportGenerator, guild_id: int, report_data: Dict[str, Any]):
        super().__init__(timeout=300)  # 5 minute timeout
        self.reporter = reporter
        self.guild_id = guild_id
        self.report_data = report_data
        self.current_view = 'overview'
        self.current_period = 'daily'
    
    @discord.ui.button(label='📊 Overview', style=discord.ButtonStyle.primary, emoji='📊')
    async def overview_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show overview dashboard"""
        embed, _ = await self.reporter.create_advanced_report_embed(
            self.guild_id, interaction.guild.name, 'all'
        )
        self.current_view = 'overview'
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label='📅 Daily', style=discord.ButtonStyle.secondary, emoji='📅')
    async def daily_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show daily detailed report"""
        if 'daily' in self.report_data['periods']:
            embed = self.reporter.create_detailed_period_embed(
                self.report_data['periods']['daily'], interaction.guild.name
            )
            self.current_view = 'daily'
            self.current_period = 'daily'
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.send_message("No daily data available.", ephemeral=True)
    
    @discord.ui.button(label='📆 Weekly', style=discord.ButtonStyle.secondary, emoji='📆')
    async def weekly_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show weekly detailed report"""
        if 'weekly' in self.report_data['periods']:
            embed = self.reporter.create_detailed_period_embed(
                self.report_data['periods']['weekly'], interaction.guild.name
            )
            self.current_view = 'weekly'
            self.current_period = 'weekly'
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.send_message("No weekly data available.", ephemeral=True)
    
    @discord.ui.button(label='📋 Monthly', style=discord.ButtonStyle.secondary, emoji='📋')
    async def monthly_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show monthly detailed report"""
        if 'monthly' in self.report_data['periods']:
            embed = self.reporter.create_detailed_period_embed(
                self.report_data['periods']['monthly'], interaction.guild.name
            )
            self.current_view = 'monthly'
            self.current_period = 'monthly'
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.send_message("No monthly data available.", ephemeral=True)
    
    @discord.ui.button(label='👥 Users', style=discord.ButtonStyle.success, emoji='👥')
    async def users_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show user analytics"""
        period_data = self.report_data['periods'].get(self.current_period)
        if period_data:
            embed = self.reporter.create_user_analytics_embed(
                period_data, interaction.guild.name
            )
            self.current_view = 'users'
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.send_message("No user data available.", ephemeral=True)
    
    @discord.ui.select(
        placeholder="Choose analysis period...",
        options=[
            discord.SelectOption(label="Daily Analysis", value="daily", emoji="📅"),
            discord.SelectOption(label="Weekly Analysis", value="weekly", emoji="📆"),
            discord.SelectOption(label="Monthly Analysis", value="monthly", emoji="📋"),
        ]
    )
    async def period_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        """Period selection dropdown"""
        selected_period = select.values[0]
        
        if selected_period in self.report_data['periods']:
            if self.current_view == 'users':
                embed = self.reporter.create_user_analytics_embed(
                    self.report_data['periods'][selected_period], interaction.guild.name
                )
            else:
                embed = self.reporter.create_detailed_period_embed(
                    self.report_data['periods'][selected_period], interaction.guild.name
                )
            
            self.current_period = selected_period
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.send_message(f"No {selected_period} data available.", ephemeral=True)
    
    async def on_timeout(self):
        """Disable all buttons when view times out"""
        for item in self.children:
            item.disabled = True


class LiveDashboardView(discord.ui.View):
    """Interactive view for live dashboard with refresh functionality"""
    
    def __init__(self, tracker_cog, guild_id: int):
        super().__init__(timeout=600)  # 10 minute timeout
        self.tracker_cog = tracker_cog
        self.guild_id = guild_id
    
    @discord.ui.button(label='🔄 Refresh', style=discord.ButtonStyle.primary, emoji='🔄')
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Refresh the dashboard with latest data"""
        await interaction.response.defer()
        
        try:
            # Recreate the dashboard embed with fresh data
            embed = discord.Embed(
                title="📊 Live Analytics Dashboard",
                description=f"Real-time insights for **{interaction.guild.name}**",
                color=0x00ff00,
                timestamp=datetime.now(timezone.utc)
            )
            
            # Get current statistics
            recent_joiners_count = len(self.tracker_cog.recent_joins)
            total_events = len(await self.tracker_cog.db.get_role_events(self.guild_id))
            
            # Get recent activity (last hour)
            one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
            recent_events = await self.tracker_cog.db.get_role_events(self.guild_id, one_hour_ago)
            recent_activity = len(recent_events)
            
            # Get today's stats
            today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            today_events = await self.tracker_cog.db.get_role_events(self.guild_id, today_start)
            today_stats = await self.tracker_cog.db.get_summary_stats(self.guild_id, today_start)
            
            # Live metrics
            embed.add_field(
                name="🔴 Live Metrics",
                value=f"**Monitoring:** {recent_joiners_count} new members\n"
                      f"**Last Hour:** {recent_activity} events\n"
                      f"**Status:** {'🟢 Active' if recent_activity > 0 else '🟡 Quiet'}\n"
                      f"**Uptime:** 24/7 🤖",
                inline=True
            )
            
            # Today's performance
            today_added = today_stats.get('roles_added', 0)
            today_removed = today_stats.get('roles_removed', 0)
            today_users = today_stats.get('unique_users', 0)
            
            embed.add_field(
                name="📅 Today's Performance",
                value=f"**Events:** {len(today_events)}\n"
                      f"**Roles Added:** {today_added} ✅\n"
                      f"**Roles Removed:** {today_removed} ❌\n"
                      f"**Active Users:** {today_users}",
                inline=True
            )
            
            # System health
            detection_window_hours = int(self.tracker_cog.onboarding_detection_window.total_seconds() // 3600)
            embed.add_field(
                name="⚙️ System Health",
                value=f"**Detection Window:** {detection_window_hours}h\n"
                      f"**Min Roles Required:** {self.tracker_cog.min_roles_for_completion}\n"
                      f"**Database:** 🟢 Connected\n"
                      f"**Auto-Detection:** 🟢 Active",
                inline=True
            )
            
            # Recent activity feed
            if recent_events:
                activity_text = ""
                for event in recent_events[-5:]:  # Last 5 events
                    timestamp = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
                    action_emoji = "✅" if event['event_type'] == 'added' else "❌"
                    time_ago = datetime.now(timezone.utc) - timestamp
                    minutes_ago = int(time_ago.total_seconds() // 60)
                    activity_text += f"{action_emoji} **{event['username']}** {event['event_type']} **{event['role_name']}** ({minutes_ago}m ago)\n"
                
                embed.add_field(
                    name="⚡ Recent Activity",
                    value=activity_text if activity_text else "No recent activity",
                    inline=False
                )
            
            # Performance indicators with visual bars
            if total_events > 0:
                success_rate = (today_added / max(1, len(today_events))) * 100
                activity_level = min(100, recent_activity * 25)  # Scale activity
                
                success_bar = "█" * int(success_rate / 10) + "░" * (10 - int(success_rate / 10))
                activity_bar = "█" * int(activity_level / 10) + "░" * (10 - int(activity_level / 10))
                
                embed.add_field(
                    name="📊 Performance Indicators",
                    value=f"**Success Rate:** {success_bar} {success_rate:.1f}%\n"
                          f"**Activity Level:** {activity_bar} {activity_level:.0f}%",
                    inline=False
                )
            
            embed.set_footer(
                text="🔄 Dashboard refreshed • Use /tracker report advanced for interactive analytics",
                icon_url=interaction.guild.icon.url if interaction.guild.icon else None
            )
            
            await interaction.edit_original_response(embed=embed, view=self)
            
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Refresh Error",
                description=f"Failed to refresh dashboard: {str(e)}",
                color=0xe74c3c
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)
    
    @discord.ui.button(label='📊 Advanced Report', style=discord.ButtonStyle.success, emoji='📊')
    async def advanced_report_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Switch to advanced interactive report"""
        await interaction.response.defer()
        
        try:
            from reports import ReportGenerator
            reporter = ReportGenerator(self.tracker_cog.db)
            embed, view = await reporter.create_advanced_report_embed(
                self.guild_id, interaction.guild.name, 'all'
            )
            await interaction.edit_original_response(embed=embed, view=view)
            
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Report Error",
                description=f"Failed to generate advanced report: {str(e)}",
                color=0xe74c3c
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)
    
    async def on_timeout(self):
        """Disable all buttons when view times out"""
        for item in self.children:
            item.disabled = True
