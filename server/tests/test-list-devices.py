import pexpect
import time
import os
import json
import sys

def parse_json_output(process: pexpect.spawn) -> dict:
    return json.loads("\n".join([l.decode() for l in process.readlines()]))

pexpect.run("server/tests/certgen.sh")
time.sleep(3)

print(os.listdir(os.path.join(os.getcwd(), "./devices/linux-client")))

child_server = pexpect.spawn("python3 -m rdfm_mgmt_server")
child_server.expect("Listening for connections on 127.0.0.1:1234...")

child_user = pexpect.spawn("python3 -m rdfm_mgmt_client u")
child_user.expect('{"method":"alert","alert":{"message":"Connected as u"}}\r\nu >')

alert = ({
    "alert": {
        "devices": []
    },
    "method": "alert"
})

# check no devices visible
child_user.sendline("LIST")
curl = pexpect.spawn("curl https://127.0.0.1:5000/ --cacert ./certs/CA.crt")
assert parse_json_output(curl) == alert
child_user.expect_exact('{"method":"alert","alert":{"devices":[]}}\r\nu > ')
#print([l.decode() for l in curl.readlines()])

# check first device visible
child_device1 = pexpect.spawn("./devices/linux-client/rdfm daemonize --name d1")
alert["alert"]["devices"].append("d1")
time.sleep(3)

child_user.sendline("LIST")
curl = pexpect.spawn("curl https://127.0.0.1:5000/ --cacert ./certs/CA.crt")
print('Curl result:', curl.buffer, file=sys.stderr)
assert parse_json_output(curl) == alert
child_user.expect_exact('{"method":"alert","alert":{"devices":["d1"]}}\r\nu > ')

# check second device visible
child_device2 = pexpect.spawn("./devices/linux-client/rdfm daemonize --name d2")
alert["alert"]["devices"].append("d2")
time.sleep(3)

child_user.sendline("LIST")
curl = pexpect.spawn("curl https://127.0.0.1:5000/ --cacert ./certs/CA.crt")
child_user.expect_exact('{"method":"alert","alert":{"devices":["d1","d2"]}}\r\nu > ')
print('Curl result:', curl.buffer, file=sys.stderr)
assert parse_json_output(curl) == alert

# check second device disconnected and not visible
child_device2.close()
alert["alert"]["devices"].remove("d2")
time.sleep(3)

child_user.sendline("LIST")
curl = pexpect.spawn("curl https://127.0.0.1:5000/ --cacert ./certs/CA.crt")
print('Curl result:', curl)
assert parse_json_output(curl) == alert
child_user.expect_exact('{"method":"alert","alert":{"devices":["d1"]}}\r\nu > ')


print("List devices test passed!")
