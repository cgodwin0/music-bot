import asyncio
import configparser
import json
import logging
import os
import time
import youtube_dl
from discord import FFmpegPCMAudio, PCMVolumeTransformer, Intents
from discord.ext import commands
from youtube_search import YoutubeSearch

youtube_dl.utils.bug_reports_message = lambda: ""

intents = Intents.all()
intents.members = True

bot = commands.Bot(
    command_prefix=commands.when_mentioned_or("!"),
    description="type !help for help",
    intents=intents
)
bot.remove_command("help")

ytdl_format_options = {
    "format": "bestaudio/best",
    "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
    "restrictfilenames": True,
    "noplaylist": True,
    "nocheckcertificate": True,
    "ignoreerrors": True,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "auto",
    "source_address": "0.0.0.0",
}

ffmpeg_options = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

# Bot initializer with config & logging handling
class Bot(commands.Cog):
    def __init__(self):
        pass

    def set_params(self):
        config = configparser.RawConfigParser()
        config_file = os.getcwd() + os.path.sep + "conf" + os.path.sep + "config.cfg"
        config.read(config_file)
        self.token = config.get("general", "discord_token")
        self.channels = config.get("general", "bot_channel_id").replace(' ', '').split(',')
        self.logging_level = config.get("logging", "level")

    def setup_logging(self):
        logging.basicConfig(
            filename="logs/bot.log",
            format="%(asctime)s | %(message)s",
            datefmt="%Y/%m/%d %H:%M:%S",
            level=eval(f"logging.{self.logging_level}"),
        )

    async def start(self):
        self.set_params()
        self.setup_logging()
        time.sleep(1)
        await bot.add_cog(BotCommands(bot, self.channels))
        await bot.start(self.token)


