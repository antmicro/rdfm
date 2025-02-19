#!/bin/bash
set -e

# This is the entrypoint for the Dockerized demo client
# This can be used to test basic integration with the RDFM server

# Environment variable overrides
SERVER_URL="${RDFM_CLIENT_SERVER_URL:-http://127.0.0.1:5000/}"
SERVER_CERT="${RDFM_CLIENT_SERVER_CERT:-/dev/zero}"
PART_A="${RDFM_CLIENT_PART_A:-/dev/zero}"
PART_B="${RDFM_CLIENT_PART_B:-/dev/zero}"
DEVICE_TYPE="${RDFM_CLIENT_DEVTYPE:-x86_64}"

# Generate a valid configuration
cat >/etc/rdfm/artifact_info << EOF
artifact_name=unknown
EOF

cat >/var/lib/rdfm/device_type << EOF
device_type=${DEVICE_TYPE}
EOF

cat >/etc/rdfm/rdfm.conf << EOF
{
    "RootfsPartA": "${PART_A}",
    "RootfsPartB": "${PART_B}"
}
EOF

cat >/var/lib/rdfm/rdfm.conf <<EOF
{
    "ServerURL": "${SERVER_URL}",
    "ServerCertificate": "${SERVER_CERT}"
}
EOF

cat >/var/lib/rdfm/actions.conf <<EOF
[
{
    "Id": "echo",
    "Name": "Echo",
    "Command": ["echo", "Executing echo action"],
    "Description": "Description of echo action",
    "Timeout": 1.0
},
{
    "Id": "sleepTwoSeconds",
    "Name": "Sleep 2",
    "Command": ["sleep", "2"],
    "Description": "Description of sleep 2 seconds action",
    "Timeout": 3.0
},
{
    "Id": "sleepFiveSeconds",
    "Name": "Sleep 5",
    "Command": ["sleep", "5"],
    "Description": "This action will timeout",
    "Timeout": 3.0
}
]
EOF

# Creating an entry in /etc/hosts for the server
IP=$(echo $SERVER_URL | awk -F"://|:" '{print $2}')
echo "$IP rdfm-server" >> /etc/hosts

# Start daemonized RDFM device client
exec rdfm daemonize ${CLIENT_ARGS}
