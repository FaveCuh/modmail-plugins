import random
import discord

class pp(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['pp'])
    async def penis(ctx, member: discord.Member=None):
        pps = [
            '8==D',
            '8===D',
            '8====D',
            '8=====D',
            '8======D',
            '8=======D',
            '8========D',
            '8=========D'
        ]
        if not member:
            member = ctx.author
            maincolor = 0xFF4136
        ppSize = random.choice(pps)
        embed = discord.Embed(description=f"{ppSize}", color=maincolor)
        embed.set_author(name=f"{member.display_name}'s Penis:")
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(pp(bot))
