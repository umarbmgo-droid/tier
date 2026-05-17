import discord
from discord.ext import commands
from discord import app_commands
from utils.db import get_db, get_config, is_any_tester, TIERS
from cogs.setup import _refresh_queue_channel


class Queue(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="queue", description="View the current tier test queue")
    async def view_queue(self, interaction: discord.Interaction):
        config = get_config(interaction.guild.id)
        if not config:
            await interaction.response.send_message("❌ Bot not set up yet.", ephemeral=True)
            return

        conn = get_db()
        rows = conn.execute(
            "SELECT * FROM queue WHERE guild_id = ? AND status = 'waiting' ORDER BY joined_at ASC",
            (str(interaction.guild.id),)
        ).fetchall()
        conn.close()

        embed = discord.Embed(title="📋 Current Queue", color=discord.Color.blurple())
        if not rows:
            embed.description = "*Queue is empty!*"
        else:
            lines = []
            for i, row in enumerate(rows, 1):
                member = interaction.guild.get_member(int(row["user_id"]))
                name = member.mention if member else f"<@{row['user_id']}>"
                lines.append(f"`#{i}` {name} — **{row['ign']}**")
            embed.description = "\n".join(lines)
        embed.set_footer(text=f"{len(rows)} player(s) waiting")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="leavequeue", description="Leave the tier test queue")
    async def leave_queue(self, interaction: discord.Interaction):
        config = get_config(interaction.guild.id)
        conn = get_db()
        row = conn.execute(
            "SELECT * FROM queue WHERE guild_id = ? AND user_id = ? AND status = 'waiting'",
            (str(interaction.guild.id), str(interaction.user.id))
        ).fetchone()
        if not row:
            conn.close()
            await interaction.response.send_message("❌ You're not in the queue.", ephemeral=True)
            return

        conn.execute(
            "DELETE FROM queue WHERE guild_id = ? AND user_id = ? AND status = 'waiting'",
            (str(interaction.guild.id), str(interaction.user.id))
        )
        conn.commit()
        conn.close()

        in_queue_role = discord.utils.get(interaction.guild.roles, name="In Queue")
        if in_queue_role and in_queue_role in interaction.user.roles:
            await interaction.user.remove_roles(in_queue_role)

        if config:
            await _refresh_queue_channel(interaction.guild, config)

        await interaction.response.send_message("✅ You've left the queue.", ephemeral=True)

    @app_commands.command(name="claim", description="Claim the next player in queue to test (Testers only)")
    async def claim(self, interaction: discord.Interaction):
        config = get_config(interaction.guild.id)
        if not config:
            await interaction.response.send_message("❌ Bot not set up yet.", ephemeral=True)
            return
        if not is_any_tester(interaction.user, config):
            await interaction.response.send_message("❌ You don't have permission to claim tests.", ephemeral=True)
            return

        conn = get_db()
        row = conn.execute(
            "SELECT * FROM queue WHERE guild_id = ? AND status = 'waiting' ORDER BY joined_at ASC LIMIT 1",
            (str(interaction.guild.id),)
        ).fetchone()
        if not row:
            conn.close()
            await interaction.response.send_message("❌ The queue is empty.", ephemeral=True)
            return

        member = interaction.guild.get_member(int(row["user_id"]))
        if not member:
            conn.execute("DELETE FROM queue WHERE id = ?", (row["id"],))
            conn.commit()
            conn.close()
            await interaction.response.send_message("⚠️ That player left the server. Removed from queue.", ephemeral=True)
            return

        # Mark as claimed in queue
        conn.execute("UPDATE queue SET status = 'claimed' WHERE id = ?", (row["id"],))
        conn.commit()
        conn.close()

        # Create ticket channel
        category = interaction.guild.get_channel(int(config["ticket_category_id"]))
        sa_role = interaction.guild.get_role(int(config["sa_tester_role_id"]))
        as_role = interaction.guild.get_role(int(config["as_tester_role_id"]))

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
            sa_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            as_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }

        ticket_channel = await interaction.guild.create_text_channel(
            name=f"test-{row['ign'].lower()}",
            category=category,
            overwrites=overwrites,
            reason=f"Tier test for {row['ign']}"
        )

        # Save ticket to DB
        conn = get_db()
        conn.execute(
            "INSERT INTO tickets (guild_id, channel_id, user_id, tester_id, ign, status) VALUES (?, ?, ?, ?, ?, 'open')",
            (str(interaction.guild.id), str(ticket_channel.id), str(member.id), str(interaction.user.id), row["ign"])
        )
        conn.commit()
        conn.close()

        # Remove In Queue role
        in_queue_role = discord.utils.get(interaction.guild.roles, name="In Queue")
        if in_queue_role and in_queue_role in member.roles:
            await member.remove_roles(in_queue_role)

        # Refresh queue channel
        await _refresh_queue_channel(interaction.guild, config)

        # Post ticket embed
        embed = discord.Embed(
            title="🎮 Tier Test Started",
            description=(
                f"**Player:** {member.mention}\n"
                f"**IGN:** `{row['ign']}`\n"
                f"**Tester:** {interaction.user.mention}\n\n"
                "The tester will begin shortly. Please be patient and follow instructions.\n\n"
                "Once the test is complete, the tester will submit your result."
            ),
            color=discord.Color.gold()
        )
        embed.set_footer(text="Ranked Tests • BlockMango Tier Testing")

        view = TicketControls()
        await ticket_channel.send(content=f"{member.mention} {interaction.user.mention}", embed=embed, view=view)
        await interaction.response.send_message(
            f"✅ Claimed **{row['ign']}**! Ticket: {ticket_channel.mention}", ephemeral=True
        )

    @app_commands.command(name="clearqueue", description="Clear the entire queue (SA Tester only)")
    async def clear_queue(self, interaction: discord.Interaction):
        config = get_config(interaction.guild.id)
        if not config:
            await interaction.response.send_message("❌ Bot not set up yet.", ephemeral=True)
            return

        sa_role = interaction.guild.get_role(int(config["sa_tester_role_id"]))
        if not sa_role or sa_role not in interaction.user.roles:
            await interaction.response.send_message("❌ Only SA Testers can clear the queue.", ephemeral=True)
            return

        conn = get_db()
        conn.execute("DELETE FROM queue WHERE guild_id = ? AND status = 'waiting'", (str(interaction.guild.id),))
        conn.commit()
        conn.close()

        # Remove In Queue roles from all members
        in_queue_role = discord.utils.get(interaction.guild.roles, name="In Queue")
        if in_queue_role:
            for member in in_queue_role.members:
                try:
                    await member.remove_roles(in_queue_role)
                except Exception:
                    pass

        await _refresh_queue_channel(interaction.guild, config)
        await interaction.response.send_message("✅ Queue cleared.", ephemeral=True)


