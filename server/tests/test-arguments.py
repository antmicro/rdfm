import pexpect
import time

def default_arguments():    
    child_server = pexpect.spawn('bash -c "python3 -m rdfm_mgmt_server --no-api-auth 2>&1 | tee arg-def-server.log"')
    child_server.expect('Listening for connections on 127.0.0.1:1234...')

    child_user = pexpect.spawn('bash -c "python3 -m rdfm_mgmt_client u 2>&1 | tee arg-def-manager.log""')
    child_user.expect('u > ')

    child_server.close()
    child_user.close()

    print('Default arguments test passed!')

def with_arguments(hostname, port):    
    child_server = pexpect.spawn(f'bash -c "python3 -m rdfm_mgmt_server --debug --no-api-auth --hostname {hostname} --port {port} 2>&1 | tee arg-server.log"')
    child_server.expect(f'Listening for connections on {hostname}:{port}...')

    child_user = pexpect.spawn('bash -c "python3 -m rdfm_mgmt_client u 2>&1 | tee arg-manager-failing.log""')
    child_user.expect(pexpect.EOF)

    child_user = pexpect.spawn(f'bash -c "python3 -m rdfm_mgmt_client u --hostname {hostname} --port {port} 2>&1 | tee arg-manager-passing.log"')
    child_user.expect('u > ')

    child_server.close()
    child_user.close()

    print('Arguments test passed!')

time.sleep(3)
default_arguments()
pexpect.run("server/tests/certgen.sh 0.0.0.0")
time.sleep(3)
with_arguments('0.0.0.0', 3333)
