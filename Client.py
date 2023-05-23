# -------------------------------------GUI modules
from tkinter import messagebox
from tkinter import ttk
from ttkbootstrap import Style
from PIL import Image, ImageTk
# -------------------------------------Networking modules
import socket, threading, os
# -------------------------------------Internal modeules
from RtpPacket import RtpPacket
# --------------------------------------Debugging modules

CACHE_FILE_NAME = "cache-"
CACHE_FILE_EXT = ".jpg"


class Client:
    request_code = {
        'SETUP': 0,
        'PLAY': 1,
        'PAUSE': 2,
        'TEARDOWN': 3
    }
    state_code = {
        'INIT': 0,
        'READY': 1,
        'PLAYING': 2
    }
    state = state_code['INIT']


    # Initiation..
    def __init__(self, master, serveraddr, serverport, rtpport, filename):
        self.master = master
        self.master.protocol("WM_DELETE_WINDOW", self.handler)
        self.createWidgets()
        self.serverAddr = serveraddr
        self.serverPort = int(serverport)
        self.rtpPort = int(rtpport)
        self.fileName = filename
        self.rtspSeq = 0
        self.sessionId = 0
        self.requestSent = -1
        self.teardownAcked = 0
        self.connectToServer()
        self.frameNbr = 0
        # self.waitForUpdate = threading.Event(); self.waitForUpdate.set()
        # Use to calculate video stream statistics
        self.videoStream = {
            'fps': 0,
            'prevTimestamp': 0,
            'noRecievedFrame': 0,
            'firstPacket': None
        }

    def createWidgets(self):
        """Build GUI."""
        self.style = Style(theme='darkly')
        # Create Play button
        self.start = ttk.Button(
            self.master,
            text='Play',
            command=self.playMovie,
            width = 20,
            bootstyle="primary"
            )
        self.start.grid(row=2, sticky="snew", column=0, padx=2, pady=2)

        # Create Pause button
        self.pause = ttk.Button(
            self.master,
            text='Pause',
            command=self.pauseMovie,
            width=20,
            bootstyle="primary"
        )
        self.pause.grid(row=2, sticky="snew", column=1, padx=2, pady=2)
        # Create Teardown button
        self.stop = ttk.Button(
            self.master,
            text='Stop',
            command=self.exitClient,
            width = 20,
            bootstyle="dangerous"
        )
        self.stop.grid(row=2, sticky="snew", column=2, padx=2, pady=2)
        # Create a label to display the movie
        self.style.configure('VideoFrame.TLabel', height=20)
        self.label = ttk.Label(self.master, style='VideoFrame.TLabel')
        self.label.grid(row=0, column=0, columnspan=3, sticky="snew")


        # ProgressBar button
        self.progressbar = ttk.Progressbar(
            self.master,
            orient='horizontal',
            length=100,
            maximum=30,
            mode='determinate'
        )
        self.progressbar.grid(row=1, column=0, columnspan=3, sticky="snew")
        self.progressbar.bind('<Button-1>', self.seek)

    def setupMovie(self):
        """Setup button handler."""
        if self.state == Client.state_code['INIT']:
            self.sendRtspRequest('SETUP')

    # TODO

    def exitClient(self):
        """Teardown button handler."""
        self.sendRtspRequest('TEARDOWN')
        self.master.destroy()
        cachfile = CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT
        if os.path.exists(cachfile):
            os.remove(cachfile)
        # pdb.set_trace()
    # TODO

    def pauseMovie(self):
        # pdb.set_trace()
        """Pause button handler."""
        if self.state == Client.state_code['PLAYING']:
            self.sendRtspRequest('PAUSE')

    def playMovie(self):
        """Play button handler."""
        # pdb.set_trace()
        if self.state == Client.state_code['INIT']:
            self.setupMovie()
        elif self.state == Client.state_code['READY']:
            threading.Thread(target=self.listenRtp).start()
            self.sendRtspRequest('PLAY')

    def seek(self, event):
        x = event.x_root - self.progressbar.winfo_rootx()
        position = int((x / self.progressbar.winfo_width()))
        seek_frameNumber = self.videoStream['fps'] * position
    def listenRtp(self):
        """Listen for RTP packets."""
        # pdb.set_trace()
        while True:
            try:
                data = self.rtpSocket.recv(20480)
                if data:
                    pkt = RtpPacket()
                    pkt.decode(data)
                    if pkt.seqNum() > self.frameNbr:
                        filename = self.writeFrame(pkt.getPayload())
                        self.updateMovie(filename, pkt.timestamp())
                        # Update video stream stats
                        self.updateFrameRate(pkt)
            except: # attempt to read the data after PAUSE or TEARDOWN request sent will cause exception
                if self.requestSent == Client.request_code['PAUSE']:
                    break
                if self.teardownAcked == 1:
                    self.rtpSocket.shutdown(socket.SHUT_RDWR)
                    self.rtpSocket.close()
                    break

    def updateFrameRate(self, currentFrame):
        """ Update the frame rate using EAM formula

        :param currentFrame: just-received RTP packet
        """
        # --------------------Params---------------------------------------
        # pdb.set_trace()
        # self.waitForUpdate.clear()
        frames_unit = 100
        alpha = 0.7
        currentTimestamp = currentFrame.timestamp() % 3600
        prevTimestamp = self.videoStream['prevTimestamp'] % 3600
        # -----------------------------------------------------------------
        if currentFrame.seqNum() == 1:
            self.videoStream['firstPacket'] = currentFrame
            self.videoStream['prevTimestamp'] = currentFrame.timestamp()

        noFrames = self.videoStream['noRecievedFrame']
        if noFrames == frames_unit:
            # pdb.set_trace()
            eam = ( currentTimestamp - prevTimestamp ) / noFrames
            if self.videoStream['fps'] != 0: # not initialized
                # use EAM to calculate the period
                eam = alpha * eam + (1 - alpha) / self.videoStream['fps']

            self.videoStream['fps'] = 1 // eam
            self.videoStream['prevTimestamp'] = currentFrame.timestamp()
            self.videoStream['noRecievedFrame'] = 0
            print(f"Frame updated: {1 // eam}")
        else:
            self.videoStream['noRecievedFrame'] = noFrames + 1
        # self.waitForUpdate.set()
    def writeFrame(self, data):
        """Write the received frame to a temp image file. Return the image file."""
        # pdb.set_trace()
        fileName = CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT
        with open(fileName, mode="wb") as fp:
            fp.write(data)

        return fileName
    # TODO

    def updateMovie(self, imageFile, timestamp):
        # pdb.set_trace()
        """Update the image file as video frame in the GUI."""
        current_frame = ImageTk.PhotoImage(Image.open(imageFile))
        # self.style.configure('VideoFrame.TLabel', height=288)
        self.label.configure(image=current_frame)
                             # , style='VideoFrame.TLabel')
        self.label.image = current_frame
        # pdb.set_trace()
        self.progress_pb(timestamp)
    # TODO

    def connectToServer(self):
        """Connect to the Server. Start a new RTSP/TCP session."""
        self.rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # TCP
        try:
            self.rtspSocket.connect((self.serverAddr, self.serverPort))
            print("Connected to Server: {}:{}".format(self.serverAddr, self.serverPort))
        except:
            messagebox.showerror(f"Failed connection to server {self.serverAddr}:{str(self.serverPort)}")

    def sendRtspRequest(self, requestCode):
        """Send RTSP request to the server."""
        self.rtspSeq = self.rtspSeq + 1

        msg = "{} {} {}\nCSeq: {}\nSession: {}".format(
            requestCode, self.fileName, "RTSP/1.0",
            str(self.rtspSeq),
            str(self.sessionId)
        )
        request = Client.request_code[requestCode]
        if request == Client.request_code['SETUP'] and self.state == Client.state_code['INIT']:
            # Create a separate thread for listening for rtsp reply
            threading.Thread(target=self.recvRtspReply).start()
            msg = msg + "; client_port= {}\n".format(str(self.rtpPort))
        elif request == Client.request_code['PLAY'] and self.state == Client.state_code['READY']:
            pass
        elif request == Client.request_code['PAUSE'] and self.state == Client.state_code['PLAYING']:
            pass
        elif request == Client.request_code['TEARDOWN'] \
                and ( self.state == Client.state_code['READY'] or self.state == Client.state_code['PLAYING']):
            pass
        elif request == Client.request_code['SEEK'] and self.state in [Client.state_code['PLAYING'], Client.state_code['READY']]:
            pass
        else: return

        if(self.requestSent != request):
            self.requestSent = request
            self.rtspSocket.send(msg.encode())
        print(f'{self.requestSent} sent')

    def recvRtspReply(self):
        """Receive RTSP reply from the server."""
        while True:
            reply = self.rtspSocket.recv(1024)
            if reply:
                self.parseRtspReply(reply.decode())
                print("\nRTSP reply: {}".format(reply))
            # End RTSP session
            if self.requestSent == Client.request_code['TEARDOWN']:
                self.rtspSocket.shutdown(socket.SHUT_RDWR)
                self.rtspSocket.close()
                break

    # TODO

    def parseRtspReply(self, data):
        """Parse the RTSP reply from the server."""
        lines = data.split('\n')
        sequence_no = int(lines[1].split(' ')[1])
        if self.sessionId == 0:
            self.sessionId = lines[2].split(' ')[1]
        if self.rtspSeq == sequence_no:
            if self.sessionId == lines[2].split(' ')[1] and lines[0].split(' ')[2] == "OK":
                if self.requestSent == Client.request_code['SETUP']:
                    # Set the session id for the communication
                    self.state = Client.state_code['READY']
                    self.openRtpPort()
                    self.playMovie() # starting play the movie
                elif self.requestSent == Client.request_code['PLAY']:
                    self.state = Client.state_code['PLAYING']
                elif self.requestSent == Client.request_code['PAUSE']:
                    self.state = Client.state_code['READY']
                elif self.requestSent == Client.request_code['TEARDOWN']:
                    # pdb.set_trace()
                    self.state = Client.state_code['INIT']
                    self.teardownAcked = 1
                elif self.requestSent == Client.request_code['SEEK']:
                    self.state =Client.state_code['PLAYING']
        print("Client State: {}".format(self.state))

    def openRtpPort(self):
        """Open RTP socket binded to a specified port."""
        # Create a new datagram socket to receive RTP packets from the server
        self.rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.rtpSocket.settimeout(0.5)
        try:
            self.rtpSocket.bind(("", self.rtpPort))
            self.state = Client.state_code['READY']
        except:
            messagebox.showerror(f"Cannot connect to server{self.serverAddr}:{self.rtpSocket}")

    def handler(self):
        """Handler on explicitly closing the GUI window."""
        if self.state == Client.state_code['PLAYING']:
            self.pauseMovie()
        if messagebox.askokcancel("Quit?", "Are you sure you want to quit?"):
            self.exitClient()
        else:
            self.playMovie()

    def progress_pb(self, current_timestamp):
        '''Advance the timestamp

        :param current_timestamp indicate the timestamp of the current RTP packet
        '''
        first_pkt = self.videoStream['firstPacket']
        if first_pkt:
            self.progressbar['value'] = current_timestamp % 3600 - first_pkt.timestamp() % 3600  # increase by one second