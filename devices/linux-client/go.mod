module github.com/antmicro/rdfm

go 1.20

require (
	github.com/balena-os/librsync-go v0.8.5
	github.com/golang-jwt/jwt/v5 v5.2.1
	github.com/google/uuid v1.6.0
	github.com/gorilla/websocket v1.5.0
	github.com/mendersoftware/mender v0.0.0-20230726064531-bbe854cef242
	github.com/mendersoftware/mender-artifact v0.0.0-20230803130415-bb342f921a12
	github.com/pkg/errors v0.9.1
	github.com/sirupsen/logrus v1.9.3
	github.com/stretchr/testify v1.8.4
	github.com/thedevsaddam/gojsonq v2.3.0+incompatible
	github.com/urfave/cli/v2 v2.25.7
	golang.org/x/sync v0.1.0
)

require (
	github.com/balena-os/circbuf v0.1.3 // indirect
	github.com/bmatsuo/lmdb-go v1.8.0 // indirect
	github.com/cpuguy83/go-md2man/v2 v2.0.2 // indirect
	github.com/davecgh/go-spew v1.1.2-0.20180830191138-d8f796af33cc // indirect
	github.com/klauspost/compress v1.16.7 // indirect
	github.com/klauspost/cpuid/v2 v2.2.5 // indirect
	github.com/klauspost/pgzip v1.2.6 // indirect
	github.com/kr/pretty v0.3.1 // indirect
	github.com/mattn/go-isatty v0.0.19 // indirect
	github.com/mendersoftware/openssl v1.1.1-0.20221101131127-8797d18baf1a // indirect
	github.com/mendersoftware/progressbar v0.0.3 // indirect
	github.com/minio/sha256-simd v1.0.1 // indirect
	github.com/pmezard/go-difflib v1.0.0 // indirect
	github.com/remyoudompheng/go-liblzma v0.0.0-20190506200333-81bf2d431b96 // indirect
	github.com/russross/blackfriday/v2 v2.1.0 // indirect
	github.com/stretchr/objx v0.5.1 // indirect
	github.com/ungerik/go-sysfs v0.0.0-20210209091351-68e6f4d6bff9 // indirect
	github.com/xrash/smetrics v0.0.0-20201216005158-039620a65673 // indirect
	golang.org/x/crypto v0.12.0 // indirect
	golang.org/x/sys v0.11.0 // indirect
	gopkg.in/yaml.v3 v3.0.1 // indirect
)

replace github.com/mendersoftware/mender v0.0.0-20230726064531-bbe854cef242 => github.com/antmicro/mender v0.0.0-20240724071621-94b3886d04b6
