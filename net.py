# (C) 2014 by Dominik Jain (djain@gmx.net)

import asyncore
import socket
import logging
import threading
import pickle
import hashlib
from Tools import *

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

#网络模块 Socket抽象
class SocketAbstract(asyncore.dispatcher_with_send):
    def __init__(self, ipv6=False, sock=None):
        asyncore.dispatcher_with_send.__init__(self, sock=sock)

        self.endTerminator = "\r\n\r\n$end$\r\n\r\n"
        self.recvBuffer = b""
        self.__debug = False
        # self.ipv6 = ipv6

    def createSocket(self):
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)  #开启Socket

    def endSocket(self):
        self.end_socket(socket.AF_INET, socket.SOCK_STREAM)  # 关闭Socket

    # 发送包
    def send(self, data):
        log.debug("sending packet; size %d" % len(data))
        if self.__debug:
            log.debug("hash: %s", hashlib.sha224(data).hexdigest())

        #通过缓冲区 实现单线程的消息传递
        self.out_buffer = self.out_buffer + data + self.endTerminator.encode("utf-8")

    # 接受包
    def handle_read(self):

        #接收byte串
        d = self.recv(8192)
        if d == "":         # 非指定终结符，清空接收内容返回
            return

        #接收缓冲
        self.recvBuffer += d
        log.debug("recvBuffer size: %d" % len(self.recvBuffer))

        while True:
            try:
                print(self.recvBuffer)
                tpos = self.recvBuffer.index(self.endTerminator.encode("utf-8"))    #接收包分割

            except:
                print("no terminator")      #非接收内容或错误 丢弃
                break

            packet = self.recvBuffer[:tpos] #解析包

            log.debug("received packet; size %d" % len(packet))
            if self.__debug: log.debug("hash: %s", hashlib.sha224(packet).hexdigest())
            # if len(packet) > 20000:
            #     with open("bigdata.dat", "wb") as f:
            #         f.write(packet)
            #         f.close()
            #
            self.getPacket(packet)
            self.recvBuffer = self.recvBuffer[tpos+len(self.endTerminator):]    #下一个包处理

    # 处理包 (可删除）
    def getPacket(self, packet):
        ''' handles a read packet '''
        print("IN the PACKET")
        log.warning('unhandled packet; size %d' % len(packet))



class SyncServer(SocketAbstract):
    def __init__(self, port, socket,ipv6 = False):
        SocketAbstract.__init__(self)

        #使用Socket
        self.delegate = socket
        self.delegate.setDispatcher(self)

        #开启socket
        # start listening for connections
        self.createSocket()

        host = ""
        self.bind((host, port))
        self.connections = []
        self.listen(5)

    def handle_accept(self):
        pair = self.accept()
        if pair is None:
            return
        log.info("incoming connection from %s" % str(pair[1]))
        conn = DispatcherConnection(pair[0], self)
        self.connections.append(conn)   #添加通道
        # send initial data to new user
        self.delegate.handle_ClientConnected(conn)

    # 通道
    def dispatch(self, d, exclude=None):
        numClients = len(self.connections) if exclude is None else len(self.connections)-1
        if type(d) == dict and "evt" in d:
            evt = d["evt"]
            if evt != "moveUserCursor":
                log.debug("dispatching %s to %d clients" % (evt, numClients))
        for c in self.connections:
            if c != exclude:
                c.dispatch(d)

    # 删除连接
    def removeConnection(self, conn):
        if not conn in self.connections:
            log.error("tried to remove non-present connection")
        self.connections.remove(conn)
        self.delegate.handle_ClientConnectionLost(conn)
        if len(self.connections) == 0:
            self.delegate.handle_AllClientConnectionsLost()

class Connection(SocketAbstract):
    def __init__(self,server,connection):
        SocketAbstract.__init__(self, sock=connection)
        self.syncserver = server

    # 接包
    def handle_packet(self, packet):
        log.debug("handling packet; size %d" % len(packet))
        if packet == "":  # connection closed from other end
            return
        self.syncserver.delegate.handle_PacketReceived(packet, self)

    # 断开连接
    def remove(self):
        log.info("client connection dropped")
        self.syncserver.removeConnection(self)

    # 关闭
    def handle_close(self):
        self.remove()
        self.close()

    def dispatch(self, d):
        self.send(pickle.dumps(d))

#改成工厂模式
class DispatcherConnection(Connection):
    def __init__(self, connection, server):
        SocketAbstract.__init__(self, sock=connection)
        self.syncserver = server

    # 接包
    def handle_packet(self, packet):
        log.debug("handling packet; size %d" % len(packet))
        if packet == "": # connection closed from other end
            return
        self.syncserver.delegate.handle_PacketReceived(packet, self)

    # 断开连接
    def remove(self):
        log.info("client connection dropped")
        self.syncserver.removeConnection(self)

    # 关闭
    def handle_close(self):
        self.remove()
        self.close()

    def dispatch(self, d):
        self.send(pickle.dumps(d))

#客户
class SyncClient(SocketAbstract):
    def __init__(self, server, port, delegate, ipv6=False):
        SocketAbstract.__init__(self, ipv6=ipv6)
        self.delegate = delegate
        self.delegate.setDispatcher(self)
        self.serverAddress = (server, port)
        self.connectedToServer = self.connectingToServer = False
        self.connectToServer()

    def connectToServer(self):
        log.info("connecting to %s..." % str(self.serverAddress))
        self.connectingToServer = True
        self.createSocket()
        self.connect(self.serverAddress)

    def handle_connect(self):
        log.info("connected to %s" % str(self.serverAddress))
        self.connectingToServer = False
        self.connectedToServer = True
        self.delegate.handle_ConnectedToServer()

    def handle_packet(self, packet):
        if packet == "": # server connection lost
            return
        self.delegate.handle_PacketReceived(packet, None)

    def handle_close(self):
        self.close()

    def close(self):
        log.info("connection closed")
        self.connectedToServer = False
        asyncore.dispatcher.close(self)
        self.delegate.handle_ConnectionToServerLost()

    # connection interface

    def dispatch(self, d, exclude=None):
        if not self.connectedToServer:
            return
        if not (type(d) == dict and "ping" in d):
            pass
        self.send(pickle.dumps(d))

    def reconnect(self):
        self.connectToServer()

#网络进程
def spawnNetworkThread():
    networkThread = threading.Thread(target=lambda:asyncore.loop(timeout=0.1))
    networkThread.daemon = True
    networkThread.start()

#开启服务
def startServer(port, delegate, ipv6=False):
    log.info("serving on port %d, IPv6: %s" % (port, ipv6))
    server = SyncServer(port, delegate, ipv6=ipv6)
    spawnNetworkThread()
    delegate.handle_ServerLaunched()

#开启客户端
def startClient(server, port, delegate, ipv6=False):
    log.info("connecting to %s:%d, IPv6: %s" % (server, port, ipv6))
    client = SyncClient(server, port, delegate, ipv6=ipv6)
    spawnNetworkThread()
