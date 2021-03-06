import dkim
import os
import smtplib
import mimetypes
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.audio import MIMEAudio
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr, formatdate
from email import encoders

class Email():
    
    def __init__(self):
        self.setEmailType()
        self.setCharset()
        self.serverFromAddr=None
        self.serverFromName=None
        self.serverToAddrs=[]
        self.toAddr=[]
        self.ccAddr=[]
        self.bccAddr=[]
        self.attachmentList=[]
        self.attachmentNum=0
        self.dkimPrivateKeyPath=None
        self.dkimSelector='dkim'


    def setServer(self,server='localhost',port=25,smtpUser=None,smtpPass=None,timeOut=600,tryTime=3):
        self.smtpServer=server
        self.smtpPort=port
        self.smtpUser=smtpUser
        self.smtpPass=smtpPass
        self.tryTime=tryTime
        self.timeOut=timeOut
        if self.serverFromAddr == None:
            self.serverFromAddr = 'dev@local.loc'
        

    def setEmailType(self,mailType='plain'):
        self.mailType=mailType
        
    def setCharset(self,charset='utf-8'):
        self.charset=charset
    
    def setSubject(self,subject):
        self.subject=subject.encode(self.charset)
    
    def setContent(self,content):
        self.content=content.encode(self.charset)
    
    def setServerFromAddr(self,fromAddr):
        self.serverFromAddr=fromAddr
        
    def setDkimPrivateKeyPath(self, dkimKeyPath):
        self.dkimPrivateKeyPath=dkimKeyPath
        
    def setServerFromName(self,fromName):
        self.serverFromName=fromName    
        
    def addToAddr(self,toAddr):
        self.toAddr.append(toAddr)
        self.serverToAddrs.append(toAddr)
    
    def addCcAddr(self,ccAddr):
        self.ccAddr.append(ccAddr)
        self.serverToAddrs.append(ccAddr)
    
    def addBccAddr(self,bccAddr):
        self.bccAddr.append(bccAddr)
        self.serverToAddrs.append(bccAddr)

    def addAttachment(self,filepath,filename=None):
        if filename == None:
            filename=os.path.basename(filepath)
        with open(filepath,'rb') as f:
            file=f.read()
        ctype, encoding = mimetypes.guess_type(filepath)
        if ctype is None or encoding is not None:ctype = "application/octet-stream"
        maintype, subtype = ctype.split('/', 1)

        if maintype == "text":
            with open(filepath) as f:file=f.read()
            attachment = MIMEText(file, _subtype=subtype)
        elif maintype == "image":
            with open(filepath,'rb') as f:file=f.read()
            attachment = MIMEImage(file, _subtype=subtype)
        elif maintype == "audio":
                with open(filepath,'rb') as f:file=f.read()
                attachment = MIMEAudio(file, _subtype=subtype)
        else:
                with open(filepath,'rb') as f:file=f.read()
                attachment = MIMEBase(maintype,subtype)
                attachment.set_payload(file)
                attachment.add_header('Content-Disposition', 'attachment', filename=filename)
                encoders.encode_base64(attachment)

        attachment.add_header('Content-Disposition', 'attachment', filename=filename)
        attachment.add_header('Content-ID',str(self.attachmentNum))
        self.attachmentNum+=1
        self.attachmentList.append(attachment)

    def send(self):
        if len(self.attachmentList) == 0:
            self.msg = MIMEText(self.content, self.mailType, self.charset)
        else:
            self.msg = MIMEMultipart()
            self.msg.attach(MIMEText(self.content, self.mailType, self.charset))
            for attachment in self.attachmentList:
                self.msg.attach(attachment)

        self.msg['Subject'] = Header(self.subject,self.charset)
        self.msg['From'] = formataddr((self.serverFromName, self.serverFromAddr))
        self.msg['To'] = ",".join(self.toAddr)
        if self.ccAddr:
            self.msg['cc'] = ",".join(self.ccAddr)
        if self.bccAddr:
            self.msg['bcc'] = ",".join(self.bccAddr)
        sender_domain = self.serverFromAddr.split("@")[-1]
        if self.dkimPrivateKeyPath and self.dkimSelector:
            # the dkim library uses regex on byte strings so everything
            # needs to be encoded from strings to bytes.
            with open(self.dkimPrivateKeyPath) as fh:
                dkim_private_key = fh.read()
            headers = [b"From", b"To", b"Reply-To", b"Subject"]
            sig = dkim.sign(
                message=self.msg.as_bytes(),
                selector=str(self.dkimSelector).encode(),
                domain=sender_domain.encode(),
                privkey=dkim_private_key.encode(),
                include_headers=headers,
            )
            # add the dkim signature to the email message headers.
            # decode the signature back to string_type because later on
            # the call to msg.as_string() performs it's own bytes encoding...
            self.msg["DKIM-Signature"] = sig[len("DKIM-Signature: "):].decode()

        #send
        for a in range(self.tryTime):
            try:
                if self.smtpPort == 25:
                    server = smtplib.SMTP(self.smtpServer, self.smtpPort,timeout=self.timeOut)
                else:
                    server = smtplib.SMTP_SSL(self.smtpServer, self.smtpPort,timeout=self.timeOut)
                #server.set_debuglevel(1)
                if self.smtpUser != None and self.smtpPass != None:
                    server.login(self.smtpUser,self.smtpPass)
                server.sendmail(self.serverFromAddr,self.serverToAddrs,self.msg.as_string())
                server.quit()
                break
            except Exception as e:
                print(e)