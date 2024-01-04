# AWS Controller Discord Bot
Fork of https://github.com/drpump/AwsEc2DiscordBot 
* Added use case to auto update the DNS record in cloudflare
* Added threading to for real time bot updates

## Tools Used
* Python 3 (v3.8 or higher) and pip3
* Python modules : ```pip3 install -r requirements.txt ```

## AWS setup #No changes 
* for ECS (Docker/Fargate) bots, see http://github.com/drpump/minebot-cdk
* for EC2 bots:
  - create an EC2 instance and configure minecraft to run as a daemon. I used msm (https://msmhq.com)
  - add a `guild` tag to your ec2 instance with your Discord guild ID as the value
  
## Bot Usage | Installation
1. Install and setup the required tools above on your bot server
2. Setup AWS CLI with ``` aws configure ```
3. Go to Discord's developer site and setup a bot [here](https://discordapp.com/developers)
4. Clone this repo into a desired folder
5. Set the discord token environment variable with the name 'AWSDISCORDTOKEN'
6. Start bot for EC2 or ECS:
   * For EC2, run python3 bot.py
   * for ECS, run python3 ecsbot.py
## Run daemon in cloud
Assuming you've already got it running locally using the instructions above ...
1. Create cloud VM using an Ubuntu image and login
2. Install python3 ```sudo apt install python3```
3. Install AWS cli ```sudo pip3 install awscli```. You might need to use ```--target /usr/lib/python3.X``` to ensure it is installed system-wide.
4. Install required libs ```sudo pip3 install -r requirements.txt```. 
5. Create a daemon user with a home dir ```sudo useradd --service -m <<NAME>>```
6. Su to that user ```sudo su - <<NAME>>```
7. Setup AWS using ```aws configure``` (you will need suitable AWS credentials, preferably locked down to limit capabilities), or copy an already configured `.aws` directory for this user (chmod'ed so <<NAME>> owns the dir and files)
8. Copy/download `bot.py` or `ecsbot.py` into the home directory
9. Exit from your `su` session (```^D```)
10. Copy/download `ec2bot.service` or `ecsbot.service`
11. Edit and set the `AWSDISCORDTOKEN` environment variable
12. Copy service file to systemd, e.g. ```sudo cp ec2bot.service /etc/systemd/system/```
13. Create a .env file in the main folder with ``bot.py`` or ``ecsbot.py``
14. Get cloudflare, or DNS of choice API key and requirements for updating the DNS records.
15. Add an A record that points to your ec2 instances public IP ``mc-server.example.com``.
16. Add a CNAME record that points to your A record (should be different names)  ``mc.example.com``
17. Load and enable 

```
  sudo systemctl daemon-reload 
  sudo systemctl enable ec2bot # or ecsbot
  sudo systemctl start ec2bot # or ecsbot
```
18. Use `tail /var/log/syslog` to check output and make sure it is running

TODO:
19. All logs can be stored in an area of your choice by modifying the .env var mc_bot.log
