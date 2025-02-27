import json
import discord
from discord import app_commands
from discord.ext import commands
from typing import List
import math
from enum import Enum
import datetime
# import datetime

# Load bot token from file
with open('../token', 'r') as file:
    bot_token = file.read().strip()

# Define intents
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.members = True

# Set up the bot
class Bot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="$", intents=intents)
        self.default_settings = {
            "notify_count": 3,
            "reset_count": 0,
            "ephemeral": "true"
        }
        self.notified_channels = {}
        # This dictionary will look like this:
        # {
        #     "user_id_1": {
        #         "channel_id_1": [notify_count_1, notify_count_2],
        #         "channel_id_2": [notify_count_1, notify_count_2]
        #     },
        #     "user_id_2": {
        #         "channel_id_1": [notify_count_1, notify_count_2],
        #         "channel_id_2": [notify_count_1, notify_count_2]
        #     }
        # }
        # make sure to not notify people if they are already in the channel

    async def setup_hook(self):
        print(f"Setup complete for {self.user}")


# Create the bot instance with a command prefix
bot = Bot()

# region save and load settings

# region pings
# Store users who want to be notified in a dictionary {guild_id: set(user_ids)}
# Load notify data from file (or return an empty dictionary if the file doesn't exist)
def load_pings():
    try:
        with open('data/pings.json', 'r') as f:
            # Load JSON data into a dictionary
            return json.load(f)
    except FileNotFoundError as error:
        print(f"Cannot load pings.json: {error}")
        # If the file doesn't exist, return an empty dictionary
        return {}


# Load the data from the JSON file when the bot starts
pings = load_pings()

# Save the current notify data to a JSON file
def save_pings():
    with open('data/pings.json', 'w') as f:
        # Write the dictionary to the JSON file
        json.dump(pings, f)

# endregion

# region server settings
# Store users who want to be notified in a dictionary {guild_id: set(user_ids)}
# Load notify data from file (or return an empty dictionary if the file doesn't exist)
def load_server_settings():
    try:
        with open('data/server_settings.json', 'r') as f:
            # Load JSON data into a dictionary
            return json.load(f)
    except FileNotFoundError as error:
        print(f"Cannot load server_settings.json: {error}")
        # If the file doesn't exist, return an empty dictionary
        return {}


# Load the data from the JSON file when the bot starts
server_settings = load_server_settings()

# Save the current notify data to a JSON file
def save_server_settings():
    with open('data/server_settings.json', 'w') as f:
        # Write the dictionary to the JSON file
        json.dump(server_settings, f)

# endregion

# region silent hours

# def load_times():
#     try:
#         with open('data/silent_hours.json', 'r') as f:
#             # Load JSON data into a dictionary
#             return json.load(f)
#     except FileNotFoundError as error:
#         print(f"Cannot load silent_hours.json: {error}")
#         # If the file doesn't exist, return an empty dictionary
#         return {}


# # Load the data from the JSON file when the bot starts
# silent_hours = load_times()

# # Save the current notify data to a JSON file
# def save_times():
#     with open('data/silent_hours.json', 'w') as f:
#         # Write the dictionary to the JSON file
#         json.dump(silent_hours, f)

# endregion

# endregion

# region get ephemeral
def return_bool(value: str):
    if value.strip().lower() in ['true', '1', 'yes', 'y']:
        return True
    elif value.strip().lower() in ['false', '0', 'no', 'n']:
        return False
    else:
        raise ValueError("Invalid input for boolean conversion.")

def get_ephemeral(guild_id_str: str):
    if guild_id_str in server_settings and "ephemeral" in server_settings[guild_id_str]:
        return not return_bool(server_settings[guild_id_str]["ephemeral"])
    else:
        return not return_bool(bot.default_settings["ephemeral"])
# endregion


@bot.event
async def on_ready():
    """Triggered when the bot has successfully connected to Discord."""
    print(f'Logged in as {bot.user}')

# region views and modals

