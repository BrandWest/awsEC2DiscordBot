import discord
import os
import boto3
import socket
import traceback
import logging
import requests
import functools

from dotenv import load_dotenv
from time import sleep


#Added logging TODO: add save to file
logging.basicConfig(
    format='%(asctime)s\t %(levelname)-8s\t %(filename)s\t%(lineno)d\t %(message)s',
    datefmt='%Y-%m-%d:%H:%M:%S',
    level=logging.INFO
)
log = logging.getLogger(__name__)

#load the .env holding secrets
load_dotenv()

#Discord requirements
intents = discord.Intents.default()
client = discord.Client(intents=intents)

#EC2 service
ec2 = boto3.resource('ec2')

#State user info
@client.event
async def on_ready():
    log.info(f"Logged in as: {client.user.name} user id: {client.user.id}")

#Get message and act on what is requested
@client.event
async def on_message(message):
    guild_id = [str(message.channel.guild.id)]
    memberIDs = (member.id for member in message.mentions)
    #Get the tag "Guild" 
    instances = list(ec2.instances.filter(Filters=[{'Name':'tag:guild', 'Values': guild_id}]))
    try:
        log.info(f"Instance: {str(instances[0])}. Number of matches: {str(len(instances))}")
    except Exception as error:
        log.error(f"Failed to act on instance. Error {error}")
    # assume that there will never be more than one matching instance
    # Check the user is in the server members list.
    if client.user.id in memberIDs and len(instances) > 0:
        log.info(f"Username: {client.user.name} performed {message.content}")
        #Stop the EC2 Instance
        if 'stop' in message.content:
            if getInstanceState(instances[0]) == "stopped":
                await message.channel.send('AWS Instance already stopped.')                
            elif getInstanceState(instances[0]) != "stopped":
                #Perform threading to wait for this to return completed.
                response = await unblock(turnOffInstance, instances[0], guild_id)
                if response: #If successful
                    await message.channel.send('AWS Instance stopped.')              
            else: #failed to stop
                log.error(f"Failed to stop instance")                
                await message.channel.send('Error stopping AWS Instance')
        # attempt to start the EC2 instance
        elif 'start' in message.content:
            #Check for ready state
            if getInstanceState(instances[0]) == "ready":
                await message.channel.send('AWS Instance already running.')
            #Check for not ready
            elif getInstanceState(instances[0]) != "ready":
                #Perform threading to wait for this to return completed.
                response = await unblock(turnOnInstance, instances[0], guild_id)
                if response: 
                    await message.channel.send('AWS Instance state is: ' + getInstanceState(instances[0]))
            else:
                log.error(f"Failed to start instance")
                await message.channel.send('Error starting AWS Instance')
        #Get the state of the machine
        elif 'state' in message.content:
            await message.channel.send('AWS Instance state is: ' + getInstanceState(instances[0]))
        #Reboot if you have proper permissions TODO: Add threading
        elif 'reboot' in message.content:
            if rebootInstance(instances[0]):
                await message.channel.send('AWS Instance started.')
            else:
                log.error(f"Failed to reboot instance")                
                await message.channel.send('Error rebooting AWS Instance')
        #Help message
        elif 'info' in message.content:
            await message.channel.send('Server start/stop bot. Commands are `start`, `stop`, `state`, `reboot`, `update_record`, and `info`')
        #Update CF DNS record with new IP Address
        elif 'update_record' in message.content:
            log.info(f"Instance state: {instances[0].state['Name']}, getInstanceState: {getInstanceState(instances[0])}")
            if instances[0].state["Name"] == "running":
                if updateDNSRecord(instances[0]): #Returns true
                    await message.channel.send(f"Updated DNS record successfully.")
                else: #Fails to update
                    await message.channel.send(f"DNS Record not updated.")                
            else: #The server isn't running
                await message.channel.send(f"Server not started. Instance state: {instances[0].state['Name']}")
        else: #Unknown command
            await message.channel.send('Server start/stop bot. Commands are `start`, `stop`, `state`, `reboot`, `update_record`, and `info`')
    else: #Not a recognized guild
        log.error(f"Attempted to perform action by unrecognized guild {str(message.channel.guild.id)}")

#Perform the dns updated
def updateDNSRecord(instance):
    public_ip = getPublicIP(instance)
    # Configure cloudflare A record
    zone_identifier = os.getenv("ZONE_IDENTIFIER")
    identifier = os.getenv("IDENTIFIER")
    auth_key = os.getenv("AUTH_KEY")
    auth_email = os.getenv("AUTH_EMAIL")
    endpoint = os.getenv("ENDPOINT")

    payload = {
            "content": f"{public_ip}",
            "name": f"{endpoint}",
            "proxied": False,
            "type": "A",
            "comment": f"Updated record for {endpoint}",
            "ttl": 3600
    }
    headers = {
            "Content-Type": "application/json",
            "Authorization" : f"Bearer {auth_key}"
    }
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_identifier}/dns_records/{identifier}"
    
    response = requests.request("PUT", url, json=payload, headers=headers)
    response_data = response.json()
    log.info(f"Response: {response_data['success']}")
    if response_data['success']: #Return true if successful
        return True
    else: #Log if not, return false
        log.error(f"Request error: {response_data['errors']}")
        return False


def getPublicIP(instance):
    return instance.public_ip_address

#Unblocking function for threading
async def unblock(blockingFunctions, *args):
    func = functools.partial(blockingFunctions, *args)
    return await client.loop.run_in_executor(None, func)
    

#Blocking function 1
def turnOffInstance(instance, guild_id):
    try:
        #Triggers the stop
        instance.stop()
        log.info(f"Checking state: {instance.state['Name']}")
        #While loop to identify if the instance state has changed to stopped.
        while instance.state['Name'].lower() != "stopped":
            log.info(f"Checking state: {instance.state['Name']}")
            sleep(10) #Not to spam
            instances = list(ec2.instances.filter(Filters=[{'Name':'tag:guild', 'Values': guild_id}])) #To update for thread
            instance = instances[0]
        log.info(f"Machine stopped.")
        return True
    except: 
        log.error(traceback.format_exc())
        return False

#Blocking function 2
def turnOnInstance(instance, guild_id):
    try:
        instance.start() #Attempt to start the machine
        log.info(f"Checking state: {instance.state['Name']}")
        while instance.state['Name'].lower() != "running": #As long as its not running
            log.info(f"Checking state: {instance.state['Name']}")
            sleep(10) #not to spam
            instances = list(ec2.instances.filter(Filters=[{'Name':'tag:guild', 'Values': guild_id}])) #Performs the update of the instance for the thread
            instance = instances[0]
        sleep(5)# Slight pause to update the dns record.
        updateDNSRecord(instance)
        return True
    except:
        log.error(traceback.format_exc())
        return False


def getInstanceState(instance):
    aws_state = instance.state
    if (aws_state['Name'] == 'running'):
        return getPortState(instance.public_ip_address, 25565)
    else:
        return aws_state['Name']

def getPortState(ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3.0)
    ready = sock.connect_ex((ip, port))
    if ready == 0:
        return 'ready at ' + ip 
    else:
        return 'game startup in progress, please wait'

def rebootInstance(instance):
    try:
        instance.reboot()
        while instance.state["Name"] == "initalizing":
            sleep(10)
        updateDNSRecord(instance)
        return True
    except:
        log.error(traceback.format_exc())
        return False

client.run(os.getenv('AWSDISCORDTOKEN'))