# Youtube Downloader class, features a search function for non-link !play requests and ffmpeg player
class YTDL(PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.1):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get("title")
        self.url = data.get("url")

    def search_yt(search_terms):
        tried = 0
        while tried < 10:
            if tried == 1:
                # Remove the first character from search results, per https://github.com/joetats/youtube_search/issues/21
                search_terms = search_terms[1:]
            results = YoutubeSearch(search_terms, max_results=1).to_json()
            results = json.loads(results)
            # google seems to rate limit the number of queries you can make with a single "device" so this
            # request will sometimes fail to return anything, which can be resolved with using a direct link
            if len(results.get("videos")):
                return "https://www.youtube.com" + results.get("videos")[0].get(
                    "url_suffix"
                )
            else:
                # Retry 10 times
                logging.info(
                    "Youtube Search was rate limited or the video was not found... retrying"
                )
                time.sleep(5)
                tried = tried + 1
        return None

    @classmethod
    async def from_url(inst, url, *, loop=None, stream=False):
        if "https://" not in url:
            # user provided a song name, search youtube for the actual url to play...
            url = inst.search_yt(url)
            if url is None:
                return
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None, lambda: ytdl.extract_info(url, download=not stream)
        )
        if not data:
            return
        if "entries" in data:
            # take first item from a playlist
            data = data["entries"][0]

        filename = data["url"] if stream else ytdl.prepare_filename(data)
        return inst(FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


# All bot commmands available in (!) commands and their definitions
class BotCommands(commands.Cog):
    def __init__(self, bot, channels):
        self.bot = bot
        self.channels = channels
        self.queue = {}
        
        for channel in self.channels:
            self.queue[channel] = []

    @commands.command()
    async def join(self, ctx):
        if not ctx.author.voice:
            return
        channel = bot.get_channel(ctx.author.voice.channel.id)
        # this code exists to check if the bot is being used in the right configured channel
        # I tried to use decorators to stop copy/pasting this code (ik bad practice) but it wouldn't
        # work with the asynchronous nature of the function, so this "it works" code is staying
        if str(ctx.message.channel.id) not in str(self.channels):
            return await bot.is_owner(ctx.author)
        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)
        await channel.connect()
        logging.info(f"Joined channel: {channel}")

    def addToQueue(self, channel, song):
        self.queue[channel].append(song)

    # removes the next song from the queue and streams it to youtube downloader
    async def playNext(self, ctx):
        async with ctx.typing():
            song = self.queue[str(ctx.message.channel.id)].pop(0)
            if song == None:
                return
            player = await YTDL.from_url(song, loop=self.bot.loop, stream=True)
            if not player:
                await ctx.send(
                    "Failed to play song... could be age restricted or we're limited rn by Google. Try a different one :man_shrugging:"
                )
                return
            ctx.voice_client.play(
                player,
                after=lambda e: asyncio.run_coroutine_threadsafe(
                    self.playNext(ctx), self.bot.loop
                ),
            )
        await ctx.send(f"**Now playing:** {player.title}")

    # handle the play command queue system
    @commands.command()
    async def play(self, ctx, *, url=None):
        if str(ctx.message.channel.id) not in str(self.channels):
            return await bot.is_owner(ctx.author)
        if ctx.voice_client is None:
            channel = bot.get_channel(ctx.author.voice.channel.id)
            await channel.connect()
        if not url:
            await ctx.send(
                "Must have something to play... try entering a link or search terms!"
            )
            return
        if ctx.voice_client.is_playing():
            self.addToQueue(str(ctx.message.channel.id), url)
            queue_len = len(self.queue[str(ctx.message.channel.id)])
            await ctx.send(
                f"Song added to queue. There are now {queue_len} songs in the queue."
            )
            return
        self.addToQueue(str(ctx.message.channel.id), url)
        await self.playNext(ctx)

    @commands.command()
    async def skip(self, ctx):
        if str(ctx.message.channel.id) not in str(self.channels):
            return await bot.is_owner(ctx.author)
        if not ctx.author.voice:
            return await ctx.send("Not connected to a voice channel.")
        await ctx.send("Skipping...")
        # catch typeerrors that happens for ctx.voice_client being NoneType
        # doesn't seem to actually be stopping it from working... idk why it's NoneType
        try:
            await ctx.voice_client.stop()
        except TypeError:
            pass
        if len(self.queue[str(ctx.message.channel.id)]):
            await self.playNext(ctx)
        else:
            return await bot.is_owner(ctx.author)

    @commands.command()
    async def stop(self, ctx):
        if not ctx.author.voice:
            return await ctx.send("Not connected to a voice channel.")
        channel = bot.get_channel(ctx.author.voice.channel.id)
        if str(ctx.message.channel.id) not in str(self.channels):
            return await bot.is_owner(ctx.author)
        await ctx.voice_client.disconnect()
        # clear the music queue
        self.queue[str(ctx.message.channel.id)].clear()
        logging.info(f"Left channel: {channel}")

    @commands.command()
    async def pause(self, ctx):
        if not ctx.author.voice:
            return await ctx.send("Not connected to a voice channel.")
        if str(ctx.message.channel.id) not in str(self.channels):
            return await bot.is_owner(ctx.author)
        if ctx.voice_client is None:
            channel = bot.get_channel(ctx.author.voice.channel.id)
            await channel.connect()
        # same NoneType error as above, doesn't affect pause function
        try:
            await ctx.voice_client.pause()
        except TypeError:
            pass

    @commands.command()
    async def resume(self, ctx):
        if not ctx.author.voice:
            return await ctx.send("Not connected to a voice channel.")
        if str(ctx.message.channel.id) not in str(self.channels):
            return await bot.is_owner(ctx.author)
        try:
            await ctx.voice_client.resume()
        except TypeError:
            pass

    @commands.command()
    async def volume(self, ctx, volume=None):
        if ctx.voice_client is None:
            return await ctx.send("Not connected to a voice channel.")
        elif not ctx.voice_client.source:
            return await ctx.send("Not currently playing music.")
        curr_vol = ctx.voice_client.source.volume * 100
        if not volume:
            return await ctx.send(f"Current Volume: {curr_vol}%")

        ctx.voice_client.source.volume = int(volume) / 100
        await ctx.send(f"Changed volume from {curr_vol}% to {volume}%")

    @commands.command()
    async def help(self, ctx):
        if str(ctx.message.channel.id) not in str(self.channels):
            return await bot.is_owner(ctx.author)
        help_txt = (
            "MUSIC MONKEY HELP!\n----------------------------\n!join - joins your channel\n"
            "!play {youtube link OR youtube search text} - adds the song to the queue\n!pause - pauses "
            "the current song\n!resume - resumes the current song\n!skip - skips the current song\n"
            "!stop - stops the song, clears the queue, and leaves the channel\n"
            "!volume {1-100} - adjust the volume of the music (bot must be playing music)"
        )
        await ctx.send(help_txt)

    @bot.event
    async def on_voice_state_update(member, before, after):
        if not member.id == bot.user.id:
            return
        elif before.channel is None:
            voice = after.channel.guild.voice_client
            time = 0
            while True:
                await asyncio.sleep(1)
                time = time + 1
                if voice.is_playing() and not voice.is_paused():
                    time = 0
                if time == 600:
                    await voice.disconnect()
                if not voice.is_connected():
                    break

    @bot.event
    async def on_ready():
        print(f"Logged in as {bot.user}")
        print("------------------------------")
        logging.info(f"Logged in as {bot.user}")
