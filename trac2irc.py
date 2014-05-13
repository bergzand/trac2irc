#!/usr/bin/env python

# Send Trac ticket updates to irc
#
#
# Setup Steps:
# update your trac.ini
# ####################
# [notification]
# smtp_always_cc = trac@yourdomain
# ####################
# invoke with a .forward file of your trac user - content "|/usr/local/bin/trac2irker.py"

import sys
import json
import email
import base64
import socket, ssl
import argparse


DESCRIPTION="Utility to parse trac report mails from stdin and send them to an Irker daemon or a ZNC daemon"
#Some defaults
IRKER_HOST="localhost"
IRKER_PORT=6659

ZNC_HOST="localhost"
ZNC_PORT=7000
ZNC_USER="znc"
ZNC_NICK="znc"

###############################################################################

def send2irker(irkercon, message):
    data = {"to": irkercon['uri'],
        "privmsg": "{}".format(message),
        }
    s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    try:
        s.connect((irkercon['host'],irkercon['port']))
        s.sendall(json.dumps(data))
    except:    
        s.close()
  

def send2znc(znccon,message):
    s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    ssl_sock = ssl.wrap_socket(s)
    try:
        ssl_sock.connect((znccon['host'],znccon['port']))
        ssl_sock.sendall("PASS {0}:{1}\r\n".format(znccon['user'],znccon['pass']))
        ssl_sock.sendall("USER {0}\r\n".format(znccon['user']))
        ssl_sock.sendall("NICK {0}\r\n".format(znccon['nick']))
        ssl_sock.sendall("PRIVMSG {0} :{1}\r\n".format(znccon['chan'], message))
        print "send to irc: {0}".format(message)
    except:
        print "something went wrong sending to irc"
    finally:
        ssl_sock.close()
pass


def parsemail(payload):
    #set defaults
    omitheader = 3
    ticketsummary = ''
    ticketstatus = 'created'
    ticketurl=''
    #parse per line
    for line in payload.split("\n"):
        #filter out header + lines (free to extend)
        #first part (summary)
        if omitheader == 3:
            if "-----+-----" in line:
                omitheader -= 1
    	        continue
            ticketsummary=(line[:75] + '..') if len(line) > 77 else line
            continue
        #second part (ticket status)
        if omitheader == 2:
            if "-----+-----" in line:
                omitheader -= 1
                continue
            else:
                continue
        #update part
        
        if omitheader == 1:
            if ("--") in line:
                omitheader -= 1
                continue
            elif "* status:" in line:
                ticketstatus = line.split()[-1]
                continue
            elif ("Comment (" in line or "Changes (" in line)and ticketstatus == 'created':
                ticketstatus = 'updated'
                continue
        #url part
        if omitheader == 0:
            if "Ticket URL:" in line:
                ticketurl = '{}'.format(line.split()[-1])
            else:
                continue
    status = {'summary':ticketsummary ,'status':ticketstatus, 'url':ticketurl}
    return status
def formatmessage():
    pass

def argParse():
    parser = argparse.ArgumentParser(description=DESCRIPTION, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-U','--irkeruri',  help='Connection string for the irker daemon')
    parser.add_argument('-i','--irkerhost', default=IRKER_HOST, help='host where the irker daemon is listening')
    parser.add_argument('-p','--irkerport', default=IRKER_PORT, help='port on which the irkerdaemon is listening')
    parser.add_argument('-c','--zncchannel', help='channel to send message to on the znc daemon')
    parser.add_argument('-z','--znchost', default=ZNC_HOST, help='host where znc is listening')
    parser.add_argument('-P','--zncport', default=ZNC_PORT, help='port on which znc is listening')
    parser.add_argument('-u','--zncuser', default=ZNC_USER, help='username for the znc user')
    parser.add_argument('-n','--zncnick', default=ZNC_NICK, help='nickname for the znc user')
    parser.add_argument('-w','--zncpass', help='password for the znc user')
    return parser.parse_args()

exitcode=0
args = vars(argParse())
if args['irkeruri']:
    irkercon = {'uri':args['irkeruri'], 'host':args['irkerhost'], 'port' : args['irkerport']}
else:
    irkercon = None
if args['zncchannel']:
    znccon = {'chan':args['zncchannel'], 'host':args['znchost'], 'port':args['zncport'], 'user':args['zncuser'], 'pass':args['zncpass'], 'nick':args['zncnick']}

else:
    znccon = None

try:
    content = email.message_from_string(sys.stdin.read())
except:
    print "something went wrong parsing the email"
    exitcode = 1
    exit(exitcode)

payload = content.get_payload().encode('utf-8')
try:
    payload = base64.decodestring(payload).encode('utf-8')
except:
    pass

#parse the status from email
parsed = parsemail(payload)

#format message string
message = '[\x0305TRAC\x0F] {0} {1}: {2}'.format(parsed['summary'], parsed['status'], parsed['url'])

#print(json.dumps(data))
if znccon:
    send2znc(znccon, message)
if irkercon:
    send2irker(irkercon,message)

