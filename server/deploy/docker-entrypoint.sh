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
if [ -n "${RDFM_DISABLE_API_AUTH}" ]; then
	server_args="${server_args} --no-api-auth"
fi

if [ ${encrypted} == 1 ]; then
	require_variable RDFM_SERVER_CERT
	require_variable RDFM_SERVER_KEY
	server_args="${server_args} --cert ${RDFM_SERVER_CERT}"
	server_args="${server_args} --key ${RDFM_SERVER_KEY}"
else
	server_args="${server_args} --no-ssl"
fi

require_variable RDFM_JWT_SECRET
export JWT_SECRET=${RDFM_JWT_SECRET}

require_variable RDFM_HOSTNAME
server_args="${server_args} --hostname ${RDFM_HOSTNAME}"

require_variable RDFM_API_PORT
server_args="${server_args} --http-port ${RDFM_API_PORT}"

require_variable RDFM_DB_CONNSTRING
server_args="${server_args} --database ${RDFM_DB_CONNSTRING}"

require_variable RDFM_LOCAL_PACKAGE_DIR
server_args="${server_args} --local-package-dir ${RDFM_LOCAL_PACKAGE_DIR}"

if [ ${_missing_variables} == 1 ]; then
	echo "Cannot start server, missing required environment variables"
	exit 1
fi

if [ -n "${RDFM_DISABLE_CORS}" ]; then
	server_args="${server_args} --disable-cors"
fi

if [ -n "${RDFM_INCLUDE_FRONTEND_ENDPOINT}" ]; then
	if [ ! -d /rdfm/frontend/dist ]; then
		echo "ERROR: Frontend files not found at frontend/dist. Make sure to build the frontend first."
		exit 1
	fi

	mkdir -p /rdfm/server/src/static
	cp -R /rdfm/frontend/dist /rdfm/server/src/static
	server_args="${server_args} --include-frontend"
fi

echo "Starting RDFM Management Server.."

wsgi_server="${RDFM_WSGI_SERVER:-gunicorn}"
if [ "${wsgi_server}" == "werkzeug" ]; then
	exec poetry run python -m rdfm_mgmt_server ${server_args}
elif [ "${wsgi_server}" == "gunicorn" ]; then
	exec poetry run gunicorn -k gevent 'rdfm_mgmt_server:setup_with_config_from_env()'
else
	echo "ERROR: Unsupported WSGI server: ${wsgi_server}"
	exit 1
fi
