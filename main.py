import ast
import datetime
import io
import os
import re
import signal

import aiohttp
import requests
import discord
import asyncio
from PIL import Image
from dotenv import load_dotenv
from discord.ext import commands

load_dotenv()
token = os.environ.get('token')

intents = discord.Intents.default()
client = discord.Client(intents=intents)
intents.members = True
intents.message_content = True
intents.moderation = True

bot = commands.Bot(command_prefix='​', intents=intents)

# server.id: gem_channel
servers = {}
servers_coal = {}
excluded_channels_global = {}
french = []

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


def serialize_misc_dict(misc_list, server_id):
    with open("misc_list-" + str(server_id) + ".txt", "w", encoding="utf-8") as f:
        f.write(str(misc_list))


def deserialize_misc_dict(server_id):
    try:
        with open("misc_list-" + str(server_id) + ".txt", "r", encoding="utf-8") as f:
            read = f.read()
            return ast.literal_eval(read) if read else {} # force to dictionary
    except FileNotFoundError:
        return {}


def serialize_thread_list(thread_list, server_id):
    with open("thread_list-" + str(server_id) + ".txt", "w") as f:
        for thread in thread_list:
            f.write(str(thread) + "\n")


def deserialize_thread_list(server_id):
    try:
        with open("thread_list-" + str(server_id) + ".txt", "r") as f:
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


def emoji_key(emoji) -> str:
    if isinstance(emoji, str):
        return f"unicode:{emoji}"

    return f"custom:{emoji.id}"


def emoji_display_name(emoji) -> str:
    if isinstance(emoji, str):
        return emoji

    return emoji.name


