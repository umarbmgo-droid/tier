import discord
from discord.ext import commands
from discord import app_commands
from utils.db import get_db, get_config, OWNER_ID, TIERS, TIER_COLORS


class Setup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setup", description="Set up the Ranked Tests bot (Owner only)")
    async def setup(self, interaction: discord.Interaction):
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ Only the server owner can run `/setup`.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        msgs = []

        # ── Roles ──────────────────────────────────────────────────────────────
        msgs.append("**Creating roles...**")

        sa_role = await guild.create_role(
            name="SA Tester",
            color=discord.Color.gold(),
            hoist=True,
            reason="Ranked Tests setup"
        )
        as_role = await guild.create_role(
            name="AS Tester",
            color=discord.Color.blue(),
            hoist=True,
            reason="Ranked Tests setup"
        )
        tested_role = await guild.create_role(
            name="Tested",
            color=discord.Color.green(),
            reason="Ranked Tests setup"
        )
        queued_role = await guild.create_role(
            name="In Queue",
            color=discord.Color.light_grey(),
            reason="Ranked Tests setup"
        )

        # Tier roles
        tier_roles = {}
        for tier in TIERS:
            color = discord.Color(TIER_COLORS[tier])
            role = await guild.create_role(name=tier, color=color, reason="Ranked Tests setup")
            tier_roles[tier] = role

        msgs.append(f"✅ Created roles: SA Tester, AS Tester, Tested, In Queue, {', '.join(TIERS)}")

        # ── Category ───────────────────────────────────────────────────────────
        tester_overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            sa_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
            as_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }

        ticket_category = await guild.create_category(
            name="🎮 Test Tickets",
            overwrites=tester_overwrites,
            reason="Ranked Tests setup"
        )
        msgs.append(f"✅ Created category: **{ticket_category.name}**")

        # ── Channels ───────────────────────────────────────────────────────────

        # Queue channel (everyone can see, only bot posts)
        queue_channel = await guild.create_text_channel(
            name="📋︱queue",
            overwrites={
                guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
                sa_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                as_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            },
            reason="Ranked Tests setup"
        )

        # Panel channel (everyone can see and interact via buttons)
        panel_channel = await guild.create_text_channel(
            name="📥︱request-test",
            overwrites={
                guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
            },
            reason="Ranked Tests setup"
        )

        # Results channel
        results_channel = await guild.create_text_channel(
            name="🏆︱tier-results",
            overwrites={
                guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
                sa_role: discord.PermissionOverwrite(send_messages=True),
                as_role: discord.PermissionOverwrite(send_messages=True),
            },
            reason="Ranked Tests setup"
        )

        # Appeals channel
        appeals_channel = await guild.create_text_channel(
            name="📢︱appeals",
            overwrites={
                guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
                sa_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            },
            reason="Ranked Tests setup"
        )

        msgs.append(f"✅ Created channels: queue, request-test, tier-results, appeals")

        # ── Save to DB ─────────────────────────────────────────────────────────
        conn = get_db()
        conn.execute("""
            INSERT OR REPLACE INTO config
            (guild_id, panel_channel_id, results_channel_id, appeals_channel_id,
             ticket_category_id, queue_channel_id, sa_tester_role_id, as_tester_role_id, tested_role_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(guild.id),
            str(panel_channel.id),
            str(results_channel.id),
            str(appeals_channel.id),
            str(ticket_category.id),
            str(queue_channel.id),
            str(sa_role.id),
            str(as_role.id),
            str(tested_role.id),
        ))
        for tier, role in tier_roles.items():
            conn.execute("""
                INSERT OR REPLACE INTO tier_roles (guild_id, tier, role_id)
                VALUES (?, ?, ?)
            """, (str(guild.id), tier, str(role.id)))
        conn.commit()
        conn.close()

        # ── Post panel embed ───────────────────────────────────────────────────
        embed = discord.Embed(
            title="🎮 BlockMango Tier Testing",
            description=(
                "Welcome to **Ranked Tests**!\n\n"
                "Click the button below to join the queue and get your tier tested.\n\n"
                "**Tiers Available:**\n"
                "> 🥇 `HT1` → `HT2` → `HT3` → `HT4` → `HT5` *(High Tier)*\n"
                "> 🔵 `LT1` → `LT2` → `LT3` → `LT4` → `LT5` *(Low Tier)*\n\n"
                "**Rules:**\n"
                "• Be honest about your skill level\n"
                "• Do not spam the queue\n"
                "• Respect your tester\n"
                "• Results are final unless appealed"
            ),
            color=discord.Color.gold()
        )
        embed.set_footer(text="Ranked Tests • BlockMango Tier Testing")

        view = QueueButton()
        await panel_channel.send(embed=embed, view=view)
        msgs.append(f"✅ Posted test panel in {panel_channel.mention}")

        # ── Done ───────────────────────────────────────────────────────────────
        summary = discord.Embed(
            title="✅ Setup Complete!",
            description="\n".join(msgs),
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=summary, ephemeral=True)


class QueueButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Join Queue", style=discord.ButtonStyle.green, custom_id="join_queue", emoji="📋")
    async def join_queue(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Hand off to queue cog modal
        await interaction.response.send_modal(QueueModal())


class QueueModal(discord.ui.Modal, title="Join Tier Test Queue"):
    ign = discord.ui.TextInput(
        label="Your BlockMango IGN",
        placeholder="e.g. BlockPlayer123",
        min_length=2,
        max_length=32
    )

    async def on_submit(self, interaction: discord.Interaction):
        from utils.db import get_config, get_db, COOLDOWN_DAYS
        import datetime

        guild = interaction.guild
        user = interaction.user
        config = get_config(guild.id)

        if not config:
            await interaction.response.send_message("❌ Bot is not set up yet. Ask the owner to run `/setup`.", ephemeral=True)
            return

        conn = get_db()

        # Check blacklist
        bl = conn.execute("SELECT * FROM blacklist WHERE guild_id = ? AND user_id = ?",
                          (str(guild.id), str(user.id))).fetchone()
        if bl:
            conn.close()
            await interaction.response.send_message(
                f"❌ You are blacklisted from tier testing.\n**Reason:** {bl['reason']}",
                ephemeral=True
            )
            return

        # Check 2-week cooldown
        last_result = conn.execute(
            "SELECT created_at FROM results WHERE guild_id = ? AND user_id = ? ORDER BY created_at DESC LIMIT 1",
            (str(guild.id), str(user.id))
        ).fetchone()
        if last_result:
            last_tested = datetime.datetime.fromisoformat(last_result["created_at"])
            cooldown_end = last_tested + datetime.timedelta(days=COOLDOWN_DAYS)
            now = datetime.datetime.utcnow()
            if now < cooldown_end:
                remaining = cooldown_end - now
                days = remaining.days
                hours = remaining.seconds // 3600
                conn.close()
                await interaction.response.send_message(
                    f"❌ You're on cooldown! You can requeue in **{days}d {hours}h**.",
                    ephemeral=True
                )
                return

        # Check if already in queue
        existing = conn.execute(
            "SELECT * FROM queue WHERE guild_id = ? AND user_id = ? AND status = 'waiting'",
            (str(guild.id), str(user.id))
        ).fetchone()
        if existing:
            conn.close()
            await interaction.response.send_message("❌ You are already in the queue!", ephemeral=True)
            return

        # Check if already has open ticket
        open_ticket = conn.execute(
            "SELECT * FROM tickets WHERE guild_id = ? AND user_id = ? AND status = 'open'",
            (str(guild.id), str(user.id))
        ).fetchone()
        if open_ticket:
            conn.close()
            await interaction.response.send_message("❌ You already have an open test ticket!", ephemeral=True)
            return

        # Add to queue
        conn.execute(
            "INSERT INTO queue (guild_id, user_id, ign, status) VALUES (?, ?, ?, 'waiting')",
            (str(guild.id), str(user.id), self.ign.value)
        )
        conn.commit()

        # Count position
        pos = conn.execute(
            "SELECT COUNT(*) as cnt FROM queue WHERE guild_id = ? AND status = 'waiting'",
            (str(guild.id),)
        ).fetchone()["cnt"]
        conn.close()

        # Give In Queue role
        in_queue_role = discord.utils.get(guild.roles, name="In Queue")
        if in_queue_role:
            await user.add_roles(in_queue_role)

        # Update queue channel
        await _refresh_queue_channel(guild, config)

        await interaction.response.send_message(
            f"✅ You've joined the queue!\n**IGN:** `{self.ign.value}`\n**Position:** #{pos}\n\nA tester will claim your test soon.",
            ephemeral=True
        )


async def _refresh_queue_channel(guild, config):
    """Refresh the queue embed in the queue channel."""
    from utils.db import get_db
    channel = guild.get_channel(int(config["queue_channel_id"]))
    if not channel:
        return

    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM queue WHERE guild_id = ? AND status = 'waiting' ORDER BY joined_at ASC",
        (str(guild.id),)
    ).fetchall()
    conn.close()

    embed = discord.Embed(
        title="📋 Tier Test Queue",
        color=discord.Color.blurple()
    )
    if not rows:
        embed.description = "*The queue is empty. Join from <#{}> !*".format(config["panel_channel_id"])
    else:
        lines = []
        for i, row in enumerate(rows, 1):
            member = guild.get_member(int(row["user_id"]))
            name = member.mention if member else f"<@{row['user_id']}>"
            lines.append(f"`#{i}` {name} — **{row['ign']}**")
        embed.description = "\n".join(lines)
    embed.set_footer(text=f"Ranked Tests • {len(rows)} player(s) waiting")

    # Delete old queue messages and repost
    try:
        await channel.purge(limit=10, check=lambda m: m.author.bot)
    except Exception:
        pass
    await channel.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Setup(bot))
    # Register persistent view
    bot.add_view(QueueButton())

