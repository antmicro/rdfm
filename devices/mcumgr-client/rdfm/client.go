package rdfm

import (
	"bytes"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"rdfm-mcumgr-client/mcumgr"
	"strings"
	"time"
)

const rdfmAuthorizationHeader = "X-RDFM-Device-Signature"

type RdfmClient struct {
	client  *http.Client
	baseUrl *url.URL

	token string
}

func InitClient(rdfmHostname string) (*RdfmClient, error) {
	baseUrl, err := url.Parse(rdfmHostname)
	if err != nil {
		return nil, errors.New(fmt.Sprintf("Failed to parse server hostname (err: %s)", err))
	}

	return &RdfmClient{
		baseUrl: baseUrl,
		client:  http.DefaultClient,
	}, nil
}

func (rc *RdfmClient) AuthorizeDevice(d *mcumgr.Device) (bool, error) {
	reqBody := AuthorizeReq{
		Metadata: DeviceMetadata{
			DeviceType:      d.Config.DevType,
			SoftwareVersion: d.PrimaryImage.Version,
			MacAddress:      d.Config.Id,
		},
		PublicKey: d.Key.PubKeyPEM(),
		Timestamp: time.Now().Unix(),
	}

	reqJson, err := json.Marshal(reqBody)
	if err != nil {
		return false, errors.New(fmt.Sprintf("Failed to encode request body"))
	}

	rc.token = ""
	req, err := rc.newRdfmRequest(http.MethodPost, "/api/v1/auth/device", reqJson)
	if err != nil {
		return false, errors.New("Failed to create new request")
	}

	signature, err := d.Key.SignPayload(reqJson)
	if err != nil {
		return false, errors.New("Failed to sign message")
	}
	req.Header.Add(rdfmAuthorizationHeader, base64.StdEncoding.EncodeToString(signature))

	resp, err := rc.client.Do(req)
	if err != nil {
		return false, errors.New("Failed to send authorization request")
	}
	defer resp.Body.Close()

	switch resp.StatusCode {
	case 200:
		var authResp AuthorizeRes
		decoder := json.NewDecoder(resp.Body)

		if err := decoder.Decode(&authResp); err != nil {
			return false, errors.New("Failed to decode response body")
		}

		rc.token = fmt.Sprintf("Bearer token=%s", authResp.Token)
		return true, nil
	case 401:
		return false, nil
	default:
		return false, errors.New(fmt.Sprintf("Unknown error (%s)", resp.Status))
	}
}

func (rc *RdfmClient) UpdateCheck(d *mcumgr.Device) (*UpdateCheckRes, error) {
	isAuth, err := rc.AuthorizeDevice(d)
	if err != nil {
		return nil, err
	}
	if !isAuth {
		return nil, errors.New("Server did not authorize this device")
	}

	reqBody := UpdateCheckReq{
		DeviceMetadata{
			DeviceType:      d.Config.DevType,
			SoftwareVersion: d.PrimaryImage.Version,
			MacAddress:      d.Config.Id,
		},
	}

	reqJson, err := json.Marshal(reqBody)
	if err != nil {
		return nil, errors.New(fmt.Sprintf("Failed to encode request body"))
	}

	req, err := rc.newRdfmRequest(http.MethodPost, "/api/v1/update/check", reqJson)

	resp, err := rc.client.Do(req)
	if err != nil {
		return nil, errors.New("Failed to send update check request")
	}
	defer resp.Body.Close()

	switch resp.StatusCode {
	case 200:
		var ucRes UpdateCheckRes
		decoder := json.NewDecoder(resp.Body)

		if err := decoder.Decode(&ucRes); err != nil {
			return nil, errors.New("Failed to decode response body")
		}

		return &ucRes, nil
	case 204:
		return nil, nil
	case 400:
		return nil, errors.New("Missing device metadata")
	case 401:
		return nil, errors.New("Device unauthorized")
	default:
		return nil, errors.New(fmt.Sprintf("Unknown error (%s)", resp.Status))
	}
}

func (rc *RdfmClient) FetchUpdateArtifact(update *UpdateCheckRes) ([]byte, error) {
	resp, err := rc.client.Get(update.Uri)
	if err != nil {
		return nil, errors.New("Failed to send fetch update request")
	}
	defer resp.Body.Close()

	artBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	artHash := sha256.Sum256(artBytes)
	if strings.ToLower(update.Sha256) != hex.EncodeToString(artHash[:]) {
		return nil, errors.New("Artifact data malformed - checksum of fetched artifact does not match one returned by server")
	}

	return artBytes, nil
}

func (rc *RdfmClient) newRdfmRequest(method, path string, body []byte) (*http.Request, error) {
	req, err := http.NewRequest(method, rc.baseUrl.JoinPath(path).String(), bytes.NewBuffer(body))
	if err != nil {
		return nil, err
	}

	req.Header.Add("Accept", "application/json")
	req.Header.Add("Content-Type", "application/json")

	if len(rc.token) > 0 {
		req.Header.Add("Authorization", rc.token)
	}

	return req, nil
}
