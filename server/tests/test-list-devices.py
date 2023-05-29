import pexpect

child_server = pexpect.spawn('python3 server.py')
child_user = pexpect.spawn('python3 client.py USER u')

# check no devices visible
child_user.sendline('LIST')
child_user.expect("\r {'Devices': \[\]}\r\nu > ", timeout=1)

# check first device visible
child_device1 = pexpect.spawn('python3 client.py DEVICE d1')
child_user.sendline('LIST')
child_user.expect("\r {'Devices': \['d1'\]}\r\nu > ", timeout=1)

# check second device visible
child_device2 = pexpect.spawn('python3 client.py DEVICE d2')
child_user.sendline('LIST')
child_user.expect("\r {'Devices': \['d1', 'd2'\]}\r\nu > ", timeout=1)

# check second device disconnected and not visible
child_device2.close()
child_user.sendline('LIST')
child_user.expect("\r {'Devices': \['d1'\]}\r\nu > ", timeout=1)

print('List devices test passed!')