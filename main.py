import ast
import os
import re
import signal
import requests
import discord
import asyncio
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
excluded_channels_global = {}

gem_board_lock = asyncio.Lock()


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


def fetch_check(url: str) -> bool:
    try:
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "")
        return content_type.startswith("image/")
    except requests.RequestException:
        return False


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
    if not (await interaction.guild.fetch_member(interaction.user.id)).guild_permissions.administrator:
        await interaction.response.send_message("You dont have permission to use this command.")
        return

    global servers

    servers.update({channel.guild.id: channel.id})

    with open("servers.txt", "w") as f:
        f.write(str(servers))

    await interaction.response.send_message("Gem channel set")


@bot.tree.command(
    name="set-coal",
    description="set the coal emoji id"
)
async def set_coal(interaction: discord.Interaction, emoji_id: str):
    if not (await interaction.guild.fetch_member(interaction.user.id)).guild_permissions.administrator:
        await interaction.response.send_message("You dont have permission to use this command.")
        return

    global servers_coal

    servers_coal.update({interaction.guild.id: emoji_id})

    with open("coals.txt", "w") as f:
        f.write(str(servers_coal))

    await interaction.response.send_message("Coal emoji set")


@bot.tree.command(
    name="set-excluded-channels",
    description="Set channels for the bot to ignore"
)
async def set_excluded_channels(interaction: discord.Interaction, channel: discord.TextChannel):
    if not (await interaction.guild.fetch_member(interaction.user.id)).guild_permissions.administrator:
        await interaction.response.send_message("You dont have permission to use this command.")
        return

    excluded_channels_from_file: dict[int, list[int]] = {}
    if "excluded_channels.txt" in os.listdir(os.getcwd()): # append if it exists
        with open("excluded_channels.txt", "r+") as f:
            read = f.read()
            if read != "":
                excluded_channels_from_file: dict[int, list[int]] = ast.literal_eval(read)

        print(excluded_channels_from_file)
        try:
            excluded_channels_from_file[interaction.guild.id].append(channel.id)
        except ValueError: # if the file exists but the guild id is not in it
            excluded_channels_from_file.update({interaction.guild.id: [channel.id]})

    global excluded_channels_global
    excluded_channels_global = excluded_channels_from_file

    with open("excluded_channels.txt", "w") as f:
        f.write(str(excluded_channels_global))

    await interaction.response.send_message("Channel added to excluded channels list.", ephemeral=True)


