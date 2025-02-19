from typing import Optional
from device_mgmt.models.remote_device import RemoteDevice
from device_mgmt.models.reverse_shell import ReverseShell
from device_mgmt.models.action_execution import ActionExecution
from uuid import UUID


class RemoteDevices:
    """Container for tracking devices connected to the management WebSocket"""

    _remote_devices: dict[str, RemoteDevice] = {}

    def add(self, device: RemoteDevice):
        """Add a new device to the tracked devices"""
        self._remote_devices[device.token.device_id] = device

    def remove(self, device: RemoteDevice):
        """Remove a device from tracked devices"""
        self._remote_devices.pop(device.token.device_id)

    def get(self, mac_address: str) -> Optional[RemoteDevice]:
        """Get a device connection by MAC address"""
        return self._remote_devices.get(mac_address, None)


def _format_shell_key(mac_address: str, uuid: UUID) -> str:
    return f"{mac_address}_{uuid}"


class ShellSessions:
    """Container for tracking active shell sessions"""

    _shell_sessions: dict[str, ReverseShell] = {}

    def add(self, shell: ReverseShell):
        """Add a new shell session to the active shell session list"""
        self._shell_sessions[
            _format_shell_key(shell.mac_addr, shell.uuid)
        ] = shell

    def remove(self, shell: ReverseShell):
        """Remove the specified shell session"""
        self._shell_sessions.pop(_format_shell_key(shell.mac_addr, shell.uuid))

    def get(self, mac_address: str, uuid: UUID) -> Optional[ReverseShell]:
        """Get a shell session specified by the device MAC and UUID"""
        return self._shell_sessions.get(
            _format_shell_key(mac_address, uuid), None
        )


class ActionExecutions:
    """Container for tracking action executions"""

    _action_executions: dict[str, ActionExecution] = {}

    def add(self, execution: ActionExecution):
        """Add a new action execution."""
        self._action_executions[execution.execution_id] = execution

    def remove(self, execution: ActionExecution):
        """Remove the specified action execution."""
        self._action_executions.pop(execution.execution_id)

    def get(self, execution_id: str) -> Optional[ActionExecution]:
        """Get action execution by its identifier."""
        return self._action_executions.get(
            execution_id, None
        )
