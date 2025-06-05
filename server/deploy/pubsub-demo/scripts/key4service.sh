#!/usr/bin/env bash

set -e

while [[ $# -gt 0 ]]; do
	case $1 in
		-c|--cn)
			CN="$2"
			shift; shift
			;;
		-s|--san)
			SAN="$2"
			shift; shift
			;;
		-crt|--cacert)
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
	echo "Error: -c(--cn) argument is not set"
	exit 1
fi

if [ -z "$SAN" ]; then
	echo "Error: -s(--san) argument is not set"
	exit 1
fi

if [ -z "$CACERT" ]; then
	echo "Error: -c(--cert) argument is not set"
	exit 1
fi

if [ ! -f "$CACERT" ]; then
	echo "Error: $CACERT doesn't exist."
	exit 1
fi

if [ -z "$CAKEY" ]; then
	echo "Error: -k(--key) argument is not set"
	exit 1
fi

if [ ! -f "$CAKEY" ]; then
	echo "Error: $CAKEY doesn't exist."
	exit 1
fi

# Generate private key for TLS for $CN
openssl ecparam -name prime256v1 -genkey -out $CN.key

# Generate certificate signing request
openssl req -new -sha256 -key $CN.key -out $CN.csr -subj "/O=Test Company/CN=$CN"

# Sign cert
echo "basicConstraints = critical, CA:FALSE" > $CN.ext
echo "keyUsage = digitalSignature, keyEncipherment, dataEncipherment, keyAgreement" >> $CN.ext
echo "subjectAltName = $SAN" >> $CN.ext # Change this to be the IP of your admin client
echo "extendedKeyUsage = serverAuth, clientAuth" >> $CN.ext
openssl x509 -req -sha256 \
        -CA $CACERT \
        -CAkey $CAKEY \
        -days 3000 \
        -in $CN.csr \
        -out $CN.crt \
        -extfile $CN.ext
rm $CN.csr
rm $CN.ext
echo "Done"