# region add ping
class VoiceChannelSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(placeholder="Select one or more channels", min_values=1, max_values=25)
        self.channel_types = [discord.ChannelType.voice]

    async def callback(self, interaction: discord.Interaction):
        if len(self.values) <= 0:
            await interaction.response.send_message(f"You must select at least one channel!", ephemeral=True)
            return
        
        

        if len(self.values) > 1:
            plural = "s"
            channel = "any of the following channels"
        else:
            plural = ""
            channel = "the following channel"

        confirmation_texts: List[str] = []
        # all_links = f"You have selected the following channel{plural}:"
        all_links = ""
        # channel_links = ""
        for channel in self.values:
            this_text = f"- https://discord.com/channels/{interaction.guild_id}/{channel.id}"
            # print(len(this_text))
            if len(all_links + "\n" + this_text) > 2048:
                confirmation_texts.append(all_links)
                all_links = this_text
            else:
                all_links += "\n" + this_text
        
        # print(len(all_links))
        confirmation_texts.append(all_links)

        confirmation_embeds: List[discord.Embed] = []
        for x in range(len(confirmation_texts)):
            if x > 0:
                title = None
            else:
                title = "Selected channels"

            confirmation_embeds.append(discord.Embed(title=title, description=confirmation_texts[x]))

        
        count_embed = discord.Embed(title="Set notify count", description=f"In the modal that opens, type a number that represents the **number of people** that need to be in the channel{plural} you selected for you to be notified.\n\nUnless you set up more than one ping for it, you won\'t be notified again until after **everyone has left** the channel.")

        confirmation_embeds.append(count_embed)
        
        await interaction.response.send_message(embeds=confirmation_embeds, view=OpenModalView(self.values, confirmation_texts), ephemeral=True)

class AddPingChannelView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(VoiceChannelSelect())

class AddPingCountModal(discord.ui.Modal, title="Specify member count"):
    plural = ""
    channel_ref = ""
    
    def __init__(self, channels: List[discord.app_commands.AppCommandChannel], links: List[str]):
        super().__init__()
        self.channels = channels
        self.links = links
        if len(channels) > 1:
            self.plural = "s"
            self.channel_ref = "any of the following channels"
        else:
            self.plural = ""
            self.channel_ref = "the following channel"
        # self.add_item(VoiceChannelSelect())
    

    notify_count = discord.ui.TextInput(
        label="Member count",
        placeholder="Enter a number",
        max_length=3,
        style=discord.TextStyle.short
        
    )

    async def on_submit(self, interaction: discord.Interaction):
        # if not self.notify_count.value:
        #     notify_count = bot.default_settings["notify_count"]
        # else:

        error_message = f"`{self.notify_count.value}` is not a valid number! Only positive whole numbers are allowed."

        try:
            notify_count = int(self.notify_count.value)
        except:
            await interaction.response.send_message(error_message, ephemeral=True)
        
        else:
            if notify_count <= 0:
                await interaction.response.send_message(error_message, ephemeral=True)
                return
            
            notify_str = str(notify_count)
            
            guild_id = str(interaction.guild_id)
            user_id = str(interaction.user.id)
            # Add the user to the notification set for the guild
            if guild_id not in pings:
                pings[guild_id] = {}
            # if user_id not in pings[guild_id]:
            #     pings[guild_id][user_id] = {}

            for channel in self.channels:
                channel_id = str(channel.id)
                if channel_id not in pings[guild_id]:
                    pings[guild_id][channel_id] = {}
                if notify_str not in pings[guild_id][channel_id]:
                    pings[guild_id][channel_id][notify_str] = []
                
                if user_id not in pings[guild_id][channel_id][notify_str]:
                    pings[guild_id][channel_id][notify_str].append(user_id)

                # region example
                # This dictionary will look something like this:
                # {
                #     guild_id_1: {
                #         channel_id_1: {
                #             count_1: [user_id_1, user_id_2],
                #             count_2: [user_id_1, user_id_2]
                #         },
                #         channel_id_2: {
                #             count_1: [user_id_1, user_id_2],
                #             count_2: [user_id_1, user_id_2]
                #         }
                #     },
                #     guild_id_2: {
                #         channel_id_1: {
                #             count_1: [user_id_1, user_id_2],
                #             count_2: [user_id_1, user_id_2]
                #         },
                #         channel_id_2: {
                #             count_1: [user_id_1, user_id_2],
                #             count_2: [user_id_1, user_id_2]
                #         }
                #     }
                # }
                # endregion

            save_pings()

            if len(self.channels) > 1:
                plural = "s"
                channel = "any of the following channels"
            else:
                plural = ""
                channel = "the following channel"

            if notify_count > 1:
                people = "people"
                verb = "are"
            else:
                people = "person"
                verb = "is"

                
            confirmation_embed = discord.Embed(title=f"Ping{plural} set!", description=f'You will be notified in dm\'s when **{notify_count} {people}** {verb} in {channel}:')

            channel_embeds: List[discord.Embed] = []
            for text in self.links:
                channel_embeds.append(discord.Embed(description=text))
            # channel_list = discord.Embed(description=self.links)

            all_embeds = [confirmation_embed] + channel_embeds
            # Respond to the user with the text they entered.
            await interaction.response.send_message(embeds=all_embeds, ephemeral=get_ephemeral(guild_id))

