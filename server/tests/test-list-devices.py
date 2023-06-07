import pexpect
import time

child_server = pexpect.spawn('python3 server.py')
child_server.expect('Listening for connections on 127.0.0.1:1234...')

child_user = pexpect.spawn('python3 client.py u')

# check no devices visible
child_user.sendline('LIST')
child_user.expect("\r {'method': 'alert', 'alert': {'devices': \[\]}}\r\nu > ")

# check first device visible
child_device1 = pexpect.spawn('./device/target/debug/rdfm-device-client --name "d1"')
time.sleep(1)
child_user.sendline('LIST')
child_user.expect("\r {'method': 'alert', 'alert': {'devices': \['d1'\]}}\r\nu > ")

# check second device visible
child_device2 = pexpect.spawn('./device/target/debug/rdfm-device-client --name "d2"')
time.sleep(1)
child_user.sendline('LIST')
child_user.expect("\r {'method': 'alert', 'alert': {'devices': \['d1', 'd2'\]}}\r\nu > ")

# check second device disconnected and not visible
child_device2.close()
time.sleep(1)
child_user.sendline('LIST')
child_user.expect("\r {'method': 'alert', 'alert': {'devices': \['d1'\]}}\r\nu > ")

print('List devices test passed!')