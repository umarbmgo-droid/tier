import discord
from discord.ext import commands
from discord import app_commands
from utils.db import get_db, get_config, TIERS, TIER_COLORS


class Appeal(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="appeal", description="Appeal your tier result")
    async def appeal(self, interaction: discord.Interaction):
        config = get_config(interaction.guild.id)
        if not config:
            await interaction.response.send_message("❌ Bot not set up yet.", ephemeral=True)
            return

        conn = get_db()
        # Check if already has open appeal
        existing = conn.execute(
            "SELECT * FROM appeals WHERE guild_id = ? AND user_id = ? AND status = 'open'",
            (str(interaction.guild.id), str(interaction.user.id))
        ).fetchone()
        if existing:
            conn.close()
            await interaction.response.send_message("❌ You already have an open appeal!", ephemeral=True)
            return

        # Check if they have a result
        result = conn.execute(
            "SELECT * FROM results WHERE guild_id = ? AND user_id = ? ORDER BY created_at DESC LIMIT 1",
            (str(interaction.guild.id), str(interaction.user.id))
        ).fetchone()
        conn.close()

        if not result:
            await interaction.response.send_message("❌ You don't have a tier result to appeal.", ephemeral=True)
            return

        await interaction.response.send_modal(AppealModal(result["tier"], result["ign"]))


class AppealModal(discord.ui.Modal, title="Tier Appeal"):
    reason = discord.ui.TextInput(
        label="Why do you want to appeal?",
        placeholder="Explain why you think your tier is wrong...",
        style=discord.TextStyle.paragraph,
        min_length=20,
        max_length=1000
    )

    def __init__(self, current_tier, ign):
        super().__init__()
        self.current_tier = current_tier
        self.ign = ign

    async def on_submit(self, interaction: discord.Interaction):
        config = get_config(interaction.guild.id)
        guild = interaction.guild

        sa_role = guild.get_role(int(config["sa_tester_role_id"]))
        as_role = guild.get_role(int(config["as_tester_role_id"]))
        category = guild.get_channel(int(config["ticket_category_id"]))

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            sa_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
            as_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
        }

        appeal_channel = await guild.create_text_channel(
            name=f"appeal-{self.ign.lower()}",
            category=category,
            overwrites=overwrites,
            reason=f"Tier appeal for {self.ign}"
        )

        conn = get_db()
        conn.execute(
            "INSERT INTO appeals (guild_id, user_id, ign, current_tier, reason, channel_id, status) VALUES (?, ?, ?, ?, ?, ?, 'open')",
            (str(guild.id), str(interaction.user.id), self.ign, self.current_tier, self.reason.value, str(appeal_channel.id))
        )
        conn.commit()
        conn.close()

        embed = discord.Embed(
            title="📢 Tier Appeal",
            color=discord.Color(TIER_COLORS.get(self.current_tier, 0xFFFFFF))
        )
        embed.add_field(name="Player", value=interaction.user.mention, inline=True)
        embed.add_field(name="IGN", value=f"`{self.ign}`", inline=True)
        embed.add_field(name="Current Tier", value=f"**{self.current_tier}**", inline=True)
        embed.add_field(name="Reason", value=self.reason.value, inline=False)
        embed.set_footer(text="Ranked Tests • SA Tester will review this appeal")

        view = AppealControls()
        await appeal_channel.send(
            content=f"{interaction.user.mention} {sa_role.mention}",
            embed=embed,
            view=view
        )

        await interaction.response.send_message(
            f"✅ Appeal submitted! Check {appeal_channel.mention}", ephemeral=True
        )


class AppealControls(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Accept Appeal", style=discord.ButtonStyle.green, custom_id="accept_appeal", emoji="✅")
    async def accept_appeal(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = get_config(interaction.guild.id)
        sa_role = interaction.guild.get_role(int(config["sa_tester_role_id"]))
        if not sa_role or sa_role not in interaction.user.roles:
            await interaction.response.send_message("❌ Only SA Testers can handle appeals.", ephemeral=True)
            return
        await interaction.response.send_modal(AppealResultModal(accepted=True))

    @discord.ui.button(label="Deny Appeal", style=discord.ButtonStyle.red, custom_id="deny_appeal", emoji="❌")
    async def deny_appeal(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = get_config(interaction.guild.id)
        sa_role = interaction.guild.get_role(int(config["sa_tester_role_id"]))
        if not sa_role or sa_role not in interaction.user.roles:
            await interaction.response.send_message("❌ Only SA Testers can handle appeals.", ephemeral=True)
            return
        await interaction.response.send_modal(AppealResultModal(accepted=False))


class AppealResultModal(discord.ui.Modal):
    response = discord.ui.TextInput(
        label="Response / Reason",
        placeholder="Explain your decision...",
        style=discord.TextStyle.paragraph,
        max_length=500
    )

    def __init__(self, accepted: bool):
        super().__init__(title="Accept Appeal" if accepted else "Deny Appeal")
        self.accepted = accepted

    async def on_submit(self, interaction: discord.Interaction):
        config = get_config(interaction.guild.id)
        conn = get_db()
        appeal = conn.execute(
            "SELECT * FROM appeals WHERE guild_id = ? AND channel_id = ? AND status = 'open'",
            (str(interaction.guild.id), str(interaction.channel.id))
        ).fetchone()
        if not appeal:
            conn.close()
            await interaction.response.send_message("❌ No open appeal found.", ephemeral=True)
            return

        conn.execute("UPDATE appeals SET status = ? WHERE id = ?",
                     ("accepted" if self.accepted else "denied", appeal["id"]))
        conn.commit()
        conn.close()

        member = interaction.guild.get_member(int(appeal["user_id"]))
        color = discord.Color.green() if self.accepted else discord.Color.red()
        status_text = "✅ Appeal Accepted" if self.accepted else "❌ Appeal Denied"

        embed = discord.Embed(title=status_text, color=color)
        embed.add_field(name="Player", value=member.mention if member else appeal["user_id"], inline=True)
        embed.add_field(name="IGN", value=f"`{appeal['ign']}`", inline=True)
        embed.add_field(name="Reviewed By", value=interaction.user.mention, inline=True)
        embed.add_field(name="Response", value=self.response.value, inline=False)
        embed.set_footer(text="Ranked Tests • Closing in 15 seconds")

        await interaction.response.send_message(embed=embed)

        # Post in results channel
        results_channel = interaction.guild.get_channel(int(config["results_channel_id"]))
        if results_channel:
            await results_channel.send(embed=embed)

        import asyncio
        await asyncio.sleep(15)
        try:
            await interaction.channel.delete()
        except Exception:
            pass


async def setup(bot):
    await bot.add_cog(Appeal(bot))
    bot.add_view(AppealControls())
