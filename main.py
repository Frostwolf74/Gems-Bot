import ast
import os
import re
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

# server.id: gem_channel
servers = {}
servers_coal = {}


def serialize_gem_list(gem_list, server_id):
    with open("gem_board-" + str(server_id) + ".txt", "w") as f:
        for msg_id in gem_list:
            f.write(str(msg_id) + "\n")


def deserialize_gem_list(server_id):
    try:
        with open("gem_board-" + str(server_id) + ".txt", "r") as f:
            return [int(line.strip()) for line in f.readlines()]
    except FileNotFoundError:
        return []


def serialize_pinned_list(pinned_list, server_id):
    with open("pinned_list-" + str(server_id) + ".txt", "w") as f:
        for msg_id in pinned_list:
            f.write(str(msg_id) + "\n")


def deserialize_pinned_list(server_id):
    try:
        with open("pinned_list-" + str(server_id) + ".txt", "r") as f:
            return [int(line.strip()) for line in f.readlines()]
    except FileNotFoundError:
        return []

@bot.command()
async def gemskill(ctx: discord.ext.commands.Context):
    if ctx.author.id != 670821194550870016:
        await ctx.send(
            "Youre not frostwolf74, you cannot use this command.")
        return

    await ctx.send("Killing myself")
    os.kill(os.getpid(), signal.SIGTERM)


@bot.tree.command(
    name="set-channel",
    description="set the channel gem reacted posts will be posted in"
)
async def set_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    global servers

    servers.update({channel.guild.id: channel.id})

    with open("servers.txt", "w") as f:
        f.write(str(servers))

    await interaction.response.send_message("Gem channel set")


@bot.tree.command(
    name="set-coal",
    description="set the coal emoji id"
)
async def set_coal(interaction: discord.Interaction, emoji_id: int):
    global servers_coal


