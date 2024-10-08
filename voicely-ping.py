import json
import discord
from discord.ext import commands

# Load bot token from file
with open('../token', 'r') as file:
    bot_token = file.read().strip()

# Load notify data from file (or return an empty dictionary if the file doesn't exist)
def load_pings():
    try:
        with open('pings.json', 'r') as f:
            # Load JSON data into a dictionary
            return json.load(f)
    except FileNotFoundError as error:
        print(f"Cannot load pings.json: {error}")
        # If the file doesn't exist, return an empty dictionary
        return {}

# Save the current notify data to a JSON file
def save_pings():
    with open('pings.json', 'w') as f:
        # Write the dictionary to the JSON file
        json.dump(pings, f)

# Define intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True
intents.messages = True
intents.members = True

# Set up the bot
class Bot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.default_settings = {
            "notify_count": 3,
            "reset_count": 0
        }

    async def setup_hook(self):
        print(f"Setup complete for {self.user}")


# Create the bot instance with a command prefix
bot = Bot()

# Store users who want to be notified in a dictionary {guild_id: set(user_ids)}
# Load the data from the JSON file when the bot starts
pings = load_pings()

@bot.event
async def on_ready():
    """Triggered when the bot has successfully connected to Discord."""
    print(f'Logged in as {bot.user}')

class AddPingModal(discord.ui.Modal, title="Setup a ping"):
    notify_count = discord.ui.TextInput(
        label="Notify count",
        placeholder=str(bot.default_settings["notify_count"]),
        required=False,
        max_length=3
    )

    channels = discord.ui.ChannelSelect(
        channel_types=[discord.ChannelType.voice],
        placeholder="Select one or more channels",
        max_values=25
    )

    async def on_submit(self, interaction: discord.Interaction):
        if not self.notify_count.value:
            notify_count = bot.default_settings["notify_count"]
        else:
            try:
                notify_count = int(self.notify_count.value)
            except:
                await interaction.response.send_message(f"{self.notify_count.value} is not a valid number! Only positive whole numbers are allowed.")
                return
            
        notify_str = str(notify_count)
        if len(self.channels.values) <= 0:
            await interaction.response.send_message(f"You must select at least one channel!")
            return
        
        guild_id = str(interaction.guild.id)
        user_id = str(interaction.user.id)
        # Add the user to the notification set for the guild
        if guild_id not in pings:
            pings[guild_id] = set()
        if user_id not in pings[guild_id]:
            pings[guild_id][user_id] = set()

        links = []
        for channel in self.channels.values:
            channel_id = str(channel.id)
            if channel_id not in pings[guild_id]:
                pings[guild_id][channel_id] = set()
            if notify_str not in pings[guild_id][channel_id]:
                pings[guild_id][channel_id][notify_str] = []
            
            if user_id not in pings[guild_id][channel_id][notify_str]:
                pings[guild_id][channel_id][notify_str].append(user_id)

            links.append(f"https://discord.com/channels/{interaction.guild_id}/{channel.id}")
            
        # Save the updated notification list to the JSON file
        save_pings()

        all_links = "\n- ".join(links)

        if len(links) == 1:
            channel = "any of the following channels"
        else:
            channel = "the following channel"

            
        confirmation_embed = discord.Embed(title="Set notify count", description=f'You will be notified when {notify_count} people are in {channel}:')
        channel_list = discord.Embed(description=all_links)
        # Respond to the user with the text they entered.
        await interaction.response.send_message(embeds=[confirmation_embed, channel_list], ephemeral=True)


@bot.hybrid_command()
async def addping(ctx: commands.Context):
    """Add a voice channel for you to be notified for."""
    modal = AddPingModal()
    await ctx.send(modal=modal, reference=ctx.message, ephemeral=True)

@bot.hybrid_command()
async def removeping(ctx: commands.Context):
    """
    Command for users to disable notifications.
    Removes the user ID from the set of users to be notified for the current guild.
    """
    guild_id = str(ctx.guild.id)
    user_id = str(ctx.author.id)
    # Remove the user from the notification set for the guild, if they exist
    if guild_id in pings and user_id in pings[guild_id]:
        pings[guild_id].remove(user_id)
        # Save the updated notification list to the JSON file
        save_pings()
        await ctx.send(f'You will no longer receive voice channel notifications.', reference=ctx.message, ephemeral=True)
    else:
        await ctx.send(f'You were not signed up for notifications.', reference=ctx.message, ephemeral=True)

@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    """
    Event triggered when a user's voice state changes.
    Checks if a user has joined a voice channel and sends a DM to users who opted in for notifications.
    """
    # Check if the user joined a voice channel (wasn't in one before, but now is)
    if before.channel is None and after.channel is not None:
        guild_id = str(member.guild.id)
        # Get users to notify for this guild
        if guild_id in pings:
            channel_link = f"https://discord.com/channels/{guild_id}/{after.channel.id}"
            # Notify all users who opted in
            for user_id in pings[guild_id]:
                user = bot.get_user(int(user_id))
                if user:
                    try:
                        # Send a DM with the link to join the voice channel
                        await user.send(
                            f'{member.name} has joined {after.channel.name}. Click here to join: {channel_link}'
                        )
                    except discord.Forbidden:
                        # Handle cases where the bot can't DM the user (e.g., DMs are disabled)
                        print(f'Could not send DM to {user.name}')

# Run the bot with the loaded token
bot.run(bot_token)
