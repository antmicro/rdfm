module github.com/antmicro/rdfm

go 1.14

require (
	github.com/balena-os/librsync-go v0.8.5
	github.com/bmatsuo/lmdb-go v1.8.0 // indirect
	github.com/golang-jwt/jwt/v5 v5.2.1 // indirect
	github.com/gorilla/websocket v1.5.0
	github.com/klauspost/compress v1.16.7 // indirect
	github.com/klauspost/cpuid/v2 v2.2.5 // indirect
	github.com/klauspost/pgzip v1.2.6 // indirect
	github.com/mattn/go-isatty v0.0.19 // indirect
	github.com/mendersoftware/mender v0.0.0-20230726064531-bbe854cef242
	github.com/mendersoftware/mender-artifact v0.0.0-20230803130415-bb342f921a12
	github.com/minio/sha256-simd v1.0.1 // indirect
	github.com/pkg/errors v0.9.1
	github.com/sirupsen/logrus v1.9.3
	github.com/spf13/viper v1.16.0
	github.com/stretchr/objx v0.5.1 // indirect
	github.com/thedevsaddam/gojsonq v2.3.0+incompatible
	github.com/ungerik/go-sysfs v0.0.0-20210209091351-68e6f4d6bff9 // indirect
	github.com/urfave/cli/v2 v2.25.7
	golang.org/x/crypto v0.12.0 // indirect
)

replace github.com/mendersoftware/mender v0.0.0-20230726064531-bbe854cef242 => github.com/antmicro/mender v0.0.0-20240724071621-94b3886d04b6
