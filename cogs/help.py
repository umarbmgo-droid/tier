import discord
from discord.ext import commands
from discord import app_commands
from utils.db import get_config, is_any_tester, is_sa_tester
import time

BOT_START_TIME = time.time()


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="View all Ranked Tests commands")
    async def help(self, interaction: discord.Interaction):
        config = get_config(interaction.guild.id)
        is_tester = is_any_tester(interaction.user, config) if config else False
        is_sa = is_sa_tester(interaction.user, config) if config else False
        is_owner = interaction.user.id == 253335267618848778

        embed = discord.Embed(
            title="📖 Ranked Tests — Help",
            description="BlockMango tier testing bot. Use the button in `📥︱request-test` to join the queue!",
            color=discord.Color.gold()
        )

        # Player commands
        embed.add_field(
            name="👤 Player Commands",
            value=(
                "`/queue` — View the current test queue\n"
                "`/leavequeue` — Leave the queue\n"
                "`/profile [user]` — View your or someone's tier profile\n"
                "`/appeal` — Appeal your tier result\n"
                "`/blacklistcheck <user>` — Check if someone is blacklisted\n"
                "`/ping` — Check the bot's latency\n"
                "`/uptime` — Check how long the bot has been online"
            ),
            inline=False
        )

        # Tester commands
        if is_tester or is_sa or is_owner:
            embed.add_field(
                name="🎮 Tester Commands (AS Tester+)",
                value=(
                    "`/claim` — Claim the next player in queue\n"
                    "**Submit Result** button — Submit a tier result inside a ticket\n"
                    "**Close Ticket** button — Close a test ticket"
                ),
                inline=False
            )

        # SA Tester commands
        if is_sa or is_owner:
            embed.add_field(
                name="⭐ SA Tester Commands",
                value=(
                    "`/addtester <user> <role>` — Give SA/AS Tester role\n"
                    "`/removetester <user> <role>` — Remove SA/AS Tester role\n"
                    "`/setresult <user> <ign> <tier>` — Manually set a player's tier\n"
                    "`/clearqueue` — Clear the entire queue\n"
                    "`/blacklist <user> <reason>` — Blacklist a player\n"
                    "`/unblacklist <user>` — Remove a player from the blacklist\n"
                    "`/blacklistlist` — View all blacklisted players\n"
                    "**Accept/Deny Appeal** buttons — Handle tier appeals"
                ),
                inline=False
            )

        # Owner commands
        if is_owner:
            embed.add_field(
                name="👑 Owner Commands",
                value="`/setup` — Set up the bot (creates all roles & channels)",
                inline=False
            )

        # Tiers
        embed.add_field(
            name="🏆 Available Tiers",
            value="`HT1` `HT2` `HT3` `HT4` `HT5` *(High Tier)*  |  `LT1` `LT2` `LT3` `LT4` `LT5` *(Low Tier)*",
            inline=False
        )

        embed.set_footer(text="Ranked Tests • BlockMango Tier Testing")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="ping", description="Check the bot's latency")
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)

        if latency < 100:
            color = discord.Color.green()
            status = "🟢 Excellent"
        elif latency < 200:
            color = discord.Color.yellow()
            status = "🟡 Good"
        else:
            color = discord.Color.red()
            status = "🔴 High"

        embed = discord.Embed(title="🏓 Pong!", color=color)
        embed.add_field(name="Latency", value=f"`{latency}ms`", inline=True)
        embed.add_field(name="Status", value=status, inline=True)
        embed.set_footer(text="Ranked Tests • BlockMango Tier Testing")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="uptime", description="Check how long the bot has been online")
    async def uptime(self, interaction: discord.Interaction):
        uptime_seconds = int(time.time() - BOT_START_TIME)

        days = uptime_seconds // 86400
        hours = (uptime_seconds % 86400) // 3600
        minutes = (uptime_seconds % 3600) // 60
        seconds = uptime_seconds % 60

        parts = []
        if days: parts.append(f"{days}d")
        if hours: parts.append(f"{hours}h")
        if minutes: parts.append(f"{minutes}m")
        parts.append(f"{seconds}s")

        uptime_str = " ".join(parts)

        embed = discord.Embed(title="⏱️ Uptime", color=discord.Color.blurple())
        embed.add_field(name="Online For", value=f"`{uptime_str}`", inline=True)
        embed.add_field(name="Bot", value=f"`{self.bot.user.name}`", inline=True)
        embed.set_footer(text="Ranked Tests • BlockMango Tier Testing")
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Help(bot))

