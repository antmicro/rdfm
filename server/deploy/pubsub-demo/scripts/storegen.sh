#!/usr/bin/env bash
# This script requires root of trust and root cert to alrady be generated (see server/tests/certgen.sh)
# For usage refer to README.md

set -e

while [[ $# -gt 0 ]]; do
	case $1 in
		-C|--cn)
			CN="$2"
			shift; shift
			;;
		-s|--san)
			SAN="$2"
			shift; shift
			;;
		-p|--password)
			PASS="$2"
			shift; shift
			;;
		-d|--destination)
			DEST="$2"
			shift; shift
			;;
		-c|--cacert)
			CACERT="$2"
			shift; shift
			;;
		-k|--cakey)
			CAKEY="$2"
			shift; shift
			;;
		-*|--*)
			echo "Unknown argument $1"
			exit 1
			;;
		*)
			shift # Discard positional argument
			;;
	esac
done

if [ -z "$CN" ]; then
	echo "Error: -C(--cn) argument is not set"
	exit 1
fi
if [ -z "$SAN" ]; then
	echo "Error: -s(--san) argument is not set"
	exit 1
fi
if [ -z "$PASS" ]; then
	echo "Error: -p(--password) argument is not set"
	exit 1
fi
if [ -z "$DEST" ]; then
	echo "Error: -d(--destiation) argument is not set"
	exit 1
fi
if [ -z "$CACERT" ]; then
	echo "Error: -c(--cacert) argument is not set"
	exit 1
fi
if [ ! -f "$CACERT" ]; then
	echo "Error: file $CACERT does not exist"
	exit 1
fi
if [ -z "$CAKEY" ]; then
	echo "Error: -k(--cakey) argument is not set"
	exit 1
fi
if [ ! -f "$CAKEY" ]; then
	echo "Error: file $CAKEY does not exist"
	exit 1
fi
if [ -e $DEST ]; then
	echo "Error: File \"$DEST\" already exists, remove it or change destination path to proceed"
	exit 1
fi

mkdir $DEST
cp $CACERT $DEST
cp $CAKEY $DEST
pushd $DEST

KEY=$(basename $CAKEY)
CERT=$(basename $CACERT)

echo "Generating a trust store from the certificate ${CERT}..."
keytool -trustcacerts -keystore TRUSTSTORE.p12 -alias CARoot -import -file ${CERT} -storetype PKCS12 \
	-noprompt -dname "O=Test, CN=Root CA" -storepass ${PASS} -keypass ${PASS}

echo "Generating keystore holding a key pair for a broker..."
keytool -genkeypair -alias localhost -keyalg EC -keystore KEYSTORE.p12 -storetype PKCS12 \
	-storepass ${PASS} -keypass ${PASS} -noprompt -dname "O=Test, CN=${CN}"

echo "Creating a certificate signing request for keystore..."
keytool -keystore KEYSTORE.p12 -alias localhost -certreq -file BROKER.csr -keypass ${PASS} -storepass ${PASS}

echo "Signing keystore certificate..."
echo "basicConstraints = critical, CA:FALSE" > BROKER.ext
echo "keyUsage = digitalSignature, keyEncipherment, dataEncipherment, keyAgreement" >> BROKER.ext
echo "subjectAltName = ${SAN}" >> BROKER.ext
echo "extendedKeyUsage = serverAuth, clientAuth" >> BROKER.ext
openssl x509 -req -CA ${CERT} -CAkey ${KEY} -in BROKER.csr -out BROKER.crt -days 3000 -extfile BROKER.ext

echo "Importing CA into keystore..."
keytool -keystore KEYSTORE.p12 -alias CARoot -import -file ${CERT} -keypass ${PASS} -storepass ${PASS} -noprompt \

echo "Import signed certificate into keystore..."
keytool -keystore KEYSTORE.p12 -alias localhost -import -file BROKER.crt -keypass ${PASS} -storepass ${PASS}

echo $PASS | tee truststore_creds keystore_creds key_creds >/dev/null
echo "Done"
popd
