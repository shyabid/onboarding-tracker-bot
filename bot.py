#!/usr/bin/env python3

from discord.ext import commands
import discord
import config
import traceback

class Bot(commands.Bot):
    def __init__(self, intents: discord.Intents, **kwargs):
        super().__init__(command_prefix=commands.when_mentioned_or('$'), intents=intents, **kwargs)

    async def setup_hook(self):
        for cog in config.cogs:
            try:
                await self.load_extension(cog)
            except Exception as exc:
                print(f'Could not load extension {cog} due to {exc.__class__.__name__}: {exc}')
        
    async def on_ready(self):
        await self.tree.sync()
        
        print(f'Logged on as {self.user} (ID: {self.user.id})')


    
    
    async def on_command_error(
        self, 
        context: commands.Context, 
        error: commands.CommandError
    ) -> None: 
        log_channel = self.get_channel(1414793522447519795)
        if log_channel is None:
            traceback.print_exception(type(error), error, error.__traceback__)
            return

        embed = discord.Embed(
            title="Bot Error",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )

        embed.add_field(name="Error Details", value=str(error)[:1024], inline=False)

        tb_string = ''.join(traceback.format_tb(error.__traceback__))

        if context.command:
            embed.add_field(name="Command", value=context.command.qualified_name, inline=True)

        if context:
            embed.add_field(name="User", value=f"{context.author.mention}", inline=True)
            embed.add_field(name="Channel", value=f"{context.channel.mention}", inline=True)
            embed.add_field(name="Guild", value=f"{context.guild.name}\n{context.guild.id}" if context.guild else "DM", inline=True)

        await log_channel.send(embed=embed, content=f"```py\n{tb_string[:1800]}\n```")
        
intents = discord.Intents.all()
bot = Bot(intents=intents)

bot.run(config.token)
