import pexpect
import time

def default_arguments():    
    pexpect.run("tests/certgen.sh")
    time.sleep(3)
    
    child_server = pexpect.spawn('python3 -m rdfm_mgmt_server')
    child_server.expect_exact('Listening for connections on 127.0.0.1:1234...')

    child_user = pexpect.spawn('python3 -m rdfm_mgmt_client u')
    child_user.expect_exact('u > ')

    child_server.close()
    child_user.close()

    print('Default arguments test passed!')

def with_arguments(hostname, port):    
    child_server = pexpect.spawn(f'python3 -m rdfm_mgmt_server -hostname {hostname} -p {port}')
    child_server.expect_exact(f'Listening for connections on {hostname}:{port}...')

    child_user = pexpect.spawn('python3 -m rdfm_mgmt_client u')
    child_user.expect_exact(pexpect.EOF)

    child_user = pexpect.spawn(f'python3 -m rdfm_mgmt_client u -hostname {hostname} -p {port}')
    child_user.expect_exact('u > ')

    child_server.close()
    child_user.close()

    print('Arguments test passed!')

pexpect.run("tests/certgen.sh")
time.sleep(3)
default_arguments()
pexpect.run("tests/certgen.sh 0.0.0.0")
time.sleep(3)
with_arguments('0.0.0.0', 3333)
