import os
import signal

import discord
from dotenv import load_dotenv
from discord.ext import commands

load_dotenv()
token = os.environ.get('token')

intents = discord.Intents.default()
client = discord.Client(intents=intents)
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='​', intents=intents)


def serialize_gem_list(gem_list):
    with open("gem_board.txt", "w") as f:
        for msg_id in gem_list:
            f.write(str(msg_id) + "\n")


def deserialize_gem_list():
    try:
        with open("gem_board.txt", "r") as f:
            return [int(line.strip()) for line in f.readlines()]
    except FileNotFoundError:
        return []


@bot.event
async def on_raw_reaction_add(event: discord.RawReactionActionEvent):
    msg = await (await bot.fetch_channel(event.channel_id)).fetch_message(event.message_id)

    # # count coal reacts
    # react_count = 0
    # count gem reacts
    gem_react_count = 0
    gem_list = deserialize_gem_list()
    for reaction in msg.reactions:
        if reaction.emoji == "💎":
            gem_react_count = reaction.count
            break

        # if "1374148035914764309" in str(reaction.emoji):
        #     react_count = reaction.count
        #     break

    # # prevent it from deleting from important channels
    # if react_count >= 5 and msg.channel.id not in [1167614611739136030, 1175632125534408844, 1331347644508930180, 1139816339213647923, 1093266096620044419, 1284274880480804958, 1347030545628135496]:
    #     print(str(msg.id) + " deleted | coals: " + str(react_count) + " | short id: " + str(msg.id)[0] + str(msg.id)[1])
    #     await msg.channel.send("https://tenor.com/view/cinema-zoolander-ben-stiller-coal-miner-gif-15796484", reference=msg)
    #     await msg.delete()

    if gem_react_count >= 2 and msg.channel.id and msg.id not in gem_list and msg.author.id != bot.user.id:
        print(str(msg.id) + " added to gem board | gems: " + str(gem_react_count) + " | short id: " + str(msg.id)[0] + str(msg.id)[1])

        gem_channel = bot.get_channel(1422572871019921569)
        current_channel = bot.get_channel(event.channel_id)
        embed = discord.Embed(colour=event.member.colour, timestamp=msg.created_at)

        embed.set_author(name=msg.author.display_name, icon_url=msg.author.avatar)

        if len(msg.content) > 0:
            embed.add_field(name="", value=msg.content)

        if len(msg.attachments) > 0:
            embed.set_image(url=msg.attachments[0].url)

        embed.add_field(name="", value=f"-# [jump to message]({msg.jump_url})", inline=False)

        gem_list.append(msg.id)
        serialize_gem_list(gem_list)

        await gem_channel.send(embed=embed)
        await current_channel.send(embed=embed, reference=msg)


@bot.event
async def on_ready():
    print("Syncing command tree")

    await bot.tree.sync()
    for command in bot.commands:
        print(command)
    for command in bot.tree.get_commands():
        print(command)

    print("Ready")


@bot.command()
async def kill(ctx: discord.ext.commands.Context):
    if ctx.author.id != 670821194550870016:
        await ctx.send(
            "Youre not frostwolf74, you cannot use this command.")
        return

    await ctx.send("Sending SIGTERM to self")
    os.kill(os.getpid(), signal.SIGTERM)


@bot.event
async def on_command_error(ctx, error): # FOR CTX
    if isinstance(error, commands.CommandNotFound): # if error instanceof CommandNotFound
        await ctx.send(error)


@bot.tree.error # FOR DISCORD.INTERACTION
async def throw_error(interaction: discord.Interaction, error):
    try:
        await interaction.followup.send(str(error)) # use preexisting webhook
    except:
        await interaction.channel.send(str(error)) # if webhook isnt reachable

    raise error


bot.run(token)