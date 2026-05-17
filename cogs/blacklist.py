import discord
from discord.ext import commands
from discord import app_commands
from utils.db import get_db, get_config, is_sa_tester


class Blacklist(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="blacklist", description="Blacklist a player from tier testing (SA Tester only)")
    @app_commands.describe(user="The player to blacklist", reason="Reason for blacklist")
    async def blacklist(self, interaction: discord.Interaction, user: discord.Member, reason: str):
        config = get_config(interaction.guild.id)
        if not config:
            await interaction.response.send_message("❌ Bot not set up yet.", ephemeral=True)
            return
        if not is_sa_tester(interaction.user, config):
            await interaction.response.send_message("❌ Only SA Testers can blacklist players.", ephemeral=True)
            return
        if user.id == interaction.user.id:
            await interaction.response.send_message("❌ You can't blacklist yourself.", ephemeral=True)
            return

        conn = get_db()
        existing = conn.execute(
            "SELECT * FROM blacklist WHERE guild_id = ? AND user_id = ?",
            (str(interaction.guild.id), str(user.id))
        ).fetchone()
        if existing:
            conn.close()
            await interaction.response.send_message(f"❌ {user.mention} is already blacklisted.", ephemeral=True)
            return

        conn.execute(
            "INSERT INTO blacklist (guild_id, user_id, reason, banned_by) VALUES (?, ?, ?, ?)",
            (str(interaction.guild.id), str(user.id), reason, str(interaction.user.id))
        )
        # Also remove from queue if they're in it
        conn.execute(
            "DELETE FROM queue WHERE guild_id = ? AND user_id = ? AND status = 'waiting'",
            (str(interaction.guild.id), str(user.id))
        )
        conn.commit()
        conn.close()

        # Remove In Queue role if they have it
        in_queue_role = discord.utils.get(interaction.guild.roles, name="In Queue")
        if in_queue_role and in_queue_role in user.roles:
            await user.remove_roles(in_queue_role)

        embed = discord.Embed(
            title="🔨 Player Blacklisted",
            color=discord.Color.red()
        )
        embed.add_field(name="Player", value=user.mention, inline=True)
        embed.add_field(name="Blacklisted By", value=interaction.user.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_footer(text="Ranked Tests • Blacklist")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="unblacklist", description="Remove a player from the blacklist (SA Tester only)")
    @app_commands.describe(user="The player to unblacklist")
    async def unblacklist(self, interaction: discord.Interaction, user: discord.Member):
        config = get_config(interaction.guild.id)
        if not config:
            await interaction.response.send_message("❌ Bot not set up yet.", ephemeral=True)
            return
        if not is_sa_tester(interaction.user, config):
            await interaction.response.send_message("❌ Only SA Testers can unblacklist players.", ephemeral=True)
            return

        conn = get_db()
        row = conn.execute(
            "SELECT * FROM blacklist WHERE guild_id = ? AND user_id = ?",
            (str(interaction.guild.id), str(user.id))
        ).fetchone()
        if not row:
            conn.close()
            await interaction.response.send_message(f"❌ {user.mention} is not blacklisted.", ephemeral=True)
            return

        conn.execute(
            "DELETE FROM blacklist WHERE guild_id = ? AND user_id = ?",
            (str(interaction.guild.id), str(user.id))
        )
        conn.commit()
        conn.close()

        embed = discord.Embed(
            title="✅ Player Unblacklisted",
            description=f"{user.mention} has been removed from the blacklist.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="blacklistcheck", description="Check if a player is blacklisted")
    @app_commands.describe(user="The player to check")
    async def blacklist_check(self, interaction: discord.Interaction, user: discord.Member):
        conn = get_db()
        row = conn.execute(
            "SELECT * FROM blacklist WHERE guild_id = ? AND user_id = ?",
            (str(interaction.guild.id), str(user.id))
        ).fetchone()
        conn.close()

        if row:
            banned_by = interaction.guild.get_member(int(row["banned_by"]))
            embed = discord.Embed(title="🔨 Blacklisted", color=discord.Color.red())
            embed.add_field(name="Player", value=user.mention, inline=True)
            embed.add_field(name="Blacklisted By", value=banned_by.mention if banned_by else row["banned_by"], inline=True)
            embed.add_field(name="Reason", value=row["reason"], inline=False)
            embed.add_field(name="Date", value=row["banned_at"][:10], inline=True)
        else:
            embed = discord.Embed(
                title="✅ Not Blacklisted",
                description=f"{user.mention} is not blacklisted.",
                color=discord.Color.green()
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="blacklistlist", description="View all blacklisted players (SA Tester only)")
    async def blacklist_list(self, interaction: discord.Interaction):
        config = get_config(interaction.guild.id)
        if not is_sa_tester(interaction.user, config):
            await interaction.response.send_message("❌ Only SA Testers can view the blacklist.", ephemeral=True)
            return

        conn = get_db()
        rows = conn.execute(
            "SELECT * FROM blacklist WHERE guild_id = ? ORDER BY banned_at DESC",
            (str(interaction.guild.id),)
        ).fetchall()
        conn.close()

        embed = discord.Embed(title="🔨 Blacklist", color=discord.Color.red())
        if not rows:
            embed.description = "*No blacklisted players.*"
        else:
            lines = []
            for row in rows:
                member = interaction.guild.get_member(int(row["user_id"]))
                name = member.mention if member else f"<@{row['user_id']}>"
                lines.append(f"{name} — {row['reason']}")
            embed.description = "\n".join(lines)
        embed.set_footer(text=f"{len(rows)} player(s) blacklisted")
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Blacklist(bot))
