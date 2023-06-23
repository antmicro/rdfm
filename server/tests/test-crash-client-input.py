import pexpect
import time

child_server = pexpect.spawn('python3 -m rdfm_mgmt_server')
child_user = pexpect.spawn('python3 -m rdfm_mgmt_client u')

# check invalid request warning
time.sleep(3)
child_user.sendline('this input should throw a warning testtesttest........')
child_user.expect_exact("Invalid request")

telnet_client = pexpect.spawn('telnet 127.0.0.1 1234')
telnet_client.sendline('server should not crash test test')

# check server replying
child_user.sendline('LIST')
child_user.expect_exact("\r {'method': 'alert', 'alert': {'devices': []}}\r\nu > ")

print('Invalid user input crash test passed!')