package handlers

import (
	"encoding/json"
	"log"

	"github.com/pkg/errors"

	"github.com/mendersoftware/mender-artifact/areader"
	"github.com/mendersoftware/mender-artifact/handlers"

	"github.com/mendersoftware/mender/datastore"
	"github.com/mendersoftware/mender/installer"
	"github.com/mendersoftware/mender/store"
	"github.com/mendersoftware/mender/utils"
)

type Handler struct {
	ar *areader.Reader
}

const (
	errMsgDependencyNotSatisfiedF = "Artifact dependency %q not satisfied by currently installed artifact (%v != %v)."
	errMsgInvalidDependsTypeF     = "invalid type %T for dependency with name %s"
)

var AvailableHandlers = map[string]func() handlers.Installer{
	"single-file": NewSingleFileUpdater,
}

func RestoreHandlersFromStore(inst *installer.AllModules, store store.Store, payloadTypes []string) ([]installer.PayloadUpdatePerformer, error) {
	var installers []installer.PayloadUpdatePerformer
	for _, payType := range payloadTypes {
		if payType == "rootfs-image" {
			if inst.DualRootfs != nil {
				rootfsHandler, ok := inst.DualRootfs.(installer.PayloadUpdatePerformer)
				if ok {
					installers = append(installers, rootfsHandler)
				}
				continue
			}
		}
		factory, ok := AvailableHandlers[payType]
		if !ok {
			continue
		}
		installHandler := factory()
		stateSaver, ok := installHandler.(StateSaver)
		if ok {
			stateSaver.RestoreState(store)
		}
		payloadUpdatePerformer, ok := installHandler.(installer.PayloadUpdatePerformer)
		if ok {
			installers = append(installers, payloadUpdatePerformer)
		}
	}
	return installers, nil
}

func NewHandler(ar *areader.Reader) *Handler {
	return &Handler{ar}
}

func (h *Handler) StorePayloads() error {
	return h.ar.ReadArtifactData()
}

func (h *Handler) VerifyDependencies(provides map[string]string) error {
	depends, err := h.GetArtifactDepends()
	if err != nil {
		return err
	}

	for key, depend := range depends {
		if key == "device_type" {
			// handled elsewhere
			continue
		}
		if p, ok := provides[key]; ok {
			switch pVal := depend.(type) {
			case []interface{}:
				if ok, err := utils.ElemInSlice(depend, p); ok {
					continue
				} else if err == utils.ErrInvalidType {
					return errors.Errorf(
						errMsgInvalidDependsTypeF,
						depend,
						key,
					)
				}
			case []string:
				// No need to check type here - all deterministic
				if ok, _ := utils.ElemInSlice(depend, p); ok {
					continue
				}
			case string:
				if p == pVal {
					continue
				}
			default:
				return errors.Errorf(
					errMsgInvalidDependsTypeF,
					depend,
					key,
				)
			}
			return errors.Errorf(errMsgDependencyNotSatisfiedF,
				key, depend, provides[key])
		}
		return errors.Errorf(errMsgDependencyNotSatisfiedF,
			key, depend, nil)
	}
	return nil
}

func (h *Handler) InstallUpdate() error {
	for _, inst := range h.getInstallerList() {
		err := inst.InstallUpdate()
		if err != nil {
			return err
		}
	}
	return nil
}

func (h *Handler) GetArtifactName() string {
	return h.ar.GetArtifactName()
}

// Returns a list of compatible devices
func (h *Handler) GetCompatibleDevices() []string {
	return h.ar.GetCompatibleDevices()
}

// Returns the merged artifact provides header-info and type-info fields
// for artifact version >= 3. Returns nil if version < 3
func (h *Handler) GetArtifactProvides() (map[string]string, error) {
	return h.ar.MergeArtifactProvides()
}

// Returns the merged artifact depends header-info and type-info fields
// for artifact version >= 3. Returns nil if version < 3
func (h *Handler) GetArtifactDepends() (map[string]interface{}, error) {
	return h.ar.MergeArtifactDepends()
}

// Returns all `clears_artifact_depends` fields from all payloads.
func (h *Handler) GetArtifactClearsProvides() []string {
	return h.ar.MergeArtifactClearsProvides()
}

func (h *Handler) GetUpdateStorers() ([]handlers.UpdateStorer, error) {
	return h.ar.GetUpdateStorers()
}

func (h *Handler) SaveUpdateToStore(store store.Store) error {
	installers := h.getInstallerList()
	list := make([]string, len(installers))
	for c := range installers {
		cSaver, ok := installers[c].(StateSaver)
		if ok {
			cSaver.SaveState(store)
		}

		list[c] = installers[c].GetType()
	}
	artifactTypeInfoProvides, err := h.GetArtifactProvides()
	if err != nil {
		return err
	}

	log.Printf("Name: %s\n", h.GetArtifactName())
	stateData := datastore.StandaloneStateData{
		Version:                  datastore.StandaloneStateDataVersion,
		ArtifactName:             h.GetArtifactName(),
		ArtifactTypeInfoProvides: artifactTypeInfoProvides,
		ArtifactClearsProvides:   h.GetArtifactClearsProvides(),
		PayloadTypes:             list,
	}
	data, err := json.Marshal(stateData)
	if err != nil {
		return err
	}

	return store.WriteAll(datastore.StandaloneStateKey, data)
}

func (h *Handler) IsRollbackSupported() bool {
	for _, inst := range h.getInstallerList() {
		if ok, _ := inst.SupportsRollback(); ok {
			return true
		}
	}
	return false
}

func (h *Handler) IsRebootNeeded() bool {
	for _, inst := range h.getInstallerList() {
		if ok, _ := inst.NeedsReboot(); ok == installer.RebootRequired {
			return true
		}
	}
	return false
}

func (h *Handler) Rollback() error {
	for _, inst := range h.getInstallerList() {
		if ok, _ := inst.SupportsRollback(); ok {
			err := inst.Rollback()
			if err != nil {
				return err
			}
		}
	}
	return nil
}

func (h *Handler) Commit() error {
	for _, inst := range h.getInstallerList() {
		err := inst.CommitUpdate()
		if err != nil {
			return err
		}
	}
	return nil
}

func (h *Handler) Cleanup() error {
	for _, inst := range h.getInstallerList() {
		err := inst.Cleanup()
		if err != nil {
			return err
		}
	}
	return nil
}

// Func from Mender
func (h *Handler) getInstallerList() []installer.PayloadUpdatePerformer {
	updateStorers, _ := h.GetUpdateStorers()
	var list []installer.PayloadUpdatePerformer
	for _, us := range updateStorers {
		installer, ok := us.(installer.PayloadUpdatePerformer)
		if !ok {
			// If the installer does not implement PayloadUpdatePerformer interface, it means that
			// it is an Artifact with no payload (for instance, bootstrap Artifact). Just skip.
			continue
		}
		list = append(list, installer)
	}

	return list
}
