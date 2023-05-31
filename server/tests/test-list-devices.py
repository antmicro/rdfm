import pexpect
import time

child_server = pexpect.spawn('python3 server.py')
child_user = pexpect.spawn('python3 client.py USER u')

# check no devices visible
child_user.sendline('LIST')
child_user.expect("\r {'method': 'alert', 'alert': {'devices': \[\]}}\r\nu > ")

# check first device visible
child_device1 = pexpect.spawn('python3 client.py DEVICE d1')
time.sleep(1)
child_user.sendline('LIST')
child_user.expect("\r {'method': 'alert', 'alert': {'devices': \['d1'\]}}\r\nu > ")

# check second device visible
child_device2 = pexpect.spawn('python3 client.py DEVICE d2')
time.sleep(1)
child_user.sendline('LIST')
child_user.expect("\r {'method': 'alert', 'alert': {'devices': \['d1', 'd2'\]}}\r\nu > ")

# check second device disconnected and not visible
child_device2.close()
time.sleep(1)
child_user.sendline('LIST')
child_user.expect("\r {'method': 'alert', 'alert': {'devices': \['d1'\]}}\r\nu > ")

print('List devices test passed!')