@bot.event
async def on_raw_reaction_add(event: discord.RawReactionActionEvent):
    msg = await (await bot.fetch_channel(event.channel_id)).fetch_message(event.message_id)
    global servers
    gem_channel_id = servers.get(msg.guild.id)
    attachment_cloud_id = 1429688927601823804 # for ensuring images are saved correctly without local storage
    gem_limit = 2
    coal_limit = 5
    pin_react_limit = 5
    excluded_channels = []
    coal_emoji_id = "1420615710681469102"

    # count coal reacts
    react_count = 0
    # count gem reacts
    gem_react_count = 0
    files = []
    gem_list = deserialize_gem_list(event.guild_id)
    pinned_list = deserialize_pinned_list(event.guild_id)
    for reaction in msg.reactions:
        if reaction.emoji == "💎":
            gem_react_count = reaction.count
            break

        if coal_emoji_id in str(reaction.emoji):
            react_count = reaction.count
            break

    # prevent it from deleting from important channels
    if react_count >= coal_limit and msg.channel.id not in excluded_channels:
        print(str(msg.id) + " deleted | coals: " + str(react_count) + " | short id: " + str(msg.id)[0] + str(msg.id)[1])
        await msg.channel.send("HWABAG or some sh", reference=msg)
        await msg.delete()

    if gem_react_count >= gem_limit and msg.channel.id not in excluded_channels and msg.id not in gem_list and msg.author.id != bot.user.id:
        print(str(msg.id) + " added to gem board | gems: " + str(gem_react_count) + " | short id: " + str(msg.id)[0] + str(msg.id)[1] + str(msg.id)[len(str(msg.id)) - 2] + str(msg.id)[len(str(msg.id)) - 1])

        gem_channel = bot.get_channel(gem_channel_id)
        current_channel = bot.get_channel(event.channel_id)
        attachment_cloud = bot.get_channel(attachment_cloud_id)
        embed = discord.Embed(colour=msg.author.color, timestamp=msg.created_at)

        embed.set_author(name=msg.author.display_name, icon_url=msg.author.avatar)

        gif_patterns = [
            r'https?://(?:www\.)?tenor\.com/view/[\w-]+',
            r'https?://(?:www\.)?gfycat\.com/[\w-]+',
            r'https?://media\d?\.giphy\.com/media/[\w-]+/giphy\.gif',
            r'.*\.gif(?:$|\?.*)'
        ]

        is_gif = False

        for pattern in gif_patterns:
            if re.search(pattern, msg.content):
                is_gif = True
                break

        if len(msg.content) > 0 and not is_gif: # message text
            embed.add_field(name="", value=msg.content)

        if len(msg.attachments) > 0:
            if msg.attachments[0].content_type == "video/mp4" or msg.attachments[0].content_type == "video/quicktime": # webm
                files = []
                for attachment in msg.attachments:
                    file = await attachment.to_file()
                    file.spoiler = attachment.is_spoiler()
                    files.append(file)

                files1 = []
                for attachment in msg.attachments:
                    file = await attachment.to_file()
                    file.spoiler = attachment.is_spoiler()
                    files1.append(file)

                try:
                    # await current_channel.send(files=files, embed=embed, reference=msg)
                    embed.add_field(name="", value=f"-# [jump to message]({msg.jump_url})", inline=False)
                    await gem_channel.send(files=files1, embed=embed)
                except discord.errors.HTTPException: # file too big
                    attachments = ""
                    for attachment in msg.attachments:
                        attachments += attachment.url + "\n"

                    # await current_channel.send(embed=embed, reference=msg)
                    # await current_channel.send(attachments)
                    embed.add_field(name="", value=f"-# [jump to message]({msg.jump_url})", inline=False)
                    await gem_channel.send(embed=embed)
                    await gem_channel.send(attachments)
            else:
                message = await attachment_cloud.send(file=await msg.attachments[0].to_file())
                embed.set_image(url=message.attachments[0].url)
                # await current_channel.send(embed=embed, reference=msg)
                embed.add_field(name="", value=f"-# [jump to message]({msg.jump_url})", inline=False)
                await gem_channel.send(embed=embed)
        elif is_gif:
            # await current_channel.send(content=msg.content, reference=msg)
            embed.add_field(name="", value=f"-# [jump to message]({msg.jump_url})", inline=False)
            await gem_channel.send(embed=embed)
            await gem_channel.send(content=msg.content)
        else:
            # await current_channel.send(embed=embed, reference=msg)
            embed.add_field(name="", value=f"-# [jump to message]({msg.jump_url})", inline=False)
            await gem_channel.send(embed=embed)

        gem_list.append(msg.id)
        serialize_gem_list(gem_list, event.guild_id)

    if gem_react_count >= pin_react_limit and msg.channel.id not in excluded_channels and msg.id not in pinned_list and msg.author.id != bot.user.id:
        pinned_list.append(msg.id)
        serialize_pinned_list(pinned_list, event.guild_id)
        print(str(msg.id) + " pinned | gems: " + str(gem_react_count) + " | short id: " + str(msg.id)[0] + str(msg.id)[1])

        try:
            await msg.pin()
        except Exception as e:
            print(e)


@bot.event
async def on_ready():
    print("Syncing command tree")

    await bot.tree.sync()
    for command in bot.commands:
        print(command.name)
    for command in bot.tree.get_commands():
        print(command.name)

    print("Syncing servers")
    global servers

    if "servers.txt" not in os.listdir(os.getcwd()):
        open("servers.txt", "w").close()

    # read existing server configuration into servers dictionary
    # server.id: gem_channel <- servers.txt
    with open("servers.txt", "r+") as servers_file:
        read = servers_file.read()
        if read != "":
            servers = ast.literal_eval(read) # interpret as dictionary when reading

    for server in servers:
        print(str(server) + ": " + str(servers.get(server)))  # to verify the dictionary is populated with the correct servers

    print("Ready")


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
