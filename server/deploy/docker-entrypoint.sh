#!/bin/bash
set +e

# Print all of the missing variables at once instead of one-by-one
_missing_variables=0
require_variable()
{
	VARNAME="$1"
	if [ -z "${!VARNAME}" ]; then
		echo "Required environment variable missing: '${VARNAME}'"
		_missing_variables=1
	fi
}

server_args=""
encrypted=1
if [ -n "${RDFM_DISABLE_ENCRYPTION}" ]; then
	encrypted=0
fi

if [ ${encrypted} == 1 ]; then
	require_variable RDFM_SERVER_CERT
	require_variable RDFM_SERVER_KEY
	server_args="${server_args} -cert ${RDFM_SERVER_CERT}"
	server_args="${server_args} -key ${RDFM_SERVER_KEY}"
else
	server_args="${server_args} -no_ssl"
fi

require_variable RDFM_JWT_SECRET
export JWT_SECRET=${RDFM_JWT_SECRET}

require_variable RDFM_HOSTNAME
server_args="${server_args} -hostname ${RDFM_HOSTNAME}"

require_variable RDFM_API_PORT
server_args="${server_args} -http_port ${RDFM_API_PORT}"

require_variable RDFM_DEVICE_PORT
server_args="${server_args} -port ${RDFM_DEVICE_PORT}"

require_variable RDFM_DB_CONNSTRING
server_args="${server_args} -database ${RDFM_DB_CONNSTRING}"

require_variable RDFM_LOCAL_PACKAGE_DIR
server_args="${server_args} -local_package_dir ${RDFM_LOCAL_PACKAGE_DIR}"

if [ ${_missing_variables} == 1 ]; then
	echo "Cannot start server, missing required environment variables"
	exit 1
fi

echo "Starting RDFM Management Server.."
exec poetry run \
	python -m rdfm_mgmt_server ${server_args}