class OpenModalView(discord.ui.View):
    def __init__(self, channels: List[discord.app_commands.AppCommandChannel], links: List[str]):
        super().__init__()
        self.channels = channels
        self.links = links
    
    @discord.ui.button(label="Continue")
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AddPingCountModal(self.channels, self.links))
# endregion

# region remove ping
def remove_ping_embed(page: int, pages: int):
    title = "Remove pings"
    description = "Choose from the dropdowns below to remove those pings."
    embed = discord.Embed(title=title, description=description)
    if pages > 1:
        # title = f"Remove pings `({page + 1}/{pages})`"
        # return 
        embed.set_footer(text=f"Page {page + 1} of {pages}")
    # else:
        # title = "Remove pings"
    return embed
    

class RemovePingSelect(discord.ui.Select):    
    def setup_select(self, options_dict: List[dict]):
        options: List[discord.SelectOption] = []
        for dict in options_dict:
            # channel_str = dict["channel_str"]
            count_str = dict["count_str"]
            try:
                count = int(count_str)
            except:
                print(f"Error converting {count_str} to an int.")
                count = None
            
            if count is None:
                plural = "(s)"
            elif count > 1:
                plural = "s"
            else:
                plural = ""
            options.append(discord.SelectOption(label=f"{dict['channel_name']}: {count_str} member{plural}", value=f"{dict['guild_str']}/{dict['channel_str']}/{count_str}", description=dict["guild_name"]))
        return options
        
    def set_placeholder(self, options: List[dict]):
        start_guild: str = options[0]["guild_name"]
        end_guild: str = options[len(options) - 1]["guild_name"]

        if start_guild == end_guild:
            return f"Pings in {start_guild}"
        else:
            return f"Servers {start_guild} to {end_guild}"
    

    def __init__(self, options: List[discord.SelectOption], index: int):
        super().__init__(min_values=1, max_values=len(options), options = self.setup_select(options), placeholder=self.set_placeholder(options))


    async def callback(self, interaction: discord.Interaction):
        if len(self.values) <= 0:
            await interaction.response.send_message(f"You must select at least one ping!", ephemeral=True)
            return
        
        for value in self.values:
            values = value.split('/')
            guild_id = values[0]
            channel_id = values[1]
            count_str = values[2]

            pings[guild_id][channel_id][count_str].remove(str(interaction.user.id))

            if len(pings[guild_id][channel_id][count_str]) == 0:
                del pings[guild_id][channel_id][count_str]
            if len(pings[guild_id][channel_id]) == 0:
                del pings[guild_id][channel_id]
            if len(pings[guild_id]) == 0:
                del pings[guild_id]

        save_pings()

        ping_count = len(self.values)
        if ping_count > 1:
            plural = "s"
        else:
            plural = ""
        await interaction.response.send_message(f"Successfully removed **{len(self.values)} ping{plural}**.", ephemeral=get_ephemeral(str(interaction.guild_id)))

