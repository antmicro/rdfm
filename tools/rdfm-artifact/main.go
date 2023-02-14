package main

import (
	"fmt"
	"os"

	"github.com/mendersoftware/mender-artifact/artifact"
	"github.com/mendersoftware/mender-artifact/awriter"
	"github.com/mendersoftware/mender-artifact/handlers"
)

func main() {
	f, err := os.OpenFile("testArtifact.rdfm", os.O_CREATE|os.O_RDWR, 0666)
	if err != nil {
		fmt.Println("File open failed")
		os.Exit(1)
	}

	writer := awriter.NewWriter(f, artifact.NewCompressorNone())
	x := getWriteArtifactArgs()
	err = writer.WriteArtifact(x)
	if err != nil {
		fmt.Println("Artifact creation failed!")
		fmt.Println(err)
		os.Exit(1)
	}

	//  Subcommands to add:
	//    +++ 	write rootfsimage
	//	  +++ 	write deltarootfsimage
	//    ++ 	read (dump info)
	//	  ++ 	dump (dump artifact contents for modification)
	//	  + 	validate
	//    + 	sign
	//	  + 	modify
	//    +		cp
	//    + 	cat
	//    + 	install
	//    + 	rm
}

func getWriteArtifactArgs() *awriter.WriteArtifactArgs {
	artifactTypeInfo := new(string)
	*artifactTypeInfo = "foo"

	x1 := NewDeltaComposer(handlers.NewRootfsV3("update.img"))
	x := &awriter.WriteArtifactArgs{
		Format:  "rdfm",
		Version: 3,
		Devices: []string{"dummy_device"},
		Name:    "dummy_artifact",
		Updates: &awriter.Updates{
			Updates: []handlers.Composer{&x1},
		},
		Scripts: &artifact.Scripts{},
		Depends: &artifact.ArtifactDepends{
			ArtifactName:      []string{"depends_artifact_name"},
			CompatibleDevices: []string{"depends_compatible_devices"},
			ArtifactGroup:     []string{"depends_artifact_group"},
		},
		Provides: &artifact.ArtifactProvides{
			ArtifactName:  "dummy_artifact",
			ArtifactGroup: "dummy_group",
		},
		TypeInfoV3: &artifact.TypeInfoV3{
			Type:            artifactTypeInfo,
			ArtifactDepends: map[string]interface{}{},
			ArtifactProvides: map[string]string{
				"rootfs-image.checksum": "foobarbaz",
				"rootfs-image.version":  "abcdef",
			},
			ClearsArtifactProvides: []string{},
		},
	}
	return x
}