@bot.event
async def on_raw_reaction_add(event: discord.RawReactionActionEvent):
    msg = await (await bot.fetch_channel(event.channel_id)).fetch_message(event.message_id)
    global servers
    gem_channel_id = servers.get(msg.guild.id) # fetch the channel value int from the associated server key int
    attachment_cloud_id = 1429688927601823804 # for ensuring images are saved correctly without local storage
    gem_limit = 2
    coal_limit = 5
    pin_react_limit = 5
    global excluded_channels_global
    excluded_channels = excluded_channels_global.get(event.guild_id)
    global servers_coal
    coal_emoji_id = servers_coal.get(event.guild_id)

    # count coal reacts
    react_count = 0
    # count gem reacts
    gem_react_count = 0
    files = []
    pinned_list = deserialize_pinned_list(event.guild_id)
    for reaction in msg.reactions:
        if reaction.emoji == "💎":
            gem_react_count = reaction.count

            # users cannot count their own reaction
            if msg.author == event.member:
                gem_react_count -= 1
            break

        if coal_emoji_id is not None and coal_emoji_id in str(reaction.emoji):
            react_count = reaction.count

            # users cannot count their own reaction
            if msg.author == event.member:
                react_count -= 1
            break

    # prevent it from deleting from important channels
    if react_count >= coal_limit and msg.channel.id not in excluded_channels:
        print(str(msg.id) + " deleted | coals: " + str(react_count) + " | short id: " + str(msg.id)[0] + str(msg.id)[1])
        await msg.channel.send("HWABAG or some sh", reference=msg)
        await msg.delete()

    if gem_react_count >= gem_limit and msg.channel.id not in excluded_channels and msg.id and msg.author.id != bot.user.id:
        global gem_board_lock # prevents parallel instances in the event that a post is reacted to by two different users at the same time
        async with gem_board_lock:
            gem_list = deserialize_gem_list(event.guild_id)
            if msg.id not in gem_list:
                print(str(msg.id) + " added to gem board | gems: " + str(gem_react_count) + " | short id: " + str(msg.id)[0] + str(msg.id)[1] + str(msg.id)[len(str(msg.id)) - 2] + str(msg.id)[len(str(msg.id)) - 1])

                gem_channel = await bot.fetch_channel(gem_channel_id) # will never not be an int
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
                is_image = fetch_check(msg.content)

                for pattern in gif_patterns:
                    if re.search(pattern, msg.content):
                        is_gif = True
                        break

                # check if there is text
                if len(msg.content) > 0 and not is_gif and not is_image:
                    embed.add_field(name="", value=msg.content)

                # check if there are attachments
                if len(msg.attachments) > 0:
                    if msg.attachments[0].content_type == "video/mp4" or msg.attachments[0].content_type == "video/quicktime" or msg.attachments[0].content_type == "video/webm": # quicktime = mov
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
                            await gem_channel.send(files=files1, embed=embed)
                        except discord.errors.HTTPException: # file too big, send attachment link instead
                            attachments = ""
                            for attachment in msg.attachments:
                                attachments += attachment.url + "\n"

                            await gem_channel.send(embed=embed)
                            await gem_channel.send(attachments)
                    else:
                        cloud_message = await attachment_cloud.send(file=await msg.attachments[0].to_file())
                        embed.set_image(url=cloud_message.attachments[0].url)
                        await gem_channel.send(embed=embed)
                elif is_gif: # would be a link
                    await gem_channel.send(embed=embed)
                    await gem_channel.send(content=msg.content)
                elif is_image: # would also be a link
                    embed.set_image(url=msg.content)
                    await gem_channel.send(embed=embed)
                else: # anything else
                    await gem_channel.send(embed=embed)

                embed.add_field(name="", value=f"-# [jump to message]({msg.jump_url})", inline=False)
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
    global servers_coal
    global excluded_channels_global

    if "servers.txt" not in os.listdir(os.getcwd()):
        open("servers.txt", "w").close()

    if "coals.txt" not in os.listdir(os.getcwd()):
        open("coals.txt", "w").close()

    # read existing server configuration into servers dictionary
    # server.id: gem_channel <- servers.txt
    with open("servers.txt", "r+") as servers_file:
        read = servers_file.read()
        if read != "":
            servers = ast.literal_eval(read) # interpret as dictionary when reading

    # read existing coal emoji ids into servers_coal dictionary
    # server.id: coal_emoji_id <- coals.txt
    with open("coals.txt", "r+") as coals_file:
        read = coals_file.read()
        if read != "":
            servers_coal = ast.literal_eval(read)

    if "excluded_channels.txt" in os.listdir(os.getcwd()):
        with open("excluded_channels.txt", "r+") as excluded_channels_file:
            read = excluded_channels_file.read()
            if read != "":
                excluded_channels_global = ast.literal_eval(read)

    print("Ready")


@bot.event
async def on_command_error(ctx, error): # FOR CTX
    if isinstance(error, commands.CommandNotFound): # if error instanceof CommandNotFound
        await ctx.send(error)


@bot.tree.error
async def throw_error(interaction: discord.Interaction, error):
    embed = discord.Embed(
        title="Error", description=f"{bot.user.name} ran into a problem and could not process your request.", color=discord.Color.red()
    )
    embed.add_field(name="", value=str(error.__cause__), inline=False)

    try:
        await interaction.followup.send(embed=embed) # use preexisting webhook
    except:
        await interaction.response.send_message(embed=embed) # if the webhook is not found, send a new message

    raise error

bot.run(token)