async def send_embed(msg: discord.Message, attachment_cloud: discord.TextChannel, target_channel: discord.TextChannel, append: str = ""):
    embed = discord.Embed(colour=msg.author.color, timestamp=msg.created_at)

    embed.set_author(name=msg.author.display_name, icon_url=msg.author.avatar)

    # patterns for links only
    gif_patterns = [
        r'https?://(?:www\.)?tenor\.com/view/[\w-]+',
        r'https?://(?:www\.)?gfycat\.com/[\w-]+',
        r'https?://media\d?\.giphy\.com/media/[\w-]+/giphy\.gif',
        r'.*\.gif(?:$|\?.*)',
        r'http(s)?:\/\/klipy\.com\/gifs\/[\w-]+'
    ]

    video_patterns = [
        r'http(s)?:\/\/cdn\.discordapp\.com\/attachments\/[\w-]+\/[\w-]+\/[\w-]+\.(mov|webm|mp4)\?[\S-]+'
    ]

    image_patterns = [
        r'http(s)?:\/\/cdn\.discordapp\.com\/attachments\/[\w-]+\/[\w-]+\/[\w-]+\.(png|jpg)[\S-]+'
    ]

    sm_post_patterns = [
        r'http(s)?:\/\/(www\.|)(x|fxtwitter|fixupx|vxtwitter|girlcockx)\.com\/[\w-]+\/status\/[\S-]+',
        r'http(s)?:\/\/(www\.|)(instagram|vxinstagram|kkinstagram)\.com\/reel\/[\S-]+',
        r'http(s)?:\/\/(www\.|music\.|)(youtu\.be|youtube\.com)\/(watch\?v=|)[\S-]+'
    ]

    is_gif = False
    is_image = fetch_check(msg.content)
    is_video = False
    is_sm_post = False

    gif_link = ""
    video_link = ""
    sm_post_link = ""
    image_link = ""

    for pattern in gif_patterns:
        if re.search(pattern, msg.content):
            is_gif = True
            gif_link = re.search(pattern, msg.content).group(0)
            break

    for pattern in video_patterns:
        if re.search(pattern, msg.content):
            is_video = True
            video_link = re.search(pattern, msg.content).group(0)
            break

    for pattern in sm_post_patterns:
        if re.search(pattern, msg.content):
            is_sm_post = True
            sm_post_link = re.search(pattern, msg.content).group(0)
            break

    for pattern in image_patterns:
        if re.search(pattern, msg.content):
            image_link = re.search(pattern, msg.content).group(0)

    print("[EMBED] is_gif = " + str(is_gif))
    print("[EMBED] is_image = " + str(is_image))
    print("[EMBED] is_video = " + str(is_video))
    print("[EMBED] is_sm_post = " + str(is_sm_post))

    # check if there is text
    if len(msg.content) > 0 and not is_gif and not is_image:
        if is_video or is_sm_post:
            embed.add_field(name="", value=msg.content.replace(video_link if video_link != "" else sm_post_link, ""))
        else:
            embed.add_field(name="", value=msg.content)

    # check if there are attachments
    if len(msg.attachments) > 0:
        # if its a video
        if msg.attachments[0].content_type == "video/mp4" or msg.attachments[0].content_type == "video/quicktime" or msg.attachments[0].content_type == "video/webm":  # quicktime = mov
            files = []
            for attachment in msg.attachments:
                file = await attachment.to_file()
                file.spoiler = attachment.is_spoiler()
                files.append(file)

            embed.add_field(name="", value=f"-# [jump to message]({msg.jump_url})", inline=False)
            embed.set_footer(text="↑")

            # jank but creative way of forcing embed width
            if msg.attachments[0].width is not None and msg.attachments[0].height is not None:
                # discord displays only max of 550x350 videos and they are resized while maintaining aspect ratio
                scale = min(550 / int(msg.attachments[0].width), 350 / int(msg.attachments[0].height), 1.0)
                attachment_width = round(int(msg.attachments[0].width) * scale)

                print("[EMBED] fake image width is: " + str(attachment_width))
                print("[EMBED] post-resize fake image width is: " + str(attachment_width-12-16))

                # remove 12 px and 16 px of padding on sides of embed added by discord
                fake_img = Image.new('RGBA', (attachment_width-12-16, 1), (0, 0, 0, 0))

                with io.BytesIO() as image_binary:
                    fake_img.save(image_binary, 'PNG')
                    image_binary.seek(0)
                    fake_img_link = await attachment_cloud.send(file=discord.File(fp=image_binary, filename=f'image-{msg.attachments[0].width}.png'))

                embed.set_image(url=fake_img_link.attachments[0].url)

            try:
                await target_channel.send(files=files, embed=embed)
            except discord.errors.HTTPException:  # file too big, send attachment link instead
                attachments = ""
                for attachment in msg.attachments:
                    attachments += attachment.url + "\n"

                await target_channel.send(attachments, embed=embed)
            return  # avoid sending embed again
        else: # if its an image
            cloud_message = await attachment_cloud.send(file=await msg.attachments[0].to_file())
            embed.set_image(url=cloud_message.attachments[0].url)
    elif is_video: # special video links that can be fetched from a cdn
        async with aiohttp.ClientSession() as session:
            async with session.get(sm_post_link if sm_post_link != "" else video_link) as response:
                if response.status != 200:
                    print("ERROR " + str(response.status))
                    return

                video_buffer = io.BytesIO()
                async for chunk in response.content.iter_chunked(8192):
                    video_buffer.write(chunk)
                video_buffer.seek(0)

                embed.set_footer(text="↑")
                await target_channel.send(file=discord.File(fp=video_buffer, filename="video.mp4"))
    elif is_gif or is_sm_post:  # would be a link, should just be sent raw
        embed.add_field(name="", value=f"-# [jump to message]({msg.jump_url})", inline=False)
        embed.set_footer(text="↓")
        await target_channel.send(embed=embed)
        await target_channel.send(content=sm_post_link or gif_link)
        return
    elif is_image:
        async with aiohttp.ClientSession() as session:
            async with session.get(image_link) as response:
                if response.status != 200:
                    print("ERROR " + str(response.status))
                    return

                image_buffer = io.BytesIO()
                async for chunk in response.content.iter_chunked(8192):
                    image_buffer.write(chunk)
                image_buffer.seek(0)

                embed.add_field(name="", value=f"-# [jump to message]({msg.jump_url})", inline=False)
                message = await attachment_cloud.send(file=discord.File(fp=image_buffer, filename="image.png"))
                embed.set_image(url=message.attachments[0])
                await target_channel.send(embed=embed)
        return

    embed.add_field(name="", value=f"-# [jump to message]({msg.jump_url})", inline=False)

    if append != "":
        await target_channel.send(embed=embed, content=append)
    else:
        await target_channel.send(embed=embed)


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
            excluded_channels_from_file.setdefault(interaction.guild.id, []).append(channel.id)
        except ValueError: # if the file exists but the guild id is not in it
            excluded_channels_from_file.update({interaction.guild.id: [channel.id]})

    # sync buffer with file
    global excluded_channels_global
    excluded_channels_global = excluded_channels_from_file

    with open("excluded_channels.txt", "w") as f:
        f.write(str(excluded_channels_global))

    await interaction.response.send_message("Channel added to excluded channels list.", ephemeral=True)


