import discord
from discord.ext import commands
import yt_dlp as youtube_dl
import asyncio
import os
from keep_alive import run  # 👉 Importamos keep_alive

# Mantener activo (solo necesario en Render, Railway o Replit)
run()

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix='!', intents=intents)

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': 'downloads/%(title)s.%(ext)s',
    'quiet': True,
    'noplaylist': True,
    'default_search': 'auto',
}
ffmpeg_options = {
    'options': '-vn',
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.thumbnail = data.get('thumbnail')
        self.url = data.get('webpage_url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=True, volume=0.5):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            data = data['entries'][0]
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data, volume=volume)

queue = []
ultima_cancion = None
volumen_actual = 0.5

@bot.event
async def on_ready():
    print(f'✅ Bot conectado como {bot.user}')
    await bot.change_presence(activity=discord.Game(name="¡Usa !play o !g para música!"))

async def reproducir_siguiente(ctx):
    global ultima_cancion
    if queue:
        player = queue.pop(0)
        ctx.voice_client.play(player, after=lambda e: asyncio.run_coroutine_threadsafe(reproducir_siguiente(ctx), bot.loop))
        ultima_cancion = player
        await bot.change_presence(activity=discord.Game(name=f"🎶 {player.title}"))
        embed = discord.Embed(title="🎶 Reproduciendo", description=f"[{player.title}]({player.url})", color=0x1DB954)
        if player.thumbnail:
            embed.set_thumbnail(url=player.thumbnail)
        await ctx.send(embed=embed)
    else:
        await bot.change_presence(activity=discord.Game(name="¡Usa !play o !g para música!"))

@bot.command(aliases=['g', 'G', 'p'])
async def play(ctx, *, search: str):
    global volumen_actual
    if ctx.author.voice is None:
        await ctx.send("🔇 Debes estar en un canal de voz.")
        return

    voice_channel = ctx.author.voice.channel

    if ctx.voice_client is None:
        try:
            await voice_channel.connect()
        except discord.ClientException:
            await ctx.send("❌ No puedo conectarme al canal de voz.")
            return
    elif ctx.voice_client.channel != voice_channel:
        await ctx.voice_client.move_to(voice_channel)

    async with ctx.typing():
        try:
            player = await YTDLSource.from_url(search, loop=bot.loop, stream=True, volume=volumen_actual)
        except Exception as e:
            await ctx.send(f"❌ Error al reproducir el audio: {e}")
            return

        if not ctx.voice_client.is_playing():
            ctx.voice_client.play(player, after=lambda e: asyncio.run_coroutine_threadsafe(reproducir_siguiente(ctx), bot.loop))
            global ultima_cancion
            ultima_cancion = player
            await bot.change_presence(activity=discord.Game(name=f"🎶 {player.title}"))
            embed = discord.Embed(title="🎶 Reproduciendo", description=f"[{player.title}]({player.url})", color=0x1DB954)
            if player.thumbnail:
                embed.set_thumbnail(url=player.thumbnail)
            await ctx.send(embed=embed)
        else:
            queue.append(player)
            await ctx.send(f"📥 Añadido a la cola: **{player.title}**")

@bot.command(aliases=['cola', 'lista', 'queue'])
async def queue_(ctx):
    if not queue:
        await ctx.send("📭 La cola está vacía.")
    else:
        lista = "\n".join(f"{idx+1}. {song.title}" for idx, song in enumerate(queue))
        await ctx.send(f"📜 **Cola de reproducción:**\n{lista}")

@bot.command()
async def volumen(ctx, value: int):
    global volumen_actual
    if ctx.voice_client is None or not ctx.voice_client.is_playing():
        await ctx.send("❌ No hay ninguna canción reproduciéndose.")
        return
    if value < 0 or value > 100:
        await ctx.send("🔊 El volumen debe estar entre 0 y 100.")
        return
    volumen_actual = value / 100
    if ctx.voice_client.source:
        ctx.voice_client.source.volume = volumen_actual
    await ctx.send(f"🔊 Volumen ajustado a {value}%")

@bot.command()
async def stop(ctx):
    if ctx.voice_client is not None:
        await ctx.voice_client.disconnect()
        await ctx.send("🛑 Desconectado del canal de voz.")
    else:
        await ctx.send("❌ No estoy conectado a ningún canal de voz.")

@bot.command()
async def pause(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("⏸ Pausado.")

@bot.command()
async def resume(ctx):
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("▶ Reanudado.")

@bot.command(aliases=['s', 'S'])
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭ Canción saltada.")
    else:
        await ctx.send("❌ No hay ninguna canción reproduciéndose.")

@bot.command(name='repetir')
async def loop(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        source = ctx.voice_client.source
        ctx.voice_client.stop()
        ctx.voice_client.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(loop(ctx), bot.loop))
        await ctx.send("🔁 Repetir activado.")
    else:
        await ctx.send("❌ No hay ninguna canción reproduciéndose.")

@bot.command()
async def estado(ctx):
    await ctx.send("✅ El bot está funcionando correctamente.")

@bot.command()
async def donde(ctx):
    voice = ctx.voice_client
    if voice and voice.channel:
        await ctx.send(f"🎧 Estoy en el canal de voz: **{voice.channel.name}**")
    else:
        await ctx.send("❌ No estoy en ningún canal de voz.")

@bot.command()
async def ultima(ctx):
    if ultima_cancion:
        await ctx.send(f"🔂 Última canción reproducida: **{ultima_cancion.title}**")
    else:
        await ctx.send("❌ Aún no se ha reproducido ninguna canción.")

if __name__ == "__main__":
    bot.run(TOKEN)