class TicketControls(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Submit Result", style=discord.ButtonStyle.green, custom_id="submit_result", emoji="✅")
    async def submit_result(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = get_config(interaction.guild.id)
        if not is_any_tester(interaction.user, config):
            await interaction.response.send_message("❌ Only testers can submit results.", ephemeral=True)
            return
        await interaction.response.send_modal(ResultModal())

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.red, custom_id="close_ticket", emoji="🔒")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = get_config(interaction.guild.id)
        if not is_any_tester(interaction.user, config):
            await interaction.response.send_message("❌ Only testers can close tickets.", ephemeral=True)
            return

        conn = get_db()
        conn.execute(
            "UPDATE tickets SET status = 'closed' WHERE guild_id = ? AND channel_id = ?",
            (str(interaction.guild.id), str(interaction.channel.id))
        )
        conn.commit()
        conn.close()

        await interaction.response.send_message("🔒 Closing ticket in 5 seconds...")
        import asyncio
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete()
        except Exception:
            pass


class ResultModal(discord.ui.Modal, title="Submit Tier Result"):
    tier = discord.ui.TextInput(
        label="Tier (HT1-HT3, LT1-LT5)",
        placeholder="e.g. LT2",
        min_length=2,
        max_length=3
    )
    notes = discord.ui.TextInput(
        label="Notes (optional)",
        placeholder="e.g. Good movement, needs more practice",
        required=False,
        style=discord.TextStyle.paragraph,
        max_length=500
    )

    async def on_submit(self, interaction: discord.Interaction):
        tier_input = self.tier.value.upper().strip()
        if tier_input not in TIERS:
            await interaction.response.send_message(
                f"❌ Invalid tier. Valid tiers: {', '.join(TIERS)}", ephemeral=True
            )
            return

        config = get_config(interaction.guild.id)
        conn = get_db()

        ticket = conn.execute(
            "SELECT * FROM tickets WHERE guild_id = ? AND channel_id = ? AND status = 'open'",
            (str(interaction.guild.id), str(interaction.channel.id))
        ).fetchone()
        if not ticket:
            conn.close()
            await interaction.response.send_message("❌ No open ticket found in this channel.", ephemeral=True)
            return

        member = interaction.guild.get_member(int(ticket["user_id"]))

        # Save result
        conn.execute(
            "INSERT INTO results (guild_id, user_id, ign, tier, tester_id, notes) VALUES (?, ?, ?, ?, ?, ?)",
            (str(interaction.guild.id), ticket["user_id"], ticket["ign"], tier_input,
             str(interaction.user.id), self.notes.value)
        )
        conn.execute(
            "UPDATE tickets SET status = 'completed' WHERE id = ?", (ticket["id"],)
        )
        conn.commit()
        conn.close()

        # Give tier role + Tested role
        if member:
            # Remove old tier roles
            for t in TIERS:
                r = discord.utils.get(interaction.guild.roles, name=t)
                if r and r in member.roles:
                    await member.remove_roles(r)

            # Add new tier role
            conn2 = get_db()
            tier_role_row = conn2.execute(
                "SELECT role_id FROM tier_roles WHERE guild_id = ? AND tier = ?",
                (str(interaction.guild.id), tier_input)
            ).fetchone()
            conn2.close()
            if tier_role_row:
                tier_role = interaction.guild.get_role(int(tier_role_row["role_id"]))
                if tier_role:
                    await member.add_roles(tier_role)

            tested_role = interaction.guild.get_role(int(config["tested_role_id"])) if config else None
            if tested_role:
                await member.add_roles(tested_role)

        # Post in results channel
        from utils.db import TIER_COLORS
        results_channel = interaction.guild.get_channel(int(config["results_channel_id"]))
        embed = discord.Embed(
            title="🏆 Tier Test Result",
            color=discord.Color(TIER_COLORS.get(tier_input, 0xFFFFFF))
        )
        embed.add_field(name="Player", value=member.mention if member else ticket["user_id"], inline=True)
        embed.add_field(name="IGN", value=f"`{ticket['ign']}`", inline=True)
        embed.add_field(name="Tier", value=f"**{tier_input}**", inline=True)
        embed.add_field(name="Tester", value=interaction.user.mention, inline=True)
        if self.notes.value:
            embed.add_field(name="Notes", value=self.notes.value, inline=False)
        embed.set_footer(text="Ranked Tests • BlockMango Tier Testing")
        if results_channel:
            await results_channel.send(embed=embed)

        await interaction.response.send_message(
            f"✅ Result submitted! **{ticket['ign']}** → **{tier_input}**\nClosing ticket in 10 seconds..."
        )
        import asyncio
        await asyncio.sleep(10)
        try:
            await interaction.channel.delete()
        except Exception:
            pass


async def setup(bot):
    await bot.add_cog(Queue(bot))
    bot.add_view(TicketControls())
