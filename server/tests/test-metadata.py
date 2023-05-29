import pexpect

child_server = pexpect.spawn('python3 server.py')
child_user = pexpect.spawn('python3 client.py USER u')
child_device1 = pexpect.spawn('python3 client.py DEVICE d1 -f tests/testdata.json')

# check initial info
child_user.sendline('REQ d1 info')
child_user.expect("\r {}\r\nu > ", timeout=1)

# check first device visible
child_user.sendline('REQ d1 refresh')
child_user.expect("{'device': 'd1', 'message': {'metadata': {'a': 5, 'b': 'foo', 'c': {'d': 'bar', 'e': 2}, 'last_updated': .*?}}}\r\nu > ")

child_user.sendline('REQ d1 info')
child_user.expect("{'a': 5, 'b': 'foo', 'c': {'d': 'bar', 'e': 2}, 'last_updated': .*?}\r\nu > ")


print('List devices test passed!')