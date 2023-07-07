#! /bin/bash

# Copyright 2023 Antmicro, based on Linaro Ltd's
# (https://gist.github.com/microbuilder/cf928ea5b751e6ea467cc0cd51d2532f#file-certg)
# License: Apache-2.0

# Arguments = server IP, certificate dirs
SERVER_IP=${1:-127.0.0.1}
CERTS_DIR=${2:-certs/}

HOSTNAME=IP.1:"$SERVER_IP"
#HOSTNAME=x
ORGNAME=Test
DIR="$CERTS_DIR"

# Generate a device ID.
# BSD's uuidgen outputs uppercase, so convert that here.
DEVID=$(uuidgen | tr '[:upper:]' '[:lower:]')

mkdir "$DIR"
cd "$DIR"

# Certificate Authority
# ---------------------

# Generate a root CA key (keep this safe!)
openssl ecparam -name prime256v1 -genkey -out CA.key

# Generate an X.509 certificate from CA.key assigning O and CN subject fields
# NOTE: CN should include a year or distinctive value to ensure a unique subj line
# ToDo: Set IsCA field to true
openssl req -new -x509 -days 3650 -key CA.key -out CA.crt \
    -subj "/O=$ORGNAME/CN=Root CA"

# Server Key/Cert
# ---------------

# Generate the server’s private key for TLS
openssl ecparam -name prime256v1 -genkey -out SERVER.key

# Generate a certificate signing request (CSR) for our key
openssl req -new -sha256 -key SERVER.key -out SERVER.csr \
    -subj "/O=$ORGNAME, LTD/CN=$HOSTNAME"

# Create a config snippet to add proper extensions to this key
# Be sure to set ‘DNS:’ to the server’s actual hostname!
echo "subjectKeyIdentifier=hash" > server.ext
echo "authorityKeyIdentifier=keyid,issuer" >> server.ext
echo "basicConstraints = critical, CA:FALSE" >> server.ext
echo "keyUsage = critical, digitalSignature" >> server.ext
echo "extendedKeyUsage = serverAuth" >> server.ext
echo "subjectAltName = $HOSTNAME" >> server.ext

# Process the server CSR and extensions
openssl x509 -req -sha256 \
    -CA CA.crt \
    -CAkey CA.key \
    -days 3560 \
    -CAcreateserial \
    -CAserial CA.srl \
    -in SERVER.csr \
    -out SERVER.crt \
    -extfile server.ext

# Clean up
rm server.ext
rm SERVER.csr

# Device Key/Cert
# ---------------

# Generate a private key for this device
openssl ecparam -name prime256v1 -genkey -out DEVICE.key

# Generate a CSR for this key
openssl req -new \
    -key DEVICE.key \
    -out DEVICE.csr \
    -subj "/O=$ORGNAME/CN=$DEVID/OU=Device Cert"

# Process the CSR using the CA cert/key
openssl x509 -req -sha256 \
    -CA CA.crt \
    -CAkey CA.key \
    -days 3560 \
    -in DEVICE.csr \
    -out DEVICE.crt

# Clean up
rm DEVICE.csr

# C Conversion
# ------------

# Convert the CA certificate to a text file
sed 's/.*/"&\\r\\n"/' CA.crt > ca_crt.txt

# Convert the device certificate to a text file
sed 's/.*/"&\\r\\n"/' DEVICE.crt > device_crt.txt

# Convert the device private key in DER format to a text file
openssl ec -in DEVICE.key -outform DER | xxd -i > device_key.txt
