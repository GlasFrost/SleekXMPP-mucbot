#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SleekXMPP: The Sleek XMPP Library
Copyright (C) 2010 Nathanael C. Fritz
This file is part of SleekXMPP.
See the file LICENSE for copying permission.
"""
import sys
import logging
import getpass
from optparse import OptionParser
import sleekxmpp
import random, urllib2, json
# Python versions before 3.0 do not use UTF-8 encoding
# by default. To ensure that Unicode is handled properly
# throughout SleekXMPP, we will set the default encoding
# ourselves to UTF-8.
if sys.version_info < (3, 0):
	from sleekxmpp.util.misc_ops import setdefaultencoding
	setdefaultencoding('utf8')
else:
	raw_input = input
class MUCBot(sleekxmpp.ClientXMPP):
	"""
	A simple SleekXMPP bot that will greets those
	who enter the room, and acknowledge any messages
	that mentions the bot's nickname.
	"""
	def __init__(self, jid, password, room, nick):
		sleekxmpp.ClientXMPP.__init__(self, jid, password)
		self.room = room
		self.nick = nick
		# The session_start event will be triggered when
		# the bot establishes its connection with the server
		# and the XML streams are ready for use. We want to
		# listen for this event so that we we can initialize
		# our roster.
		self.add_event_handler("session_start", self.start)
		# The groupchat_message event is triggered whenever a message
		# stanza is received from any chat room. If you also also
		# register a handler for the 'message' event, MUC messages
		# will be processed by both handlers.
		self.add_event_handler("groupchat_message", self.muc_message)
		# The groupchat_presence event is triggered whenever a
		# presence stanza is received from any chat room, including
		# any presences you send yourself. To limit event handling
		# to a single room, use the events muc::room@server::presence,
		# muc::room@server::got_online, or muc::room@server::got_offline.
		self.add_event_handler("muc::%s::got_online" % self.room,
			self.muc_online)
	
	def start(self, event):
		"""
		Process the session_start event.
		Typical actions for the session_start event are
		requesting the roster and broadcasting an initial
		presence stanza.
		Arguments:
		event -- An empty dictionary. The session_start
		event does not provide any additional
		data.
		"""
		self.get_roster()
		self.send_presence()
		self.plugin['xep_0045'].joinMUC(self.room,
			self.nick,
			# If a room password is needed, use:
			# password=the_room_password,
			wait=True)
	
	def muc_message(self, msg):
		"""
		Process incoming message stanzas from any chat room. Be aware
		that if you also have any handlers for the 'message' event,
		message stanzas may be processed by both handlers, so check
		the 'type' attribute when using a 'message' event handler.
		Whenever the bot's nickname is mentioned, respond to
		the message.
		IMPORTANT: Always check that a message is not from yourself,
		otherwise you will create an infinite loop responding
		to your own messages.
		This handler will reply to messages that mention
		the bot's nickname.
		Arguments:
		msg -- The received message stanza. See the documentation
		for stanza objects and the Message stanza to see
		how it may be used.
		"""
		if msg['mucnick'] != self.nick and msg['body'].startswith('#'):
			try:
				issue_id = int(msg['body'][1:])
			except Exception:
				self.send_message(mto=msg['from'].bare,
					mbody="%s, \"%s\" doesn't look like a number. I couldn't lookup that Github issue for you." % (msg['mucnick'], msg['body'][1:]),
					mtype='groupchat')
			else	:
				# Lookup github issue
				f = open('../github-token-mucbot.txt','r')
				token = f.read()
				f.close()
				try:
					req = urllib2.Request('https://api.github.com/repos/GlasFrost/SleekXMPP-mucbot/issues/'+unicode(issue_id), headers={'Authorization':'token '+token})
					page = urllib2.urlopen(req)
				except Exception as e:
					self.send_message(mto=msg['from'].bare,
						mbody="%s, the issue lookup failed. Error message: %s" % (msg['mucnick'], e),
						mtype='groupchat')
				else:
					response = json.loads(page.read())
					#(name): Issue #(id): (url)
					#((state)) (title)
					#(body)
					output = "%s: Issue #%s: %s\n(%s) %s\n%s" % (msg['mucnick'], unicode(response['number']), response['html_url'], response['state'], response['title'], response['body'])
					self.send_message(mto=msg['from'].bare,
						mbody=output,
						mtype='groupchat')
	
	def muc_online(self, presence):
		"""
		Process a presence stanza from a chat room. In this case,
		presences from users that have just come online are
		handled by sending a welcome message that includes
		the user's nickname and role in the room.
		Arguments:
		presence -- The received presence stanza. See the
		documentation for the Presence stanza
		to see how else it may be used.
		"""
		#greetings = (
			#('Hello,', '!'),
			#('Welcome,', '!'),
			#('Hi,', '!'),
			#('How are you doing,', '?'),
			#('What\'s up,', '?')
			#)
		#greeting = random.choice(greetings)
		#if presence['muc']['nick'] != self.nick:
			#self.send_message(mto=presence['from'].bare,
				#mbody="%s %s %s %s" % (greeting[0], presence['muc']['role'],
				#presence['muc']['nick'], greeting[1]),
				#mtype='groupchat')

if __name__ == '__main__':
	# Setup the command line arguments.
	optp = OptionParser()
	# Output verbosity options.
	optp.add_option('-q', '--quiet', help='set logging to ERROR',
		action='store_const', dest='loglevel',
		const=logging.ERROR, default=logging.INFO)
	optp.add_option('-d', '--debug', help='set logging to DEBUG',
		action='store_const', dest='loglevel',
		const=logging.DEBUG, default=logging.INFO)
	optp.add_option('-v', '--verbose', help='set logging to COMM',
		action='store_const', dest='loglevel',
		const=5, default=logging.INFO)
	# JID and password options.
	optp.add_option("-j", "--jid", dest="jid",
		help="JID to use")
	optp.add_option("-p", "--password", dest="password",
		help="password to use")
	optp.add_option("-r", "--room", dest="room",
		help="MUC room to join")
	optp.add_option("-n", "--nick", dest="nick",
		help="MUC nickname")
	opts, args = optp.parse_args()
	# Setup logging.
	logging.basicConfig(level=opts.loglevel,
		format='%(levelname)-8s %(message)s')
	if opts.jid is None:
		opts.jid = raw_input("Username: ")
	if opts.password is None:
		opts.password = getpass.getpass("Password: ")
	if opts.room is None:
		opts.room = raw_input("MUC room: ")
	if opts.nick is None:
		opts.nick = raw_input("MUC nickname: ")
	# Setup the MUCBot and register plugins. Note that while plugins may
	# have interdependencies, the order in which you register them does
	# not matter.
	xmpp = MUCBot(opts.jid, opts.password, opts.room, opts.nick)
	xmpp.register_plugin('xep_0030') # Service Discovery
	xmpp.register_plugin('xep_0045') # Multi-User Chat
	xmpp.register_plugin('xep_0199') # XMPP Ping
	# Connect to the XMPP server and start processing XMPP stanzas.
	if xmpp.connect():
		# If you do not have the dnspython library installed, you will need
		# to manually specify the name of the server if it does not match
		# the one in the JID. For example, to use Google Talk you would
		# need to use:
		#
		# if xmpp.connect(('talk.google.com', 5222)):
		# ...
		xmpp.process(block=True)
		print("Done")
	else:
		print("Unable to connect.")
