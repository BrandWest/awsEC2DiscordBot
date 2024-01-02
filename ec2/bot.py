import discord
import asyncio
import os
import boto3
import socket
import traceback
import logging

logging.basicConfig(
    format='%(asctime)s\t %(levelname)-8s\t %(filename)s\t%(lineno)d\t %(message)s',
    datefmt='%Y-%m-%d:%H:%M:%S',
    level=logging.INFO
)
log =logging.getLogger(__name__)

intents = discord.Intents.default()
client = discord.Client(intents=intents)

ec2 = boto3.resource('ec2')

@client.event
async def on_ready():
    log.info(f"Logged in as: {client.user.name} user id: {client.user.id}")

@client.event
async def on_message(message):
    memberIDs = (member.id for member in message.mentions)
    instances = list(ec2.instances.filter(Filters=[{'Name':'tag:guild', 'Values': [str(message.channel.guild.id)]}]))
    try:
        log.info(f"Instance: {str(instances[0])}. Number of matches: {str(len(instances))}")
    except Exception as error:
        log.error(f"Failed to act on instance. Error {error}")
    # assume that there will never be more than one matching instance
    if client.user.id in memberIDs and len(instances) > 0:
        
        log.info(f"Username: {client.user.name} performed {message.content}")
        if 'stop' in message.content:
            if getInstanceState(instances[0]) == "stopped":
                await message.channel.send('AWS Instance already stopped.')                
            elif getInstanceState(instances[0]) != "stopped":
                if turnOffInstance(instances[0]):
                    await message.channel.send('AWS Instance stopping')
                else:
                    log.error(f"Failed to stop instance")
                    await message.channel.send('Error stopping AWS Instance')                
            else:
                log.error(f"Failed to stop instance")                
                await message.channel.send('Error stopping AWS Instance')
        elif 'start' in message.content:
            if getInstanceState(instances[0]) == "running":
                await message.channel.send('AWS Instance already running.')                  
            elif getInstanceState(instances[0]) != "running":
                if turnOnInstance(instances[0]):
                    await message.channel.send('AWS Instance starting')
                else:
                    log.error(f"Failed to start instance")
                    await message.channel.send('Error starting AWS Instance')
            else:
                log.error(f"Failed to start instance")
                await message.channel.send('Error starting AWS Instance')                    
        elif 'state' in message.content:
            await message.channel.send('AWS Instance state is: ' + getInstanceState(instances[0]))
        elif 'reboot' in message.content:
            if rebootInstance(instances[0]):
                await message.channel.send('AWS Instance rebooting')
            else:
                log.error(f"Failed to reboot instance")                
                await message.channel.send('Error rebooting AWS Instance')
        elif 'info' in message.content:
            await message.channel.send('Server start/stop bot. Commands are `start`, `stop`, `state`, `reboot` and `info`')
        else: 
            await message.channel.send('Server start/stop bot. Commands are `start`, `stop`, `state`, `reboot` and `info`')            
    else:
        log.error(f"Attempted to perform action by unrecognized guild {str(message.channel.guild.id)}")

def turnOffInstance(instance):
    try:
        instance.stop()
        return True
    except: 
        log.error(traceback.format_exc())
        return False

def turnOnInstance(instance):
    try:
        instance.start()
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
        return True
    except:
        log.error(traceback.format_exc())
        return False

client.run(os.environ['AWSDISCORDTOKEN'])
