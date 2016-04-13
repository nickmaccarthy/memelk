# MEMELK - Memcache monitoring for ELK

# What is it?
In my environment we have a few different memcache clusters that we like to monitor.  While I found other tools out there like phpmemcacheadming, I needed someting that was easy to setup and easily scalable to monitor our memcache clusters.  By monitor I'm refering to output and calculations arond the ```stats``` command in memcache.

This script will will run forever and is ment to be controlled with something like supervisord.  Below is a sample supervisor config

# Requirements
* python 2.7
* virtualenv
* pip


# Install
1. git clone this repo
2. ```cd <cloned_dir> && virtualenv env && source env/bin/activate ```
3. ```pip install -r requirements.txt``` 
4. Copy ```config.yml.example``` to ```config.yml``` and fill in your relevent info
5. Run it with something like supervisor
6. Install the optional kibana4 dashboard ( json included ) into your kibana 4 instance

# Sample kibana dashboard
![alt text](redis-kibana.png "Example Redis Dashboard")

# Sample supervisord entry

```
[program:memelk]
command=/opt/monitor/memcache-stats/env/bin/python /opt/monitor/memcache-stats/memelk.py
directory=/opt/monitor/memcache-stats
autostart=true
autorestart=true
logfile=/var/log/supervisor/memcache-stats.log
```
