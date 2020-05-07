# -*- coding: utf-8 -*-
import imaplib
import getpass
import email
import email.header
import datetime
import time
import ants.utils as utils
import json
import logging
import threading

from ants.provider.provider import Provider


class EmailProvider(Provider):
    def __init__(self, request_raw_data=False):
        Provider.__init__(self)
        self.logger = logging.getLogger(__name__)
        self.isRun = True
        self.request_raw_data = request_raw_data
        self.load_setting("configs/mail.key")

    def run(self):
        self.logger.info("email provider run.")
        mailConn = self.conn()
        if mailConn is None:
            self.logger.error("Can" "t get mail connect")
            return

        ret = self.login(mailConn)
        if ret != "OK":
            self.logger.error(ret)
            return

        # 시작하기전에 메일을 비워준다
        self.clearMailBox(mailConn)

        self.thread_hnd = threading.Thread(target=self._run, args=(mailConn,))
        self.thread_hnd.start()

    def stop(self):
        self.logger.info("email provider will stop...")
        self.isRun = False
        self.thread_hnd.join()
        self.logger.info("email provider will stop.")

    def _run(self, mailConn):
        self.errorCnt = 0
        while self.isRun:
            try:
                self.openFolder(mailConn)
                time.sleep(5)  # 입력값은 초단위이다. n초마다 업데이트 확인함
                mthList = self.mailSearch(mailConn)
                msgList = self.getMailList(mailConn, mthList)

                for msg in msgList:
                    if self.request_raw_data == False:
                        ret = self.parsingMsg(msg[0][1])
                        if ret != {}:
                            self.logger.info("doActoin :{}".format(ret))
                            self.notify(ret)
                            self.logger.info("actoin done")
                    else:
                        self.notify(self.get_header(msg[0][1]))

                self.closeFolder(mailConn)
            except Exception as exp:
                self.logger.warning("_run : {}".format(exp))
                time.sleep(30)

                mailConn = self.connectionReset()

                if mailConn == None:
                    self.errorCnt += 1
                    if self.errorCnt > 10:
                        self.logger.error(
                            "email connection has some probleam. PROVIDER BE STOP!! : errorCnt > 10"
                        )
                        # TODO 사용자에게 알림을 날려준다.
                        self.isRun = False
                        break
                else:
                    self.errorCnt = 0

        self.logout(mailConn)
        self.logger.info("Thread will terminate!")

    def connectionReset(self):
        self.logger.warning("connetion has some probleam. Connection will reset.")
        M = self.conn()
        if M == None:
            return M

        ret = self.login(M)
        if ret != "OK":
            self.logger.error("Can" "t get connetion() : {}".format(ret))
            return None

        return M

    def register(self, update, coins):
        self.logger.info("register update")
        self.attach(update)

    def load_setting(self, file_name):
        config = utils.readKey(file_name)
        self.account = config["id"]
        self.password = config["password"]
        self.folder = config["folder"]
        self.imap_server = config["imap_server"]
        try:
            self.delete_mail = config["after_read_delete"].upper()
            if self.delete_mail == "TRUE":
                self.delete_mail = True
            else:
                self.delete_mail = False
        except Exception:
            self.delete_mail = False

    def get_header(self, data):
        msg = email.message_from_bytes(data)
        hdr = email.header.make_header(email.header.decode_header(msg["Subject"]))

        subject = str(hdr)

        return subject

    def parsingMsg(self, data):
        # 샘플 확보용 코드
        # utils.saveBinFile('/tmp/email.sample',data)

        subject = self.get_header(data)

        self.logger.debug("subject : {}".format(subject))
        # subject ex) TradingView Alert: #BTCKRW #1M #SELL #BITHUMB

        _list = subject.split("#")
        ret = {}
        ret["market"] = _list[1].strip()
        ret["time"] = _list[2].strip()
        ret["action"] = _list[3].strip()
        ret["exchange"] = _list[4].strip()

        return ret

    def setFlag(self, M, msg_num):
        """
        Gmail에선 Delete가 제대로 되지 않는 경우가 있다
        https://stackoverflow.com/questions/3180891/imap-deleting-messages
        그래서 Trash로 이동하는 루틴으로 바꿈
        """
        action = "\\Seen"
        if self.delete_mail:
            action = "\\Deleted"

        if self.is_gmail:
            M.store(msg_num, "+X-GM-LABELS", "\\Trash")

        typ, data = M.store(msg_num, "+FLAGS", action)
        if typ != "OK":
            self.logger.warning("{}/{} FLAGS setting error {}".format(msg_num, action, typ))
            return

        self.logger.debug("{} is {}".format(msg_num, action))

    def getLocalTime(self, msg):
        # Now convert to local date-time
        date_tuple = email.utils.parsedate_tz(msg["Date"])
        if date_tuple:
            local_date = datetime.datetime.fromtimestamp(email.utils.mktime_tz(date_tuple))
            self.logger.info("Local Date:", local_date.strftime("%a, %d %b %Y %H:%M:%S"))
            return "No have time info"

        return local_date

    def mailSearch(self, M):
        # rv, data = M.search(None, "ALL")
        rv, data = M.search(None, "(UNSEEN)")
        if rv != "OK":
            self.logger.info("No messages found!")
            return

        self.logger.debug("mail list : {}".format(data[0].split()))

        return data[0].split()  # 메일 id 리스트를 넘겨준다

    def getMailList(self, M, mList):
        mailList = []
        for msg_num in mList:
            rv, data = M.fetch(msg_num, "(RFC822)")
            if rv != "OK":
                self.logger.warning("ERROR getting message : {}".format(msg_num))
                pass

            mailList.append(data)
            self.setFlag(M, msg_num)

        return mailList

        # msg = parsingMsg(data[0][1])
        # setFlag(M, msg_num, '+FLAGS', '\\Seen')

    def conn(self):
        mailConn = None
        try:
            mailConn = imaplib.IMAP4_SSL(self.imap_server)
            if self.imap_server.find("gmail") > -1:
                self.is_gmail = True
            else:
                self.is_gmail = False

        except Exception as exp:
            self.logger.error("Connecting error : {}".format(exp))

        return mailConn

    def login(self, conn):
        try:
            rv, data = conn.login(self.account, self.password)
            self.logger.info("IMAP Login {},\t{}".format(rv, data))
        except imaplib.IMAP4.error as exp:
            self.logger.error("LOGIN FAILED!!! {}".format(exp))
            return "False"

        return "OK"

    def openFolder(self, M):
        rv, data = M.select(self.folder)
        if rv == "OK":
            pass
        else:
            self.logger.warning("ERROR: Unable to open mailbox : {}".format(rv))

    def getFolderList(self, M):
        rv, mailBoxes = M.list()
        if rv == "OK":
            self.logger.info("Mailboxes:\n{}".format(mailBoxes))

    def closeFolder(self, M):
        M.close()

    def logout(self, M):
        M.logout()

    def clearMailBox(self, M):
        self.openFolder(M)
        self.logger.info("Mailbox clear")
        data = self.mailSearch(M)
        self.getMailList(M, data)
        self.closeFolder(M)


if __name__ == "__main__":
    print("mail test")
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    stream_hander = logging.StreamHandler()
    stream_hander.setFormatter(formatter)
    logger.addHandler(stream_hander)

    import signal

    def signal_handler(sig, frame):
        print("\nExit Program by user Ctrl + C")
        ep.stop()

    signal.signal(signal.SIGINT, signal_handler)

    ep = EmailProvider()
    ep.load_setting("configs/mail.key")
    ep.run()
