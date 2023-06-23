import pexpect
import time

def default_arguments():
    # default arguments
    child_server = pexpect.spawn('python3 -m rdfm_mgmt_server')
    child_server.expect_exact('Listening for connections on 127.0.0.1:1234...')

    child_user = pexpect.spawn('python3 -m rdfm_mgmt_client u')
    child_user.expect_exact('u > ')

    child_server.close()
    child_user.close()

    print('Default arguments test passed!')

def with_arguments():
    hostname = '0.0.0.0'
    port = '3333'
    child_server = pexpect.spawn(
        f'python3 -m rdfm_mgmt_server -hostname {hostname} -p {port}'
    )
    child_server.expect_exact(f'Listening for connections on {hostname}:{port}...')

    child_user = pexpect.spawn('python3 -m rdfm_mgmt_client u -p 2345')
    child_user.expect('ConnectionRefusedError: \[Errno 111\] Connection refused')

    child_user = pexpect.spawn(
        f'python3 -m rdfm_mgmt_client u -hostname {hostname} -p {port}'
    )
    child_user.expect_exact('u > ')

    child_server.close()
    child_user.close()

    print('Arguments test passed!')

default_arguments()
time.sleep(1)
with_arguments()