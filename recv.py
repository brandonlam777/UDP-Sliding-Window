from socket import socket, AF_INET, SOCK_DGRAM
from sys import argv
import struct

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
	
def createHeader(seqNum, ack, fin, data):
    strNum = str(seqNum)

    #Append 0s to the front of strNum and strChk to ensure consistent header size
    for i in range(len(strNum), 3):
        strNum = '0' + strNum 

    strChk = str(checksum(strNum + str(ack) + str(fin) + data))
    for i in range(len(strChk), 5):
    	strChk = '0' + strChk

    return (strNum + strChk + str(ack) + str(fin))
	
if __name__ == "__main__":
	#Get command line args
	sender = (argv[1], int(argv[2]))
	recv = (argv[3], int(argv[4]))
	windowSize = int(argv[5])
	send_socket = socket(AF_INET,SOCK_DGRAM) #set up UDP sockets
	recv_socket = socket(AF_INET,SOCK_DGRAM)
	recv_socket.bind(recv) #bind receive socket to port
	
	fileName, addr = sock.recvfrom(bufferSize)
	fileSize, addr = sock.recvfrom(bufferSize)
	
	framesRequired = (fileSize/windowSize)
	opFile = open('rcvdData.txt', 'w')
	expSeqNum = 0
	ack = 1
	fin3way = False
	fin = 0
	dataBuffer = [None]* windowSize
	outOfOrderBuffer = [0]*windowSize
	ackBuffer = [0]*windowSize
	ackFlag = True
	while(True):
		packet, address = recv_socket.recvfrom(4096)
		
		seqNumPkt, checksumPkt, ackPkt, finPkt, data = packet[:3], packet[3:8], packet[8], packet[9], packet[10:]
		
		if checksum(str(seqNumPkt) + str(ackPkt) + str(finPkt) + data) == int(checksumPkt):
			if finPkt == '1':
				if(not fin3way):
					fin3way = True
				else:
					break
				fin = 1
				send_socket.sendto(createHeader(expSeqNum, ack, fin, ''), sender)
			header = createHeader(expSeqNum, ack, fin, '')
			send_socket.sendto(header,sender)
			expSeqNum += 1
			expSeqNum = expSeqNum % 999
			ackBuffer[seqNumPkt%32] = ack
			dataBuffer[seqNumPkt%32] = data

		for i in ackBuffer:
			if (ackBuffer[i] == 0):
				ackFlag = False
		if ackFlag:
			for i in range(0, windowSize)-1):
				opFile.write(dataBuffer[i])
				dataBuffer[i] = None
				ackBuffer[i] = 0
				
	print 'File successfully received. (Stored in rcvdData.txt)'
	opFile.close() #close file
