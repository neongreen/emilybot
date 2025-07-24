# emilybot

It's a bot.

## notes to self

### how this was added to discord

<https://discordpy.readthedocs.io/en/stable/discord.html>

in the bot settings enable 'message content intent'

add the bot to any server (my server): <https://discord.com/oauth2/authorize?client_id=1397835166906323085&scope=bot> (grab the client id from <https://discord.dev>)

then find the bot in the server members list and DM it and now you can DM it

### sops

created a key for the server with `age-keygen`, added to the server as `AGE_SECRET_KEY`
