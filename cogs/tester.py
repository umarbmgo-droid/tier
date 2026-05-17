import discord
from discord.ext import commands
from discord import app_commands
from utils.db import get_db, get_config, TIERS, TIER_COLORS


class Tester(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="addtester", description="Add a tester role to a user (SA Tester or Admin)")
    @app_commands.describe(user="The user to promote", role="SA Tester or AS Tester")
    @app_commands.choices(role=[
        app_commands.Choice(name="SA Tester", value="sa"),
        app_commands.Choice(name="AS Tester", value="as"),
    ])
    async def add_tester(self, interaction: discord.Interaction, user: discord.Member, role: str):
        config = get_config(interaction.guild.id)
        if not config:
            await interaction.response.send_message("❌ Bot not set up yet.", ephemeral=True)
            return
        sa_role = interaction.guild.get_role(int(config["sa_tester_role_id"]))
        is_sa = sa_role and sa_role in interaction.user.roles
        is_admin = interaction.user.guild_permissions.administrator
        if not is_sa and not is_admin:
            await interaction.response.send_message("❌ Only SA Testers or Admins can manage tester roles.", ephemeral=True)
            return

        if role == "sa":
            target_role = interaction.guild.get_role(int(config["sa_tester_role_id"]))
        else:
            target_role = interaction.guild.get_role(int(config["as_tester_role_id"]))

        if not target_role:
            await interaction.response.send_message("❌ Role not found.", ephemeral=True)
            return

        await user.add_roles(target_role)
        embed = discord.Embed(
            title="✅ Tester Added",
            description=f"{user.mention} has been given **{target_role.name}**.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="removetester", description="Remove a tester role from a user (SA Tester or Admin)")
    @app_commands.describe(user="The user to demote", role="SA Tester or AS Tester")
    @app_commands.choices(role=[
        app_commands.Choice(name="SA Tester", value="sa"),
        app_commands.Choice(name="AS Tester", value="as"),
    ])
    async def remove_tester(self, interaction: discord.Interaction, user: discord.Member, role: str):
        config = get_config(interaction.guild.id)
        if not config:
            await interaction.response.send_message("❌ Bot not set up yet.", ephemeral=True)
            return
        sa_role = interaction.guild.get_role(int(config["sa_tester_role_id"]))
        is_sa = sa_role and sa_role in interaction.user.roles
        is_admin = interaction.user.guild_permissions.administrator
        if not is_sa and not is_admin:
            await interaction.response.send_message("❌ Only SA Testers or Admins can manage tester roles.", ephemeral=True)
            return

        if role == "sa":
            target_role = interaction.guild.get_role(int(config["sa_tester_role_id"]))
        else:
            target_role = interaction.guild.get_role(int(config["as_tester_role_id"]))

        if not target_role:
            await interaction.response.send_message("❌ Role not found.", ephemeral=True)
            return

        await user.remove_roles(target_role)
        embed = discord.Embed(
            title="✅ Tester Removed",
            description=f"{user.mention} has had **{target_role.name}** removed.",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="setresult", description="Set a player's tier manually (SA Tester only)")
    @app_commands.describe(user="The player", ign="Their IGN", tier="The tier to assign")
    @app_commands.choices(tier=[app_commands.Choice(name=t, value=t) for t in TIERS])
    async def set_result(self, interaction: discord.Interaction, user: discord.Member, ign: str, tier: str):
        config = get_config(interaction.guild.id)
        if not config:
            await interaction.response.send_message("❌ Bot not set up yet.", ephemeral=True)
            return
        sa_role = interaction.guild.get_role(int(config["sa_tester_role_id"]))
        if not sa_role or sa_role not in interaction.user.roles:
            await interaction.response.send_message("❌ Only SA Testers can manually set results.", ephemeral=True)
            return

        # Remove old tier roles
        for t in TIERS:
            r = discord.utils.get(interaction.guild.roles, name=t)
            if r and r in user.roles:
                await user.remove_roles(r)

        # Add new tier role
        conn = get_db()
        tier_role_row = conn.execute(
            "SELECT role_id FROM tier_roles WHERE guild_id = ? AND tier = ?",
            (str(interaction.guild.id), tier)
        ).fetchone()
        conn.execute(
            "INSERT INTO results (guild_id, user_id, ign, tier, tester_id, notes) VALUES (?, ?, ?, ?, ?, ?)",
            (str(interaction.guild.id), str(user.id), ign, tier, str(interaction.user.id), "Manually set by SA Tester")
        )
        conn.commit()
        conn.close()

        if tier_role_row:
            tier_role = interaction.guild.get_role(int(tier_role_row["role_id"]))
            if tier_role:
                await user.add_roles(tier_role)

        tested_role = interaction.guild.get_role(int(config["tested_role_id"]))
        if tested_role:
            await user.add_roles(tested_role)

        # Post in results
        results_channel = interaction.guild.get_channel(int(config["results_channel_id"]))
        embed = discord.Embed(
            title="🏆 Tier Manually Set",
            color=discord.Color(TIER_COLORS.get(tier, 0xFFFFFF))
        )
        embed.add_field(name="Player", value=user.mention, inline=True)
        embed.add_field(name="IGN", value=f"`{ign}`", inline=True)
        embed.add_field(name="Tier", value=f"**{tier}**", inline=True)
        embed.add_field(name="Set By", value=interaction.user.mention, inline=True)
        embed.set_footer(text="Ranked Tests • Manually Set")
        if results_channel:
            await results_channel.send(embed=embed)

        await interaction.response.send_message(
            f"✅ Set **{user.display_name}**'s tier to **{tier}**.", ephemeral=True
        )

    @app_commands.command(name="profile", description="View a player's tier profile")
    @app_commands.describe(user="The player to look up (leave empty for yourself)")
    async def profile(self, interaction: discord.Interaction, user: discord.Member = None):
        target = user or interaction.user
        conn = get_db()
        result = conn.execute(
            "SELECT * FROM results WHERE guild_id = ? AND user_id = ? ORDER BY created_at DESC LIMIT 1",
            (str(interaction.guild.id), str(target.id))
        ).fetchone()
        conn.close()

        embed = discord.Embed(
            title=f"📊 {target.display_name}'s Profile",
            color=discord.Color(TIER_COLORS.get(result["tier"], 0xFFFFFF)) if result else discord.Color.greyple()
        )
        if result:
            tester = interaction.guild.get_member(int(result["tester_id"]))
            embed.add_field(name="IGN", value=f"`{result['ign']}`", inline=True)
            embed.add_field(name="Current Tier", value=f"**{result['tier']}**", inline=True)
            embed.add_field(name="Tested By", value=tester.mention if tester else "Unknown", inline=True)
            if result["notes"]:
                embed.add_field(name="Notes", value=result["notes"], inline=False)
            embed.add_field(name="Date", value=result["created_at"][:10], inline=True)
        else:
            embed.description = f"*{target.display_name} has not been tested yet.*"
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.set_footer(text="Ranked Tests • BlockMango Tier Testing")
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Tester(bot))
