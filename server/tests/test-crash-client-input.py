import pexpect
import time

child_server = pexpect.spawn('python3 server.py')
child_user = pexpect.spawn('python3 client.py USER u')

# check invalid request warning
child_user.sendline('this input should throw a warning testtesttest........')
time.sleep(3)
child_user.expect("Invalid request")

# check server replying
child_user.sendline('LIST')
child_user.expect("\r {'method': 'alert', 'alert': {'devices': \[\]}}\r\nu > ")

print('Invalid user input crash test passed!')