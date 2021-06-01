# (C) 2014 by Dominik Jain (djain@gmx.net)

import sys
import pickle
import wx
import time as t
import traceback
from whiteboard import Whiteboard
import objects
import numpy
import time
import logging
from net import *

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

#白板程序 继承whiteboard
class DispatchingWhiteboard(Whiteboard):
	def __init__(self, title, isServer, **kwargs):
		self.isServer = isServer		#判断
		self.lastPing = t.time()		#ping值
		self.lastCursorMoveTime = t.time()	#move事件？
		self.userName = "user " + str(t.time())
		self.remoteUserCursorUpdateInterval = 0.1  #光标更新间隙
		Whiteboard.__init__(self, title, **kwargs)		#白板
		self.Centre()					#
		self.connId2UserName = {}		#Client连接ID

	def onObjectCreationCompleted(self, object):			#添加元素
		self.dispatch(evt="addObject", args=(object.serialize(),))

	def onObjectsDeleted(self, *ids):						#删除元素
		self.dispatch(evt="deleteObjects", args=ids)

	def onObjectsMoved(self, offset, *ids):					#移动元素
		self.dispatch(evt="moveObjects", args=[offset] + list(ids))

	def onObjectUpdated(self, objectId, operation, args):	#更新元素
		self.dispatch(evt="updateObject", args=(objectId, operation, args))

	def onCursorMoved(self, pos):							#光标移动
		now = t.time()
		if now - self.lastCursorMoveTime > self.remoteUserCursorUpdateInterval:
			#for i in range(1000):
			self.dispatch(evt="moveUserCursor", args=(self.userName, pos,))
			self.lastCursorMoveTime = now

	def moveUserCursor(self, userName, pos):				#移动光标
		sprite = self.viewer.userCursors.get(userName)
		if sprite is None: return
		sprite.animateMovement(pos, self.remoteUserCursorUpdateInterval)
		#sprite.pos = pos

	def _deserialize(self, s):
		if not type(s) == bytes:
			return s
		return objects.deserialize(s, self.viewer)

	def addObject(self, object):	#显示白板添加元素
		super(DispatchingWhiteboard, self).addObject(self._deserialize(object))

	def setObjects(self, objects, dispatch=True):	#
		log.debug("setObjects with %d objects", len(objects))
		objects = map(lambda o: self._deserialize(o), objects)
		super(DispatchingWhiteboard, self).setObjects(objects)
		if dispatch:
			self.dispatchSetObjects(self.dispatcher)

	def dispatchSetObjects(self, dispatcher):
		dispatcher.dispatch(dict(evt="setObjects", args=([o.serialize() for o in self.getObjects()], False)))

	def updateObject(self, objectId, operation, args):
		obj = self.viewer.objectsById.get(objectId)
		if obj is None: return
		eval("obj.%s(*args)" % operation)

	def dispatch(self, exclude=None, **d):
		self.dispatcher.dispatch(d, exclude=exclude)

	#网络事件
	def handleNetworkEvent(self, d):
		exec("self.%s(*d['args'])" % d["evt"])

	def OnTimer(self, evt):
		# Player.OnTimer(self, evt)
		# # perform periodic ping from client to server
		# if not self.isServer:
		# 	if t.time() - self.lastPing > 1:
		# 		self.lastPing = t.time()
		# 		self.dispatch(ping = True)
		None
	# server delegate methods

	def handle_ServerLaunched(self):
		self.Show()

	def handle_ClientConnected(self, conn):
 		conn.dispatch(dict(evt="addUser", args=(self.userName,)))
 		self.dispatchSetObjects(conn)

	def handle_ClientConnectionLost(self, conn):
		log.info("client connection lost: %s", conn)
		userName = self.connId2UserName.get(id(conn))
		if userName is not None:
			log.info("connection of user '%s' closed", userName)
			self.deleteUser(userName)
		else:
			log.warning("connection closed, unknown user name")

	def handle_AllClientConnectionsLost(self):
		self.errorDialog("All client connections have been closed.")

	# client delegate methods

	def handle_ConnectedToServer(self):
		self.Show()
		self.dispatch(evt="addUser", args=(self.userName,))

	def handle_ConnectionToServerLost(self):
		self.deleteAllUsers()
		if self.questionDialog("No connection. Reconnect?\nClick 'No' to quit.", "Reconnect?"):
			self.dispatcher.reconnect()
		else:
			self.Close()

	# client/server delegate methods
	#拿包
	def handle_PacketReceived(self, data, conn):
		d = pickle.loads(data)
		if type(d) == dict and "ping" in d: # ignore pings
			return
		if type(d) == dict and "evt" in d:
			if d["evt"] == "addUser":
				log.info("addUser from %s with name '%s'", conn, d["args"][0])
				self.connId2UserName[id(conn)] = d["args"][0]
			# forward event to other clients
			if self.isServer:
				self.dispatch(exclude=conn, **d)
			# handle in own player
			self.handleNetworkEvent(d)

	def setDispatcher(self, dispatcher):
		self.dispatcher = dispatcher


#主程序开启
if __name__=='__main__':
	app = wx.App(False)

	argv = sys.argv[1:]
	#size = (1800, 950)
	size = (800, 600)
	isServer = None
	server = None
	ipv6 = False
	help = False
	while len(argv) > 0:
		a = argv[0]
		if a == "serve" and len(argv) >= 2:
			port = int(argv[1])
			isServer = True
			argv = argv[2:]
		elif a == "connect" and len(argv) >= 3:
			isServer = False
			server = argv[1]
			port = int(argv[2])
			argv = argv[3:]
		elif a == "--ipv6":
			ipv6 = True
			argv = argv[1:]
		else:
			print ("invalid argument: {}".format(a))
			help = True
			break
	if help or isServer is None:
		appName = "sync.py"
		print ("\nwYPeboard\n")
		print ("usage:")
		print ("   server:  {} [options] serve <port>".format(appName))
		print ("   client:  {} [options] connect <server> <port>".format(appName))
		print ("\noptions:")
		print ("   --ipv6   use IPv6 instead of IPv4")
		sys.exit(1)
	whiteboard = DispatchingWhiteboard("wYPeboard server" if isServer else "wYPeboard client", isServer, canvasSize=size)
	if isServer:
		startServer(port, whiteboard, ipv6=ipv6)
	else:
		startClient(server, port, whiteboard, ipv6=ipv6)
	whiteboard.startRendering()
	app.MainLoop()
