package api

type DeviceMetadata struct {
	DeviceType      string `json:"rdfm.hardware.devtype"`
	SoftwareVersion string `json:"rdfm.software.version"`
	MacAddress      string `json:"rdfm.hardware.macaddr"`
}

type AuthorizeReq struct {
	Metadata  DeviceMetadata `json:"metadata"`
	PublicKey string         `json:"public_key"`
	Timestamp int64          `json:"timestamp"`
}

type AuthorizeRes struct {
	Expires int64  `json:"expires"`
	Token   string `json:"token"`
}

type UpdateCheckReq struct {
	DeviceMetadata
}

type UpdateCheckRes struct {
	Id      int64  `json:"id"`
	Created string `json:"created"`
	Sha256  string `json:"sha256"`
	Uri     string `json:"uri"`
}