# @bot.event
# async def on_message(msg: discord.Message):
#     if msg.author.bot:
#         return

#     match = set(msg.content.lower().split(" ")).intersection(french)
#     if len(match) > 0:
#         if isinstance(msg.author, discord.Member):
#             try:
#                 await msg.author.timeout(datetime.timedelta(minutes=1), reason="Speaking french")

#                 words = ""
#                 for i, word in enumerate(match):
#                     words += word
#                     if i < len(match) - 1:
#                         words += ", "

#                 if len(match) > 1:
#                     await msg.channel.send("\"" + words + "\" are french words, start speaking english or face punishment.")
#                 else:
#                     await msg.channel.send("\"" + words + "\" is a french word, start speaking english or face punishment.")
#             except discord.Forbidden as e:
#.                print("\033[1;33m" + "Cannot timeout user (role hierarchy issue?): " + "\033[0m")
#                 print(e)




@bot.event
async def on_raw_reaction_add(event: discord.RawReactionActionEvent):
    msg = await (await bot.fetch_channel(event.channel_id)).fetch_message(event.message_id)
    global servers
    gem_channel_id = servers.get(msg.guild.id) # fetch the channel value int from the associated server key int
    gem_channel = await bot.fetch_channel(gem_channel_id)  # will never not be an int
    attachment_cloud_id = 1429688927601823804 # for ensuring images are saved correctly without local storage
    attachment_cloud = bot.get_channel(attachment_cloud_id)
    gem_limit = 3
    coal_limit = 5
    pin_react_limit = 5
    misc_react_limit = 3
    global excluded_channels_global
    excluded_channels = excluded_channels_global.get(event.guild_id) if excluded_channels_global.get(event.guild_id) is not None else []
    global servers_coal
    coal_emoji_id = servers_coal.get(event.guild_id)

    # count coal reacts
    react_count = 0
    # count gem reacts
    gem_react_count = 0
    # count misc reacts
    misc_react_count = 0
    # the emoji itself
    top_misc_react = ""

    misc_dict = deserialize_misc_dict(event.guild_id)
    files = []
    pinned_list = deserialize_pinned_list(event.guild_id)
    for reaction in msg.reactions:
        if reaction.emoji == "💎":
            gem_react_count = reaction.count

            # users cannot count their own reaction
            # if msg.author == event.member:
            #     gem_react_count -= 1
            break

        if coal_emoji_id is not None and coal_emoji_id in str(reaction.emoji):
            react_count = reaction.count

            # users cannot count their own reaction
            if msg.author == event.member:
                react_count -= 1
            break

        # any other reaction, get the highest number
        if reaction.count > misc_react_count:
            misc_react_count = reaction.count
            top_misc_react = reaction.emoji

            # users cannot count their own reaction
            if msg.author == event.member:
                misc_react_count -= 1

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

                current_channel = bot.get_channel(event.channel_id)

                await send_embed(msg, attachment_cloud, gem_channel)
                gem_list.append(msg.id)
                serialize_gem_list(gem_list, event.guild_id)

    if misc_react_count >= misc_react_limit:
        thread_list = deserialize_thread_list(event.guild_id)

        misc_key = emoji_key(top_misc_react)
        misc_name = emoji_display_name(top_misc_react)

        if misc_key not in misc_dict.keys():
            message = await gem_channel.send(content=misc_name)
            thread = await message.create_thread(
                name=misc_name
            )
            misc_dict.update({misc_key: thread.id})
            serialize_misc_dict(misc_dict, event.guild_id)

        thread = await bot.fetch_channel(int(misc_dict.get(misc_key)))
        msg = await (await bot.fetch_channel(event.channel_id)).fetch_message(event.message_id)

        # Check if this message was already posted in the thread
        existing_message = None
        async for message in thread.history(limit=None):
            if message.author.id == bot.user.id and len(message.embeds) > 0:
                # Check if the embed's author matches and the jump link contains the original message ID
                embed = message.embeds[0]
                if embed.author and embed.author.name == msg.author.display_name:
                    for field in embed.fields:
                        if f"({msg.jump_url})" in field.value:
                            existing_message = message
                            break
                if existing_message:
                    break

        # If message already exists, edit it with updated reaction count
        if existing_message:
            await existing_message.edit(content=f"{top_misc_react} {misc_react_count}")
            return

        await send_embed(msg=msg, attachment_cloud=attachment_cloud, target_channel=thread, append=f"{top_misc_react} {misc_react_count}")

        thread_list.append(thread.id)
        serialize_thread_list(thread_list, event.guild_id)


    if gem_react_count >= pin_react_limit and msg.channel.id not in excluded_channels and msg.id not in pinned_list and msg.author.id != bot.user.id:
        pinned_list.append(msg.id)
        serialize_pinned_list(pinned_list, event.guild_id)
        print(str(msg.id) + " pinned | gems: " + str(gem_react_count) + " | short id: " + str(msg.id)[0] + str(msg.id)[1])

        try:
            await msg.pin()
        except Exception as e:
            print(e)