class NavigationType(Enum):
    next = "next"
    previous = "previous"

def get_select_pages(all_options: List[dict]):
    select_count = math.ceil(len(all_options) / 25)
    if select_count == 5:
        pages = 1
    else:
        pages = math.ceil(select_count / 4)

    return pages

class NavigationButton(discord.ui.Button):
    def __init__(self, navigation_type: NavigationType, all_options: List[dict], page: int, pages: int):
        self.all_options = all_options
        self.page = page
        self.pages = pages
        if navigation_type == NavigationType.next:
            # print('got here')
            label = "Next Page"
            # emoji = "⏩"
            self.next_page = self.page + 1
        elif navigation_type == NavigationType.previous:
            label = "Previous Page"
            # emoji = "⏪"
            self.next_page = self.page - 1
        super().__init__(label=label)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=remove_ping_embed(self.next_page, self.pages), view=RemovePingView(self.all_options, self.next_page), ephemeral=True)


class RemovePingView(discord.ui.View):
    # pages = 0
    # # select_count = 0
    # all_options: List[dict] = []
    # count = 0
    # page = 0
    def __init__(self, options: List[dict], page: int):
        super().__init__()
        self.all_options = options
        self.page = page
        self.pages = get_select_pages(options)

        self.index = page * 4 * 25

        self.count = 0
        
        def add_option():
            options = self.all_options[self.index:min(self.index + 25, len(self.all_options))]
            select = RemovePingSelect(options, self.index)
            self.add_item(select)
            self.index += 25
            self.count += 1

        
        while (self.index < len(self.all_options)) and (self.count < 4):
            add_option()
        
        if self.pages == 1 and self.index < len(self.all_options):
            add_option()
        
        self.add_navigation()

    def add_navigation(self):
        if self.pages > 1:
            if self.page < self.pages - 1:
                self.add_item(NavigationButton(NavigationType.next, self.all_options, self.page, self.pages))
            if self.page != 0:
                self.add_item(NavigationButton(NavigationType.previous, self.all_options, self.page, self.pages))
        
# endregion

# region silent hours
# class SilentHoursStart(discord.ui.View):
#     def __init__(self, channels: List[discord.app_commands.AppCommandChannel], links: List[str]):
#         super().__init__()
#         self.channels = channels
#         self.links = links
    
#     @discord.ui.button(label="Continue")
#     async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
#         await interaction.response.send_modal(AddPingCountModal(self.channels, self.links))


# class SilentHoursModal(discord.ui.Modal, title="Specify member count"):
#     def __init__(self, channels: List[discord.app_commands.AppCommandChannel], links: List[str]):
#         super().__init__()
    

#     start_time = discord.ui.TextInput(
#         label="Start time",
#         placeholder="Enter a start time in ",
#         max_length=3,
#         style=discord.TextStyle.short
#     )

#     async def on_submit(self, interaction: discord.Interaction):
#         # if not self.notify_count.value:
#         #     notify_count = bot.default_settings["notify_count"]
#         # else:

#         error_message = f"`{self.notify_count.value}` is not a valid number! Only positive whole numbers are allowed."

# class TimeSelect(discord.ui.Select):
#     def __init__(self):
#         super().__init__(placeholder="Select one or more channels", min_values=1, max_values=25)
#         self.channel_types = [discord.ChannelType.voice]

#     async def callback(self, interaction: discord.Interaction):
#         if len(self.values) <= 0:
#             await interaction.response.send_message(f"You must select at least one channel!", ephemeral=True)
#             return

# endregion

# region Reused errors
def get_error(action: str, error = None):
    if error:
        return f"I could not {action}: {error}"
    return f"I encountered an error while trying to {action}."
# endregion

# region commands
def return_stripped(argument: str):
    return argument.strip().lower()

