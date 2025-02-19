import time
from typing import Optional
from device_mgmt.models.action_execution import ActionExecution
from rdfm.ws import RDFM_WS_INVALID_REQUEST, WebSocketException
from request_models import Action, ActionExec, ActionListQuery
import server

import queue

QUEUE_RETRY_DELAY = 5
"""Delay between attempts at queueing action execution."""

QUEUE_RESPONSE_TIMEOUT = 30
"""Timeout for the action execute request."""

ACTION_UPDATE_TIMEOUT = 30
"""Timeout for the action list update request."""

EXECUTION_TOTAL_TIMEOUT = 3600 * 2
"""Maximum wait time for action execution."""


def execute_action(mac_address: str, action_id: str) -> Optional[tuple[int, str]]:
    if not (remote_device := server.instance.remote_devices.get(mac_address)):
        msg = f"Device '{mac_address}' not connected to the management WS."
        raise WebSocketException(msg, RDFM_WS_INVALID_REQUEST)

    ensure_actions(mac_address)

    if not (action := remote_device.actions.get(action_id)):
        msg = f"Action '{action_id}' doesn't exist for device '{mac_address}'."
        raise WebSocketException(msg, RDFM_WS_INVALID_REQUEST)

    execution = ActionExecution(action)
    server.instance.action_executions.add(execution)

    try:
        print(
            f"Attempting to queue execution '{execution.execution_id}' "
            f"for device '{mac_address}'...",
            flush=True,
        )
        while True:
            remote_device.send_message(
                ActionExec(action_id=action.action_id, execution_id=execution.execution_id)
            )

            try:
                control_msg = execution.execution_control.get(timeout=QUEUE_RESPONSE_TIMEOUT)
                if control_msg == "ok":
                    print(f"Queued execution '{execution.execution_id}'.", flush=True)
                    break
                elif control_msg == "full":
                    print(
                        f"Failed to queue execution '{execution.execution_id}'. "
                        f"Retrying in {QUEUE_RETRY_DELAY}s seconds...",
                        flush=True,
                    )
                    time.sleep(QUEUE_RETRY_DELAY)
                else:
                    msg = f"Unknown control message: '{control_msg}'."
                    raise WebSocketException(msg, RDFM_WS_INVALID_REQUEST)
            except queue.Empty:
                msg = (
                    f"Client failed to respond to execution "
                    f"{execution.execution_id} in {QUEUE_RESPONSE_TIMEOUT}s."
                )
                raise WebSocketException(msg, RDFM_WS_INVALID_REQUEST)

        execution.execution_queued.set()

        if not execution.execution_completed.wait(EXECUTION_TOTAL_TIMEOUT):
            msg = (
                f"Execution '{execution.execution_id}' "
                f"timed-out after {EXECUTION_TOTAL_TIMEOUT}s."
            )
            raise WebSocketException(msg, RDFM_WS_INVALID_REQUEST)

        if execution.status_code is None:
            msg = f"Status code was not set for execution '{execution.execution_id}'."
            raise WebSocketException(msg, RDFM_WS_INVALID_REQUEST)

        return execution.status_code, execution.output

    finally:
        server.instance.action_executions.remove(execution)


def execute_action_result(execution_id: str, status_code: int, output: str):
    if not (execution := server.instance.action_executions.get(execution_id)):
        msg = f"Invalid execution {execution_id}"
        raise WebSocketException(msg, RDFM_WS_INVALID_REQUEST)

    # TODO: possible race condition if the device malfunctions
    # and sends multiple action execution results

    execution.status_code = status_code
    execution.output = output

    execution.execution_completed.set()


def execute_action_control(execution_id: str, status: str):
    if not (execution := server.instance.action_executions.get(execution_id)):
        msg = f"Invalid execution {execution_id}"
        raise WebSocketException(msg, RDFM_WS_INVALID_REQUEST)

    execution.execution_control.put(status)


def ensure_actions(mac_address: str) -> list[Action]:
    if not (remote_device := server.instance.remote_devices.get(mac_address)):
        msg = f"Device '{mac_address}' not connected to the management WS."
        raise WebSocketException(msg, RDFM_WS_INVALID_REQUEST)

    if not remote_device.actions_updated.is_set():
        try:
            remote_device.actions_updated.clear()
            remote_device.send_message(
                ActionListQuery()
            )

            if not remote_device.actions_updated.wait(ACTION_UPDATE_TIMEOUT):
                msg = f"Action list for '{mac_address} timed-out in {ACTION_UPDATE_TIMEOUT}s.'"
                raise WebSocketException(msg, RDFM_WS_INVALID_REQUEST)
        finally:
            pass

    return list(remote_device.actions.values())
