import pexpect

# currently there are d1 and d2 devices connected in the docker-compose
# and the server is visible on 0.0.0.0:1234
child_user = pexpect.spawn('python3 client.py USER u')
child_user.expect_exact('u > ')
child_user.sendline('LIST')
child_user.expect_exact("u > {'Devices': \['d1', 'd2'\]}")

print('Docker connect test passed!')