@bot.hybrid_group()
async def ping(ctx: commands.Context):
    """Add or remove a ping."""
    if ctx.invoked_subcommand is None:
        await ctx.send(f"{ctx.invoked_subcommand} is not a valid subcommand.", reference=ctx.message, ephemeral=True)

# def is_in_guild(interaction: discord.Interaction | commands.Context) -> bool:
#     return interaction.guild is not None

@ping.command()
async def add(ctx: commands.Context):
    """Add a voice channel for you to be notified in dm\'s for."""

    if ctx.guild is None:
        if ctx.invoked_subcommand is not None:
            subcommand = f" {ctx.invoked_subcommand}"
        else:
            subcommand = ""

        await ctx.send(f"`/{ctx.command}{subcommand}` cannot be used in dm's! Please use this command in the text channel of a server.", reference=ctx.message, ephemeral=True)
        return

    embed = discord.Embed(title="Setup new ping(s)", description='Choose from the dropdown to specify **one or more channels** to be notified in dm\'s for.')
    await ctx.send(embed=embed, view=AddPingChannelView(), reference=ctx.message, ephemeral=True)

@ping.command()
async def remove(ctx: commands.Context):
    """Remove a ping that you previously set up."""
    # guild_id = str(ctx.guild.id)
    user_id_str = str(ctx.author.id)
    # Remove the user from the notification set for the guild, if they exist
    # listed_pings = {}
    options: List[dict] = []
    for guild_id_str in pings:
        for channel_id_str in pings[guild_id_str]:
            for count_str in pings[guild_id_str][channel_id_str]:
                if user_id_str in pings[guild_id_str][channel_id_str][count_str]:
                    
                    channel = bot.get_channel(int(channel_id_str))
                    guild = bot.get_guild(int(guild_id_str))

                    options.append({
                        "guild_str": guild_id_str,
                        "guild_name": guild.name,
                        "channel_str": channel_id_str,
                        "channel_name": channel.name,
                        "count_str": count_str
                    })
    
    if len(options) == 0:
        await ctx.send(f'You have not set up any pings to remove.', reference=ctx.message, ephemeral=True)
    else:
        def sort_options(option):
            guild_name: str = option["guild_name"]
            channel_name: str = option["channel_name"]

            count_str = option["count_str"]

            while len(count_str) < 3:
                count_str = f"0{count_str}"

            return f"{guild_name} {channel_name} {count_str}"

        options.sort(key=sort_options)
        # embed = discord.Embed(title="Remove pings", description=f"Choose from the dropdowns below to remove those pings.")
        # view = RemovePingView(options, 0)
        
        await ctx.send(embed=remove_ping_embed(0, get_select_pages(options)), view=RemovePingView(options, 0), reference=ctx.message, ephemeral=True)

@bot.hybrid_command()
@commands.has_permissions(administrator=True)
@app_commands.describe(value="Type 'true' to make responses visible, 'false' to make them invisible, or 'reset' to set to default.")
async def visible(ctx: commands.Context, value: return_stripped):
    """Set whether commands return a response that is visible to other server members."""

    guild_id_str = str(ctx.guild.id)

    if value is None or value == "":
        await ctx.send("`value` must be either `true`, `false`, or `reset`.\n\nType `true` to make responses visible, `false` to make them invisible, or `reset` to set to default.", reference=ctx.message, ephemeral=True)
        return
    elif value == "true" or value == "false":
        if guild_id_str not in server_settings:
            server_settings[guild_id_str] = {}
        server_settings[guild_id_str]["ephemeral"] = value

        save_server_settings()

        if value == "true":
            string = "visible"
        elif value == "false":
            string = "invisible"

        await ctx.send(f"Command responses have been made **{string}** to all server members.\n\nThis will only affect the **final confirmations** of the `/ping add` and `/ping remove` commands.", reference=ctx.message, ephemeral=True)
    elif value == "reset":
        if guild_id_str in server_settings and "ephemeral" in server_settings[guild_id_str]:
            del server_settings[guild_id_str]["ephemeral"]
        
        if len(server_settings[guild_id_str]) == 0:
            del server_settings[guild_id_str]

        save_server_settings()

        await ctx.send(f"The visibility of command responses has been **reset** to the bot's default: `{bot.default_settings['ephemeral']}`", reference=ctx.message, ephemeral=True)


