package download

import (
	"errors"
	"fmt"
	"io"
	"net/http"
	"time"

	conf "github.com/antmicro/rdfm/devices/linux-client/conf"

	"github.com/mendersoftware/mender/client"
	log "github.com/sirupsen/logrus"
)

type RdfmHttpUpdateReader struct {
	offset    int64
	body      io.ReadCloser
	apiClient *client.ApiClient
	url       string
}

func (r *RdfmHttpUpdateReader) Read(p []byte) (n int, err error) {
	startOffset := r.offset
	n, err = r.body.Read(p)
	r.offset += int64(n)
	if err == nil || err == io.EOF {
		return n, err
	}

	rdfmConf, _, _ := conf.GetConfig()

	for i := 0; i < rdfmConf.ReconnectRetryCount; i++ {
		if r.body != nil {
			r.body.Close()
		}
		log.Errorf("Connection error - trying to resume")
		time.Sleep(time.Duration(rdfmConf.ReconnectRetryTime) * time.Second)
		response, supportsRangeRequests, err := setupHttpConnection(r.apiClient, r.url, r.offset)

		if err != nil {
			continue
		}

		if !supportsRangeRequests {
			return n, errors.New("Server doesn't support range requests - cannot resume connection")
		}

		r.body = response.Body

		n, err = r.body.Read(p[r.offset-startOffset:])
		r.offset += int64(n)
		if err == nil || err == io.EOF {
			break
		}
	}

	return int(r.offset - startOffset), nil
}

func (r *RdfmHttpUpdateReader) Close() error {
	return r.body.Close()
}

func NewRdfmHttpUpdateReader(url string, offset int64, clientConfig client.Config) (*RdfmHttpUpdateReader, int64, bool, error) {
	apiReq, _ := client.NewApiClient(clientConfig)

	response, supportsRangeRequests, err := setupHttpConnection(apiReq, url, offset)

	if err != nil {
		return nil, -1, false, err
	}

	return &RdfmHttpUpdateReader{
		offset:    offset,
		body:      response.Body,
		url:       url,
		apiClient: apiReq,
	}, response.ContentLength, supportsRangeRequests, nil
}

func setupHttpConnection(apiReq *client.ApiClient, url string, offset int64) (*http.Response, bool, error) {
	supportsRangeRequests := true
	req, err := client.MakeUpdateFetchRequest(url)
	if err != nil {
		return nil, false, err
	}
	req.Header.Add("Range", fmt.Sprintf("bytes=%d-", offset))
	response, err := apiReq.Do(req)

	if err != nil {
		return nil, false, err
	}

	if ret := response.Header.Get("Accept-Ranges"); ret == "" || ret == "none" {
		supportsRangeRequests = false
	}

	if (response.StatusCode != http.StatusOK &&
		response.StatusCode != http.StatusPartialContent) ||
		(response.ContentLength < 0) {

		response.Body.Close()
		return nil, false, errors.New("Incorrect HTTP response")
	}

	return response, supportsRangeRequests, nil
}
