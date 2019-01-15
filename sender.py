from socket import socket, AF_INET, SOCK_DGRAM, timeout
from threading import Thread
import os.path
import struct
import time
import sys

#Returns a 16-bit integer checksum
def checksum(data):  
    checksum = 0
    
    data = bytearray(data)
    if(len(data) & 1):               #if length of data is odd
        data += struct.pack('!B', 0) #add one byte to ease splitting process
    
    lData = len(data)

    for i in range(0, lData, 2):
        checksum += (int(data[i]) << 8) + (int(data[i + 1])) #shift the first char over 8 bytes and add it to the 2nd char 
                                                   # in order to make it 16-bits long
    
    overflow = (checksum >> 16)                 #get any carry-over if necessary
    checksum = (checksum & 0xFFFF) + overflow   #ensure checksum is 16 bits long and add the overflow
    checksum = ~checksum & 0xFFFF               #flip the checksum and 0 out the remaining larger bits
    return checksum

#Constructs a header to be sent with the rest of the packet
def createHeader(seqNum, ack, fin, data):
    strNum = str(seqNum)

    #Append 0s to the front of strNum and strChk to ensure consistent header size
    for i in range(len(strNum), 3):
        strNum = '0' + strNum 

    strChk = str(checksum(strNum + str(ack) + str(fin) + data))
    for i in range(len(strChk), 5):
        strChk = '0' + strChk

    return (strNum + strChk + str(ack) + str(fin))
	
def send():
    global base 
    global seqNum
    global pkts
    global fin
    global base_time
    global len_pkts
    global pktsent
	global wnd
	global ackBuffer
	
	ackFlag = True
    readSize = 100
    len_pkts = 0

    with open(FNAME) as f:
		if seqNum < ((base + wnd)) and len(pkts) <= (wnd-1): #window/bounds check

			content =  f.read(readSize-headerSize)
			len_pkts += 1
			header = ""

			#if no more data to read in file...
			if not content: 
				header = createHeader(seqNum, 0, 1, content) #send fin signal to receiver
				fin = 1
				print '100% of file sent.'
			else:
				header = createHeader(seqNum, 0, 0, content)
			
			content = header + content   #Attach header to content read from file
			pkts.append(content)
			send_sock.sendto(content, dest)
			pktsent += 1

			#Restart the timeout thread
			if base == seqNum:
				base_time = time.time()

			seqNum = (seqNum + 1) % 999
        while not fin:
			for i in ackBuffer:
				if(ackBuffer[i] == 0):
					ackFlag = False
			if(ackBuffer):
				if seqNum < ((base + wnd)) and len(pkts) <= (wnd-1): #window/bounds check

					content =  f.read(readSize-headerSize)
					len_pkts += 1
					header = ""

					#if no more data to read in file...
					if not content: 
						header = createHeader(seqNum, 0, 1, content) #send fin signal to receiver
						fin = 1
						print '100% of file sent.'
					else:
						header = createHeader(seqNum, 0, 0, content)
					
					content = header + content   #Attach header to content read from file
					pkts.append(content)
					send_sock.sendto(content, dest)
					pktsent += 1

					#Restart the timeout thread
					if base == seqNum:
						base_time = time.time()

					seqNum = (seqNum + 1) % 999

    print pktsent, 'packets sent'

def receiveACKs():
    global base
    global pkts
    global timeout_thread
    global base_time
    global len_pkts
    global wnd
    reT = 0

    while True:
        packet, address = recv_sock.recvfrom(4096)
        seqNumPkt, checksumPkt, ackPkt, finPkt, data = packet[:3], packet[3:8], packet[8], packet[9], packet[10:]
        chksum = checksum( seqNumPkt + ackPkt + finPkt + data)
        
        if chksum == int(checksumPkt) and int(seqNumPkt) < ((base + wnd)):
            #Clear ACKed packets from array
            if len(pkts) > 0:
		r = int(seqNumPkt) - base
		if r == 0 and int(seqNumPkt) == base:
			r = 1	
		for i in range(0,r):
            		del pkts[i]
            		len_pkts -= 1
    		if base % (wnd) == 0:
    			deletePkts()
			ackBuffer[seqNumPkt%wnd] = 1
            #increase base of window
            base = (int(seqNumPkt) + 1) % 999

            if base == seqNum:
               base_time = 0
            else:
                base_time = time.time()

            #all data has been sent and all acks have been received
            if fin and int(finPkt):
                header = createHeader(base, 0, 1, '') #send final fin signal to receiver
		
		pkts.append(header)
                send_sock.sendto(header, dest)
                break

def deletePkts():
	global pkts
	pktlen = len(pkts)

	#Return if pkts is in a valid order.
	if pktlen > 0 and int(pkts[0][0:3]) >=base:
		return

	#Delete packets that have already been acked.
	i = 0
	while i < pktlen:
		if int(pkts[i][0:3]) < base:
			del pkts[i]
			pktlen -= 1
		elif int(pkts[i][0:3]) >= base: 
			break
		else:
			i += 1

def timeout():
    global timeouts
    global base_time

    base_time = time.time() #time in seconds of first packet sent to receiver since timer started
    while recv_thread.isAlive():
        if (base_time != 0) and (time.time() - base_time >= .02): #If time threshold passed, retransmit
	    pkts_temp = pkts[:]	
            timeouts += 1
            base_time = time.time()
            for i in range(0, len(pkts_temp)):
                 send_sock.sendto(pkts_temp[i], dest)

timeout_thread = None
timeouts = 0
base = 0
pkts = []
seqNum = 0
wnd = 32
FNAME = "alice.txt"
fin = 0
base_time = 0
pktsent = 0
headerSize = len(createHeader(0, 0, 0, ''))
ackBuffer = [0]*wnd

if __name__ == "__main__":
    if(len(sys.argv) != 7):
    	print '# arguments incorrect. Check Readme for format.'
        sys.exit

    dest = (argv[1], int(argv[2]))
    listen = (argv[3], int(argv[4]))

    if not (argv[5] == ""):
	FNAME = argv[5]
    if not (argv[6] == ""):
    	wnd = int(argv[6])  
	
    send_sock = socket(AF_INET, SOCK_DGRAM) #opens a new socket
    recv_sock = socket(AF_INET, SOCK_DGRAM)
    recv_sock.bind(listen)

    #Create threads to be run concurrently.
    send_thread = Thread(target = send)
    recv_thread = Thread(target = receiveACKs)
    time_out_thread = Thread(target = timeout)
    start_time = time.time()

    #Start necessary threads 
    send_thread.start()
    recv_thread.start()
    time_out_thread.start()

    recv_thread.join()
    progTime = time.time() - start_time
    time.sleep(.5)
    print 'Time to run program: ', progTime, ' seconds'
    print 'Throughput: ', os.path.getsize(FNAME)/progTime , 'Bytes per second'
    print '# of timeouts/retransmissions; ', timeouts