@bot.event
async def on_raw_reaction_remove(event: discord.RawReactionActionEvent):
    msg = await (await bot.fetch_channel(event.channel_id)).fetch_message(event.message_id)
    global servers
    misc_react_limit = 3

    # count misc reacts
    misc_react_count = 0
    # the emoji itself
    top_misc_react = ""

    misc_dict = deserialize_misc_dict(event.guild_id)

    for reaction in msg.reactions:
        if reaction.emoji == "💎":
            continue

        coal_emoji_id = servers_coal.get(event.guild_id)
        if coal_emoji_id is not None and coal_emoji_id in str(reaction.emoji):
            continue

        # any other reaction, get the highest number
        if reaction.count > misc_react_count:
            misc_react_count = reaction.count
            top_misc_react = reaction.emoji

            # users cannot count their own reaction
            if msg.author.id == event.user_id:
                misc_react_count -= 1

    if misc_react_count >= misc_react_limit and top_misc_react != "":
        misc_key = emoji_key(top_misc_react)

        if misc_key in misc_dict.keys():
            thread = await bot.fetch_channel(int(misc_dict.get(misc_key)))

            # Find the existing message in the thread
            existing_message = None
            async for message in thread.history(limit=None):
                if message.author.id == bot.user.id and len(message.embeds) > 0:
                    embed = message.embeds[0]
                    if embed.author and embed.author.name == msg.author.display_name:
                        for field in embed.fields:
                            if f"({msg.jump_url})" in field.value:
                                existing_message = message
                                break
                    if existing_message:
                        break

            # Update the existing message with the new reaction count
            if existing_message:
                await existing_message.edit(content=f"{top_misc_react} {misc_react_count}")


@bot.event
async def on_ready():
    # print("Syncing command tree")

    # await bot.tree.sync()
    # for command in bot.commands:
    #     print(command.name)
    # for command in bot.tree.get_commands():
    #     print(command.name)

    try:
        print("\nSyncing command tree:")

        tree_commands = await asyncio.wait_for(bot.tree.sync(), timeout=10.0)

        if len(tree_commands) < 1:
            print("\033[1;33m" + "WARNING: No commands were synced." + "\033[0m")
        for command in tree_commands:
            print(command.name)
    except asyncio.TimeoutError:
        print("Could not sync commands: Command tree sync timed out after waiting for 10 seconds")
    except Exception as e:
        print("Could not sync commands:", e)

    print("\nSyncing local files with buffer")
    global servers
    global servers_coal
    global excluded_channels_global
    global french

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

    with open("french.txt", "r") as f:
        for line in f.readlines():
            french.append(line.strip())

    print("\nReady in:")
    for guild in bot.guilds:
        print(guild)


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
