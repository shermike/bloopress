#!/usr/bin/python3.4
# -*- coding: utf-8 -*-
import telebot
import cherrypy
import config
import sqlite3
import datetime
import tempfile
import os

import matplotlib
# Force matplotlib to not use any Xwindows backend. 
matplotlib.use('Agg')
import matplotlib.pyplot as plt

WEBHOOK_HOST = '188.120.241.60'
WEBHOOK_PORT = 443
WEBHOOK_LISTEN = '188.120.241.60'

WEBHOOK_SSL_CERT = 'cert/webhook_cert.pem'
WEBHOOK_SSL_PRIV = 'cert/webhook_pkey.pem'

WEBHOOK_URL_BASE = "https://%s:%s" % (WEBHOOK_HOST, WEBHOOK_PORT)
WEBHOOK_URL_PATH = "/%s/" % (config.token)


bot = telebot.TeleBot(config.token)

class WebhookServer(object):
    @cherrypy.expose
    def index(self):
        if 'content-length' in cherrypy.request.headers and \
                        'content-type' in cherrypy.request.headers and \
                        cherrypy.request.headers['content-type'] == 'application/json':
            length = int(cherrypy.request.headers['content-length'])
            json_string = cherrypy.request.body.read(length).decode("utf-8")
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
            return ''
        else:
            raise cherrypy.HTTPError(403)

@bot.message_handler(commands=['add'])
def enter_pressure(message):
    db = sqlite3.connect('data.db')
    cursor = db.cursor()

    parts = message.text.split()[1:4]
    try:
        assert len(parts) >= 3
        map(int, parts)
    except:
        bot.send_message(message.chat.id, "Wrong message! It must be like '/add 120 80 70'")
        return
    dt = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    values = '"{}", {}'.format(dt, ', '.join(parts))
    print values
    cursor.execute('INSERT INTO pressure (date, systolic, diastolic, pulse) VALUES ({})'.format(values))
    bot.send_message(message.chat.id, values)
    
    db.commit()
    db.close()


@bot.message_handler(commands=['last'])
def print_last(message):
    db = sqlite3.connect('data.db')
    cursor = db.cursor()
    
    parts = message.text.split()
    graph = len(parts) > 1 and parts[1] == 'graph'
    
    try:    n = int(parts[2 if graph else 1])
    except: n = 5
    try:
        cursor.execute('SELECT * FROM pressure WHERE id > (SELECT MAX(id) - {} FROM pressure)'.format(n))
        data = cursor.fetchall()
        if graph:
            vals = []
            for d in data:
                vals.append(map(int, d[2:4]))
            print vals
            plt.plot(vals)
            plt.grid(True)
            fname = '/tmp/tmp.png'
            plt.savefig(fname)
            if not os.path.exists(fname):
                print 'Failed saving png to file!'
            else:
                print 'Good!'
            bot.send_photo(message.chat.id, open(fname, 'rb'))
        else:
            fmt = '{:<20}{} ({})\n'
            answer = '' #fmt.format('Date', 'Press', 'Pulse')
        for d in data:
            answer += fmt.format('[%s]'%d[1][:-3], '%d/%d'%(d[2], d[3]), d[4])
        bot.send_message(message.chat.id, answer)
    except Exception as e:
        print e

    cursor.execute('SELECT * FROM pressure)'.format(n))
    data = cursor.fetchall()
    
    db.close()


while True:
    try:
        print "Run bot..."


        bot.remove_webhook()

        bot.set_webhook(url=WEBHOOK_URL_BASE + WEBHOOK_URL_PATH,
                certificate=open(WEBHOOK_SSL_CERT, 'r'))
				
        cherrypy.config.update({
            'server.socket_host': WEBHOOK_LISTEN,
            'server.socket_port': WEBHOOK_PORT,
            'server.ssl_module': 'builtin',
            'server.ssl_certificate': WEBHOOK_SSL_CERT,
            'server.ssl_private_key': WEBHOOK_SSL_PRIV})

        cherrypy.quickstart(WebhookServer(), WEBHOOK_URL_PATH, {'/': {}})
    except Exception as e:
        print e
        break