# @bot.hybrid_group()
# async def set(ctx: commands.Context):
#     """Various personal settings."""

#     if ctx.invoked_subcommand is None:
#         await ctx.send(f"{ctx.invoked_subcommand} is not a valid subcommand.", reference=ctx.message, ephemeral=True)


# def return_time(argument: str):
#     try:
#         datetime.datetime.strptime(argument, '%I:%M %p')
#     except:
#         return argument.lower()
    
# def return_weekday(argument: str):



# @bot.hybrid_command()
# async def silenthours(ctx: commands.Context):
#     """Set the times during which you will never be notified."""



# endregion

@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    """
    Event triggered when a user's voice state changes.
    Checks if a user has joined a voice channel and sends a DM to users who opted in for notifications.
    """
    # region edit message
    async def edit_message(channel_id: int, members_message: str, verb: str, guild_id_str: str, channel_id_str: str):
        for user_id_str in bot.notified_channels: #If this user has been notified
            if channel_id in bot.notified_channels[user_id_str]: #If they have been notified for this channel
                for this_count in bot.notified_channels[user_id_str][channel_id]: #For each count they've been notified for
                    message: discord.Message | None = bot.notified_channels[user_id_str][channel_id][this_count] #Get the previously sent notification
                    if message is not None:
                        await message.edit(content=f"{members_message} {verb} currently in https://discord.com/channels/{guild_id_str}/{channel_id_str}")
    # endregion
    # region set member message
    def make_member_list(count: int, member_list: List[discord.Member]):
        if count <= 5:
            final_message = ""
            for x in range(count):
                if count == 1: #If there is only one user
                    final_message += f"<@{member_list[x].id}>"
                elif x == 0 and count == 2: #If there are two users, but we're referencing the first user
                    final_message += f"<@{member_list[x].id}> "
                elif x < count - 1: #If it's not the last user we're referencing
                    final_message += f"<@{member_list[x].id}>, "
                else: #If this is the last user we're referencing
                    final_message += f"and <@{member_list[x].id}>"
        else: #If there are more than five members in the channel
            final_message = f"**{count}** members"
        return final_message
    # endregion
    # region Reset pings
    if before.channel is not None:
        if len(before.channel.members) == 0: #If everyone has left the voice channel
            for user_id_str in bot.notified_channels: #For each person who has been notified
                if before.channel.id in bot.notified_channels[user_id_str]: #If this person has been notified for this channel
                    for this_count in bot.notified_channels[user_id_str][before.channel.id]:
                        message: discord.Message | None = bot.notified_channels[user_id_str][before.channel.id][this_count] #Get previously sent message
                        if message is not None: #If message exists
                            await message.edit(content=message.content.replace("is currently", "was").replace("are currently", "were") + f".\n-# Last member left at <t:{str(datetime.datetime.now().timestamp())[:10]}:t>.")
                    del bot.notified_channels[user_id_str][before.channel.id] #Remove channel from list, because everyone has left.
        else: #Otherwise, just update the message for everyone who was notified
            # region Calculate members list
            before_member_list = before.channel.members
            # region ignore bots
            for before_member_check in before_member_list:
                if before_member_check.bot:
                    before_member_list.remove(before_member_check)
            # endregion
            before_count = len(before_member_list)
            before_channel_id = before.channel.id
            
            if before_count == 1: #If there is one member in the channel
                before_verb = "is"
            else: #If there is more than one member in the channel
                before_verb = "are"
            # endregion
            await edit_message(before_channel_id, make_member_list(before_count, before_member_list), before_verb, str(before.channel.guild.id), str(before_channel_id))

    # endregion
    # region Ping
    if after.channel is not None:
        member_list = after.channel.members
        # region ignore bots
        for member_check in member_list:
            if member_check.bot:
                member_list.remove(member_check)
        # endregion
        count = len(member_list)
        count_str = str(count)
        guild_id_str = str(after.channel.guild.id)
        channel_id = after.channel.id
        channel_id_str = str(channel_id)
        # region Make Message
        members_message = make_member_list(count, member_list)

        if count == 1: #If there is one member in the channel
            verb = "is"
        else: #If there is more than one member in the channel
            verb = "are"
        # endregion
        if guild_id_str in pings and channel_id_str in pings[guild_id_str] and count_str in pings[guild_id_str][channel_id_str]: #If people have signed up to be pinged for this count in this channel and guild
            for pinged_id_str in pings[guild_id_str][channel_id_str][count_str]: #For each user that wants to be pinged for this count
                pinged_user = bot.get_user(int(pinged_id_str))
                if pinged_id_str in bot.notified_channels: #If this user already has been pinged, and that has already been recorded
                    if channel_id in bot.notified_channels[pinged_id_str]: #if they were already pinged for this channel
                        if count in bot.notified_channels[pinged_id_str][channel_id]: #if they were already pinged for this count
                            await edit_message(channel_id, members_message, verb, guild_id_str, channel_id_str)
                            continue
                        elif pinged_user not in member_list: #If they were not yet pinged for this count, and they're also not in the channel
                            for this_count in bot.notified_channels[pinged_id_str][channel_id]:
                                to_delete: discord.Message | None = bot.notified_channels[pinged_id_str][channel_id][this_count]
                                if to_delete is not None:
                                    await to_delete.delete() #Delete the message, then continue to send the next one after this if statement
                                    bot.notified_channels[pinged_id_str][channel_id][this_count] = None
                        else: #If they were not pinged for this count, but they're in the voice channel
                            await edit_message(channel_id, members_message, verb, guild_id_str, channel_id_str)
                else: #If it's not recorded that this user has been pinged
                    bot.notified_channels[pinged_id_str] = {} #Add a dictionary for this user containing channel id's

                if channel_id not in bot.notified_channels[pinged_id_str]:
                    bot.notified_channels[pinged_id_str][channel_id] = {}
                    
                if pinged_user in member_list: #If this user is in the voice channel
                    continue
                bot.notified_channels[pinged_id_str][channel_id][count] = None
                
                try:
                    message = await pinged_user.send(f"{members_message} {verb} currently in https://discord.com/channels/{guild_id_str}/{channel_id_str}")
                except discord.Forbidden as error:
                    print(f"Could not send ping to {pinged_user.name}: {error}")
                
                else:
                    bot.notified_channels[pinged_id_str][channel_id][count] = message
        else:
            await edit_message(channel_id, members_message, verb, guild_id_str, channel_id_str)
            
    # endregion


