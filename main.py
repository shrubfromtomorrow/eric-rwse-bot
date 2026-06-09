import os
from dotenv import load_dotenv
import discord
from discord.ext import commands
from services.ModmailService import ModmailService
from cogs.Social import Social
from cogs.Chalvering import Chalvering
from cogs.Sheet import Sheet
from cogs.Moderation import Moderation
from cogs.Modmail import Modmail
from cogs.PinArchiving import PinArchiving
from cogs.Slowmode import AdaptiveSlowmode
from cogs.FirstPlaythrough import FirstPlaythrough
from cogs.EmbedBuilder import EmbedBuilder
import utils.checks as checks
import utils.exceptions as exceptions
from config.ConfigManager import ConfigManager
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from cogs.ImageManager import ImageManager
from cogs.PagedLogs import LogsCog
from cogs.Autoresponder import Autoresponder
from cogs.Autopinner import Autopinner
import traceback
import types
import time
import asyncio
import faulthandler
import signal
import traceback
from cogs.Ogspores import Ogspores

intents = discord.Intents()
intents.message_content = True
intents.messages = True
intents.dm_typing = True
intents.dm_messages = True
intents.guilds = True
intents.members = True
intents.voice_states = True
intents.presences = True
intents.moderation = True

load_dotenv()

# Create a new client and connect to the server
mongo = MongoClient(os.environ['CONNECTION_URI'])

# Send a ping to confirm a successful connection
try:
  start_time = time.perf_counter()
  mongo.admin.command('ping')
  latency_ms = (time.perf_counter() - start_time) * 1000

  print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
  print(e)

bot = commands.Bot(command_prefix='.', intents=intents)
bot.remove_command('help')

modmail_service: ModmailService = ModmailService(bot, mongo)

bot.add_cog(Social(bot, mongo))
bot.add_cog(Chalvering(bot))
bot.add_cog(Sheet(bot))
bot.add_cog(FirstPlaythrough(bot))
bot.add_cog(Moderation(bot, mongo, modmail_service))
bot.add_cog(Modmail(bot, mongo, modmail_service))
bot.add_cog(ImageManager(bot, mongo))
bot.add_cog(AdaptiveSlowmode(bot, mongo))
bot.add_cog(LogsCog(bot, mongo))
bot.add_cog(Autoresponder(bot, mongo))
bot.add_cog(PinArchiving(bot, mongo))
bot.add_cog(EmbedBuilder(bot))
bot.add_cog(Autopinner(bot, mongo))


faulthandler.enable()

def dump_tasks(sig, frame):
  print("\n===== TASK DUMP =====")
  for task in asyncio.all_tasks():
    print(task)
    task.print_stack()
  print("===== END TASK DUMP =====\n")

signal.signal(signal.SIGUSR1, dump_tasks)

################### SHENANIGANS #######################
@bot.command()
@checks.allowed_for_role_group('staff', cm=ConfigManager())
@commands.guild_only()
async def Ogspores(ctx: commands.Context):
  try:
    bot.add_cog(Ogspores(bot, mongo))
    await ctx.send('Run for your lives! There\'s some sort of disease spreading throug the air called the "ogspores"!')
  except discord.errors.ClientException:
    await ctx.send('Ogspores have already breached containment.')

@bot.command()
@checks.allowed_for_role_group('staff', cm=ConfigManager())
@commands.guild_only()
async def deactivate_ogspores(ctx: commands.Context):
  try:
    bot.remove_cog(Ogspores(bot, mongo))
    await ctx.send('Cure for ogspores has been put into the water supplies.')
  except discord.errors.ClientException:
    await ctx.send('Cure for ogspores has already been unleashed.')
################### SHENANIGANS #######################


@bot.command()
@checks.allowed_for_role_group('staff', cm=ConfigManager())
@commands.guild_only()
async def activate_adaptive_slowmode(ctx: commands.Context):
  try:
    bot.add_cog(AdaptiveSlowmode(bot, mongo))
    await ctx.send('Activated adaptive slowmode!')
  except discord.errors.ClientException:
    await ctx.send('Adaptive slowmode is already active.')

