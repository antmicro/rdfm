import pexpect

def default_arguments():
    # default arguments
    child_server = pexpect.spawn('python3 server.py')
    child_server.expect('Listening for connections on 127.0.0.1:1234...')

    child_user = pexpect.spawn('python3 client.py USER u')
    child_user.expect('u > ')

    child_server.close()
    child_user.close()

    print('Default arguments test passed!')

def with_arguments():
    hostname = '0.0.0.0'
    port = '3333'
    child_server = pexpect.spawn(f'python3 server.py -hostname {hostname} -p {port}')
    child_server.expect(f'Listening for connections on {hostname}:{port}...')

    child_user = pexpect.spawn('python3 client.py USER u')
    child_user.expect('ConnectionRefusedError: \[Errno 111\] Connection refused')

    child_user = pexpect.spawn(f'python3 client.py USER u -hostname {hostname} -p {port}')
    child_user.expect('u > ', timeout=1)

    child_server.close()
    child_user.close()

    print('Arguments test passed!')

default_arguments()
with_arguments()