import pexpect
import time
import os
import json

def parse_json_output(process: pexpect.spawn) -> dict:
    return json.loads("\n".join([l.decode() for l in process.readlines()]))

pexpect.run("server/tests/certgen.sh")
time.sleep(3)

print(os.listdir(os.path.join(os.getcwd(), "./devices/linux-client")))

child_server = pexpect.spawn('bash -c "python3 -m rdfm_mgmt_server --debug 2>&1 | tee list-server.log"')
child_server.expect_exact("Running on https://127.0.0.1:5000")

child_user = pexpect.spawn('bash -c "python3 -m rdfm_mgmt_client u 2>&1 | tee list-manager.log"')
child_user.expect_exact('Connected as u')

alert = ({
    "alert": {
        "devices": []
    },
    "method": "alert"
})

# check no devices visible
child_user.sendline("LIST")
time.sleep(3)
curl = pexpect.spawn('bash -c "curl https://127.0.0.1:5000/ --cacert ./certs/CA.crt -s 2>&1 | tee list-curl1.log"')
assert parse_json_output(curl) == alert
child_user.expect_exact('{"method":"alert","alert":{"devices":[]}}')
#print([l.decode() for l in curl.readlines()])

# check first device visible
child_device1 = pexpect.spawn('bash -c "./devices/linux-client/rdfm daemonize --name d1 --no-jwt-auth 2>&1 | tee list-device1.log"')
alert["alert"]["devices"].append("d1")

time.sleep(3)
child_user.sendline("LIST")
time.sleep(3)
curl = pexpect.spawn('bash -c "curl https://127.0.0.1:5000/ --cacert ./certs/CA.crt -s 2>&1 | tee list-curl2.log"')
assert parse_json_output(curl) == alert
child_user.expect_exact('{"method":"alert","alert":{"devices":["d1"]}}')

# check second device visible
child_device2 = pexpect.spawn('bash -c "./devices/linux-client/rdfm daemonize --name d2 --no-jwt-auth 2>&1 | tee list-device2.log"')
alert["alert"]["devices"].append("d2")
time.sleep(3)

child_user.sendline("LIST")
time.sleep(3)
curl = pexpect.spawn('bash -c "curl https://127.0.0.1:5000/ --cacert ./certs/CA.crt 2>&1 -s | tee list-curl3.log"')
child_user.expect_exact('{"method":"alert","alert":{"devices":["d1","d2"]}}')
assert parse_json_output(curl) == alert

# check second device disconnected and not visible
child_device2.close()
alert["alert"]["devices"].remove("d2")
time.sleep(3)

child_user.sendline("LIST")
time.sleep(3)
curl = pexpect.spawn('bash -c "curl https://127.0.0.1:5000/ --cacert ./certs/CA.crt 2>&1 -s | tee list-curl4.log"')
assert parse_json_output(curl) == alert
child_user.expect_exact('{"method":"alert","alert":{"devices":["d1"]}}')

print("List devices test passed!")
