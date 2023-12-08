import datetime
from colorama import Fore, Back, Style

class Logger(object):
    def info(self, msg):
        print(f"{Fore.BLUE}[{datetime.datetime.now().strftime('%a %b %d %H:%M:%S %Y')}] [INFO] {msg}")
    
    def warn(self, msg):
        print(f"{Fore.YELLOW}[{datetime.datetime.now().strftime('%a %b %d %H:%M:%S %Y')}] [WARN] {msg}")
    
    def error(self, msg):
        print(f"{Fore.RED}[{datetime.datetime.now().strftime('%a %b %d %H:%M:%S %Y')}] [ERROR] {msg}")

    def debug(self, msg):
        print(f"{Fore.CYAN}[{datetime.datetime.now().strftime('%a %b %d %H:%M:%S %Y')}] [DEBUG] {msg}")
    
    def success(self, msg):
        print(f"{Fore.GREEN}[{datetime.datetime.now().strftime('%a %b %d %H:%M:%S %Y')}] [SUCCESS] {msg}")
    
    def fail(self, msg):
        print(f"{Back.RED}[{datetime.datetime.now().strftime('%a %b %d %H:%M:%S %Y')}] [FAIL] {msg}")
    
    def log(self, type, msg):
        if type=="INFO":
            self.info(msg)
        elif type=="WARN":
            self.warn(msg)
        elif type=="ERROR":
            self.error(msg)
        elif type=="DEBUG":
            self.debug(msg)
        elif type=="SUCCESS":
            self.success(msg)
        elif type=="FAIL":
            self.fail(msg)
        else:
            self.info(msg)    

    def log2file(self, type, msg, file):
        self.log(type, msg)
        with open(file, "a") as f:
            f.write(f"[{datetime.datetime.now().strftime('%a %b %d %H:%M:%S %Y')}] [{type}] {msg}\n")
        