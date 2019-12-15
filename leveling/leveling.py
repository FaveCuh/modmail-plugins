"""
Leveling plugin for Modmail.

Written by Papiersnipper.
All rights reserved.
"""

from discord import Embed, Message, User
from discord.ext.commands import Bot, Cog, Context, group
from motor.motor_asyncio import AsyncIOMotorCollection

from core.checks import has_permissions
from core.models import PermissionLevel


class Leveling(Cog):
    """A leveling system for your server: see who's active and who's not.
    More info: [click here](https://github.com/papiersnipper/modmail-plugins/tree/master/leveling)
    """

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.db: AsyncIOMotorCollection = bot.plugin_db.get_partition(self)

    @Cog.listener()
    async def on_message(self, message: Message) -> None:
        if message.author.bot:
            return

        try:
            amount = (await self.db.find_one({"_id": "leveling-config"}))["amount_per_message"]
        except (KeyError, TypeError):
            return

        person = await self.db.find_one({"id": message.author.id})

        if person is None:
            await self.db.insert_one(
                {
                    "id": message.author.id,
                    "name": message.author.name,
                    "gold": amount,
                    "exp": amount,
                    "level": 1,
                }
            )
        else:
            new_gold = person["gold"] + amount
            new_exp = person["exp"] + amount
            level = int(new_exp ** (1 / 4))

            if person["level"] < level:
                await message.channel.send(
                    _("Congratulations, {usser}, you are now level {level}!").format(
                        user=message.author.mention, level=level
                    )
                )

                await self.db.update_one(
                    {"id": message.author.id},
                    {
                        "$set": {
                            "gold": new_gold,
                            "exp": new_exp,
                            "level": level,
                            "name": message.author.name,
                        }
                    },
                )
            else:
                await self.db.update_one(
                    {"id": message.author.id},
                    {"$set": {"gold": new_gold, "exp": new_exp, "name": message.author.name,}},
                )

    @group(name="level", invoke_without_command=True)
    @has_permissions(PermissionLevel.REGULAR)
    async def level(self, ctx: Context) -> None:
        """A leveling system for your server: see who's active and who's not."""

        await ctx.send_help(ctx.command)

    @level.command(name="info")
    @has_permissions(PermissionLevel.REGULAR)
    async def info(self, ctx: Context, user: User = None) -> None:
        """Check someone's current amount of gold, exp and level."""

        user: User = user if user is not None else ctx.author

        stats = await self.db.find_one({"id": user.id})

        if stats is None:
            embed = Embed(
                title="Leveling",
                url="https://github.com/papiersnipper/modmail-plugins/blob/master/leveling",
                description=_("User {name} hasn't sent a single message here.").format(
                    name=user.name
                ),
                color=self.bot.main_color,
            )

            return await ctx.send(embed=embed)

        embed = Embed(
            title="Leveling",
            url="https://github.com/papiersnipper/modmail-plugins/blob/master/leveling",
            description=_("{name} is level {level}, has {exp} exp and {gold} gold.").format(
                name=user.name, level=stats["level"], exp=stats["exp"], gold=stats["gold"]
            ),
            color=self.bot.main_color,
        )

        await ctx.send(embed=embed)

    @level.command(name="amount")
    @has_permissions(PermissionLevel.ADMINISTRATOR)
    async def amount(self, ctx: Context, amount: str = "") -> None:
        """Change the amount of gold given to a user per message."""

        if amount == "":
            try:
                amount = (await self.db.find_one({"_id": "leveling-config"}))["amount_per_message"]
            except (KeyError, TypeError):
                return await ctx.send_help(ctx.command)

            embed = Embed(
                title="Leveling",
                url="https://github.com/papiersnipper/modmail-plugins/blob/master/leveling",
                description=_("The amount of gold given per message is {amount}.").format(
                    amount=amount
                ),
                color=self.bot.main_color,
            )

            return await ctx.send(embed=embed)

        try:
            amount = int(amount)
        except ValueError:
            embed = Embed(
                title="Leveling",
                url="https://github.com/papiersnipper/modmail-plugins/blob/master/leveling",
                description=_("That doesn't look like a valid number."),
                color=self.bot.main_color,
            )

            return await ctx.send(embed=embed)

        if amount < 1:
            embed = Embed(
                title="Leveling",
                url="https://github.com/papiersnipper/modmail-plugins/blob/master/leveling",
                description=_("I can't give negative gold."),
                color=self.bot.main_color,
            )

            return await ctx.send(embed=embed)

        config = await self.db.find_one({"_id": "leveling-config"})

        if config is None:
            await self.db.insert_one({"_id": "leveling-config", "amount_per_message": amount})
            embed = Embed(
                title="Leveling",
                url="https://github.com/papiersnipper/modmail-plugins/blob/master/leveling",
                description=_("I set the amount of gold given to {amount}.").format(amount=amount),
                color=self.bot.main_color,
            )
        else:
            await self.db.update_one(
                {"_id": "leveling-config"}, {"$set": {"amount_per_message": amount}}
            )
            embed = Embed(
                title="Leveling",
                url="https://github.com/papiersnipper/modmail-plugins/blob/master/leveling",
                description=_("I updated the amount of gold given to {amount}.").format(
                    amount=amount
                ),
                color=self.bot.main_color,
            )

        await ctx.send(embed=embed)

    @level.command(name="leaderboard", aliases=["lb"])
    @has_permissions(PermissionLevel.REGULAR)
    async def leaderboard(self, ctx: Context) -> None:
        """Check who has the most experience points."""

        users = self.db.find({}).sort("exp", -1)

        embed = Embed(
            title=_("Leaderboard for {guild}").format(guild=ctx.guild.name),
            url="https://github.com/papiersnipper/modmail-plugins/blob/master/leveling",
            colour=self.bot.main_color,
        )

        for user in await users.to_list(length=11):
            try:
                embed.add_field(name=user["name"], value=str(user["exp"]) + " exp")
            except KeyError:
                continue

        await ctx.send(embed=embed)

    @level.command(name="give")
    @has_permissions(PermissionLevel.ADMINISTRATOR)
    async def give(self, ctx: Context, user: User, amount: str) -> None:
        """Give a specific amount of gold to a user."""

        try:
            amount = int(amount)
        except ValueError:
            embed = Embed(
                title="Leveling",
                url="https://github.com/papiersnipper/modmail-plugins/blob/master/leveling",
                description=_("That doesn't look like a valid number."),
                color=self.bot.main_color,
            )

            return await ctx.send(embed=embed)

        if amount < 1:
            embed = Embed(
                title="Leveling",
                url="https://github.com/papiersnipper/modmail-plugins/blob/master/leveling",
                description=_("I can't give negative gold."),
                color=self.bot.main_color,
            )

            return await ctx.send(embed=embed)

        stats = await self.db.find_one({"id": user.id})

        if stats is None:
            embed = Embed(
                title="Leveling",
                url="https://github.com/papiersnipper/modmail-plugins/blob/master/leveling",
                description=_("User {name} hasn't sent a single message here.").format(
                    name=user.name
                ),
                color=self.bot.main_color,
            )

            return await ctx.send(embed=embed)

        gold = int(stats["gold"])

        await self.db.update_one({"id": user.id}, {"$set": {"gold": gold + amount}})

        embed = Embed(
            title="Leveling",
            url="https://github.com/papiersnipper/modmail-plugins/blob/master/leveling",
            description=_("I gave {amount} gold to {name}.").format(amount=amount, name=user.name),
            color=self.bot.main_color,
        )

        await ctx.send(embed=embed)


def setup(bot: Bot) -> None:
    """Bot cog load."""
    bot.add_cog(Leveling(bot))