@bot.command()
@checks.allowed_for_role_group('staff', cm=ConfigManager())
@commands.guild_only()
async def deactivate_adaptive_slowmode(ctx: commands.Context):
  try:
    bot.remove_cog(AdaptiveSlowmode(bot, mongo))
    await ctx.send('Deactivated adaptive slowmode!')
  except discord.errors.ClientException:
    await ctx.send('Adaptive slowmode is already inactive.')

@bot.event
async def on_error(event_name, *args, **kwargs):
  err = traceback.format_exc()
  try:
    float(err)
    await print_error(f"float coming from on_error, {err}")
  except ValueError:
    await print_error(err)

@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
  if isinstance(error, (exceptions.RoleNotFound, exceptions.NotAHandler, exceptions.MemberNotFound, commands.MemberNotFound, exceptions.EditColorInvalidColor, commands.CommandNotFound)):
    return
  await print_error(f"original message: {ctx.message.content}\n error: {error}")

@bot.event
async def on_application_command_error(ctx: commands.Context, error: commands.CommandError):
  if isinstance(error, (exceptions.RoleNotFound, exceptions.InvalidSpeerdunValidation, commands.CommandOnCooldown, exceptions.CommandOnCooldown, exceptions.NoChallengeCompletions, exceptions.MemberNotFound, commands.MemberNotFound)):
    return
  await print_error(f"application command error: {error}")

async def print_error(error_string: str):
  logbook = mongo.sprinkles.config.find_one({'setting': 'logbook'})
  logbook_id = logbook['value']['channel_id']
  logbook_channel = await bot.fetch_channel(logbook_id)
  
  if len(error_string) <= 3900:
    embed = discord.Embed(title="Error Log", description=f'```{error_string}```', color=4491263)
    await logbook_channel.send(embed=embed)
    return
  
  parts = []
  current_part = ""
  
  for line in error_string.split('\n'):
    if len(current_part) + len(line) + 1 > 3900:
      parts.append(current_part)
      current_part = line
    else:
      current_part += '\n' + line if current_part else line
  
  if current_part:
    parts.append(current_part)
  
  for i, part in enumerate(parts):
    embed = discord.Embed(title=f"Error Log (Part `{i + 1}`/`{len(parts)}`)", description=f'```{part}```', color=4491263)
    await logbook_channel.send(embed=embed)

# For emergencies only 
@bot.command()
@checks.allowed_for_role_group('admins', cm=ConfigManager())  
async def crash(ctx: commands.Context, ident: str):
  with open('identifier.txt') as my_ident:
    me = my_ident.readlines()[0].strip()
    if me == ident:
      await ctx.send("\\*leaps into a bottomless pit\\*\nweeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee")
      await bot.close()
    else:
      await ctx.send(f'Ignroing order to leap into a bottomless pit. My identifier is: `{me}`')


@bot.event
async def on_ready():
  print('\n\n************************ READY ************************\n\n')
  startup_settings = mongo.sprinkles.config.find_one({'setting': 'ready-settings'})
  ready_id = startup_settings['value']['ready_channel_id']
  status = startup_settings['value']['default_status']

  await bot.change_presence(activity=discord.CustomActivity(name=status))
  settings_channel = await bot.fetch_channel(ready_id)
  
  with open('identifier.txt', encoding='UTF-8') as ident:
    embed = discord.Embed(title='\\*whoosh!\\*', color=4776171, description=f"""
The cycle has just begun and I have just restarted! My prefix is `{bot.command_prefix}`
Status set to: `{status}`. 
-# (You can change this with `.set_status [status]`)

My latency: `{round(bot.latency * 1000)}` ms
MongoDB latency: `{round(latency_ms)}` ms""")
    embed.set_footer(text=f'Identifier: {ident.readlines()[0]}')
    await settings_channel.send(embed=embed)
  

bot.run(os.environ['DISCORD_TOKEN'])