@bot.command()
@commands.is_owner()
@app_commands.describe(guild="The server ID of the server you want to sync commands to.")
async def sync(ctx: commands.Context, guild: discord.Guild = None):
    """Sync slash commands either globally or for a specific guild."""

    # print("sync triggered")

    if guild:
        synced_commands = await bot.tree.sync(guild=guild)
        command_list = ""
        for command in synced_commands:
            command_list += f"\n- `/{command.name}`"
        await ctx.send(f"Commands synced to the guild: {guild.name}{command_list}\nPlease note it may take up to an hour to propagate globally.", reference=ctx.message, ephemeral=True)
    else:
        try:
            synced_commands = await bot.tree.sync()
        except discord.app_commands.CommandSyncFailure as error:
            print(f"CommandSyncFailure: {error}")
        except discord.HTTPException as error:
            print(f"HTTPException: {error}")
        except discord.Forbidden as error:
            print(f"Forbidden: {error}")
        except discord.app_commands.TranslationError as error:
            print(f"TranslationError: {error}")
        # print("synced commands globally")
        command_list = ""
        for command in synced_commands:
            command_list += f"\n- `/{command.name}`"
        await ctx.send(f"Commands synced globally:{command_list}\nPlease note it may take up to an hour to propagate globally.", reference=ctx.message, ephemeral=True)


# Run the bot with the loaded token
bot.run(bot_token)
