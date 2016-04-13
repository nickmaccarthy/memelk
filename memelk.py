import re
import telnetlib
import time
import pprint
from collections import defaultdict
from elasticsearch import Elasticsearch
import arrow
import datetime
import Queue
from multiprocessing.pool import ThreadPool
import math
import sys
import os
import yaml
from autocast import autocast

pp = pprint.PrettyPrinter(indent=4)

SHOME = os.path.abspath(os.path.join(os.path.dirname(__file__)))

class MemcachedStats:
    ''' this class was borrowed from https://github.com/dlrust/python-memcached-stats, thank you for the fine work! '''
    _client = None
    _key_regex = re.compile(ur'ITEM (.*) \[(.*); (.*)\]')
    _slab_regex = re.compile(ur'STAT items:(.*):number')
    _stat_regex = re.compile(ur"STAT (.*) (.*)\r")

    def __init__(self, host='localhost', port='11211'):
        self._host = host
        self._port = port

    @property
    def client(self):
        if self._client is None:
            self._client = telnetlib.Telnet(self._host, self._port)
        return self._client

    def command(self, cmd):
        ' Write a command to telnet and return the response '
        self.client.write("%s\n" % cmd)
        return self.client.read_until('END')

    def key_details(self, sort=True, limit=100):
        ''' Return a list of tuples containing keys and details '''
        cmd = 'stats cachedump %s %s'
        keys = [key for id in self.slab_ids()
            for key in self._key_regex.findall(self.command(cmd % (id, limit)))]
        if sort:
            return sorted(keys)
        else:
            return keys

    def keys(self, sort=True, limit=100):
        ''' Return a list of keys in use '''
        return [key[0] for key in self.key_details(sort=sort, limit=limit)]

    def slab_ids(self):
        ''' Return a list of slab ids in use '''
        return self._slab_regex.findall(self.command('stats items'))

    def stats(self):
        ''' Return a dict containing memcached stats '''
        return dict(self._stat_regex.findall(self.command('stats')))

@autocast
def autocastit(e):
    return e

def load_conf():
    import yaml
    with open('{}/config.yml'.format(SHOME), 'r') as f:
        doc = yaml.load(f)
    return doc

conf = load_conf()
poll_interval = conf['script_args'].get('poll_interval', 1)

es = Elasticsearch(conf['elasticsearch']['hosts'], **conf['elasticsearch']['args'])


def indexit(d):
    def get_index():
        now = arrow.utcnow().format('YYYY.MM.DD')
        return 'memcache-stats-{}'.format(now)        
    es = Elasticsearch(conf['elasticsearch']['hosts'], **conf['elasticsearch']['args'])   
    return es.index(index=get_index(), doc_type='memcache-stats', body=d)


def ddiff(d1,d2):
    diff_items = [ 
        'auth_cmds', 
        'auth_errors', 
        'bytes_read', 
        'bytes_written', 
        'bytes', 
        'cas_badval', 
        'cas_hits', 
        'cas_misses', 
        'cmd_get', 
        'cmd_set', 
        'decr_hits', 
        'decr_misses', 
        'delete_hits', 
        'delete_misses', 
        'evictions',
        'get_hits', 
        'get_misses', 
        'incr_hits', 
        'incr_misses', 
        'total_connections', 
        'total_items' 
    ]
    d = {}
    d['metrics'] = {} 
    d['metrics']['per_second'] = {}
    for item in diff_items:
        d['metrics']['per_second'][item] = int(d2[item]) - int(d1[item])

    #d['metrics']['get_hit_percentage'] = float(int(d2['get_hits']) / int(d2['total_items']) * 100)
    return d

def cast_stats(stats):
    d = {}
    for k,v in stats.iteritems():
        d[k] = autocastit(v)
    return d

def worker(host):
    (hostname,args), = host.items()
    m = MemcachedStats(hostname, args.get('port', 11211))
    d1 = m.stats()
    time.sleep(1)
    d2 = m.stats()
    diffed = ddiff(d1,d2)
    diffed['stats'] = cast_stats(d2)
    diffed['host'] = hostname
    diffed['@timestamp'] = datetime.datetime.utcnow()
    #pp.pprint(diffed)
    print indexit(diffed)

def main():
    conf = load_conf()
    hosts = conf['hosts']
    pool = ThreadPool(processes=5)
    pool.map(worker, hosts)
    pool.close()
    pool.join()



if __name__ == '__main__':
    while True:
        main()
        time.sleep(poll_interval)
