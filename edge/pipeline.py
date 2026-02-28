from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime
from typing import Any, Dict, List

import cv2
from loguru import logger

from edge.cloud_client import CloudClient
from edge.control.buzzer import BuzzerController
from edge.control.conveyor import ConveyorController
from edge.decide.risk_evaluator import RiskEvaluator
from edge.decide.rule_engine import RuleEngine
from edge.detect.entrapment_detector import EntrapmentDetector
from edge.detect.fall_detector import FallDetector
from edge.detect.fire_detector import FireDetector
from edge.detect.person_detector import PersonDetector
from edge.detect.zone_checker import ZoneChecker
from edge.state import SystemStateManager
from edge.visualize.overlay_renderer import OverlayRenderer
from edge.webrtc.peer import WebRTCPeer
from shared.enums import OperationMode, RiskLevel


class SafetyPipeline:
    def __init__(
        self,
        camera: Any,
        person_detector: PersonDetector,
        fall_detector: FallDetector,
        fire_detector: FireDetector,
        entrapment_detector: EntrapmentDetector,
        zone_checker: ZoneChecker,
        risk_evaluator: RiskEvaluator,
        rule_engine: RuleEngine,
        conveyor: ConveyorController,
        buzzer: BuzzerController,
        state: SystemStateManager,
        cloud_client: CloudClient,
        webrtc_peer: WebRTCPeer,
        overlay_renderer: OverlayRenderer | None = None,
        incident_cooldown_sec: float = 8.0,
    ) -> None:
        self.camera = camera
        self.person_detector = person_detector
        self.fall_detector = fall_detector
        self.fire_detector = fire_detector
        self.entrapment_detector = entrapment_detector
        self.zone_checker = zone_checker
        self.risk_evaluator = risk_evaluator
        self.rule_engine = rule_engine
        self.conveyor = conveyor
        self.buzzer = buzzer
        self.state = state
        self.cloud_client = cloud_client
        self.webrtc_peer = webrtc_peer
        self.overlay_renderer = overlay_renderer
        self.incident_cooldown_sec = max(1.0, incident_cooldown_sec)

        self._running = False
        self._was_locked = False
        self._last_incident_sent_at: Dict[str, float] = {}

    async def _handle_commands(self) -> None:
        commands = await self.cloud_client.get_pending_commands()
        for command in commands:
            cmd_type = command.get("command")
            if cmd_type == "START_AUTOMATIC":
                self.state.start_automatic_mode()
            elif cmd_type == "START_MAINTENANCE":
                self.state.start_maintenance_mode()
            elif cmd_type == "STOP":
                self.state.stop_system_globally()
            elif cmd_type == "RESET":
                self.state.reset_system()
                self.conveyor.power_off("System reset")
                self.buzzer.stop()
            elif cmd_type == "UPDATE_ZONES":
                self.state.set_zones(command.get("data", []))

        pulled_zones = self.cloud_client.get_latest_zones()
        if pulled_zones:
            self.state.set_zones(pulled_zones)

    @staticmethod
    def _compute_risk_level(risk_factors: List[Dict[str, Any]], mode: OperationMode) -> str:
        if any(f["type"] in {"POSTURE_FALLING", "SENSOR_ALERT", "FIRE_DETECTED", "ENTRAPMENT_DETECTED"} for f in risk_factors):
            return RiskLevel.CRITICAL.value
        if mode == OperationMode.MAINTENANCE and any(f["type"] == "ZONE_INTRUSION" for f in risk_factors):
            return RiskLevel.LOTO_RISK_DETECTED.value
        if any(f["type"] == "ZONE_INTRUSION" for f in risk_factors):
            return RiskLevel.WARNING.value
        if any(f["type"] == "POSTURE_CROUCHING" for f in risk_factors):
            return RiskLevel.NOTICE.value
        return RiskLevel.SAFE.value

    async def _send_log_from_action(
        self,
        action: Dict[str, Any],
        risk_factors: List[Dict[str, Any]],
        mode: OperationMode,
    ) -> None:
        action_type = action.get("type", "")
        if not action_type.startswith("LOG_"):
            return

        log_risk_level = "INFO"
        description = "System is operating normally."

        if any(f["type"] == "FIRE_DETECTED" for f in risk_factors):
            log_risk_level = "CRITICAL"
            description = "Possible fire has been detected in the monitored area."
        elif any(f["type"] == "ENTRAPMENT_DETECTED" for f in risk_factors):
            log_risk_level = "CRITICAL"
            description = "Possible entrapment risk detected while conveyor is running."
        elif any(f["type"] == "SENSOR_ALERT" for f in risk_factors):
            log_risk_level = "CRITICAL"
            sensor_type = next((f.get("sensor_type") for f in risk_factors if f["type"] == "SENSOR_ALERT"), "unknown")
            description = f"An emergency signal from sensor '{sensor_type}' has been detected."
        elif any(f["type"] == "POSTURE_FALLING" for f in risk_factors):
            log_risk_level = "CRITICAL"
            description = "A person falling has been detected."
        elif any(f["type"] == "ZONE_INTRUSION" for f in risk_factors):
            log_risk_level = "WARNING"
            details = next((f.get("details", []) for f in risk_factors if f["type"] == "ZONE_INTRUSION"), [])
            zone_names = ", ".join(sorted({item.get("zone_name", "unknown") for item in details}))
            description = f"Person detected in danger zone(s): {zone_names}."
        elif any(f["type"] == "POSTURE_CROUCHING" for f in risk_factors):
            log_risk_level = "NOTICE"
            description = "A person in a crouching pose has been detected."

        await self.cloud_client.report_log(
            {
                "event_type": action_type,
                "details": {"description": description},
                "log_risk_level": log_risk_level,
                "operation_mode": mode.value,
            }
        )

    async def _execute_actions(
        self,
        actions: List[Dict[str, Any]],
        risk_factors: List[Dict[str, Any]],
        mode: OperationMode,
    ) -> None:
        for action in actions:
            action_type = action.get("type")
            reason = action.get("details", {}).get("reason", "rule_engine")

            if action_type == "LOCK_SYSTEM":
                self.state.lock_system(reason)
                continue

            if action_type == "POWER_ON":
                self.conveyor.power_on(reason)
            elif action_type == "POWER_OFF":
                self.conveyor.power_off(reason)
            elif action_type == "REDUCE_SPEED_50":
                self.conveyor.set_speed(50, reason)
            elif action_type == "RESUME_FULL_SPEED":
                self.conveyor.set_speed(100, reason)
            elif action_type == "TRIGGER_ALARM_MEDIUM":
                self.buzzer.trigger_medium()
            elif action_type == "TRIGGER_ALARM_HIGH":
                self.buzzer.trigger_high()
            elif action_type == "TRIGGER_ALARM_CRITICAL":
                self.buzzer.trigger_critical()
            elif action_type == "STOP_ALARM":
                self.buzzer.stop()

            await self._send_log_from_action(action, risk_factors, mode)

    async def _maybe_publish_incident(
        self,
        incident_type: str,
        severity: str,
        zone_id: str | None,
        details: Dict[str, Any],
        frame: Any,
    ) -> None:
        now_mono = time.monotonic()
        last = self._last_incident_sent_at.get(incident_type, 0.0)
        if now_mono - last < self.incident_cooldown_sec:
            return

        incident_id = await self.cloud_client.create_incident(
            {
                "edge_id": self.cloud_client.edge_id,
                "incident_type": incident_type,
                "severity": severity,
                "zone_id": zone_id,
                "detected_at": datetime.now(UTC).isoformat(),
                "details": details,
            }
        )
        if not incident_id:
            return

        try:
            ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            if ok:
                await self.cloud_client.upload_incident_snapshot(incident_id, encoded.tobytes())
        except Exception as exc:
            logger.warning(f"incident 스냅샷 인코딩 실패(무시): {exc}")

        self._last_incident_sent_at[incident_type] = now_mono

    async def _maybe_publish_incidents(
        self,
        risk_factors: List[Dict[str, Any]],
        zone_alerts: List[Dict[str, Any]],
        frame: Any,
    ) -> None:
        if any(f["type"] == "FIRE_DETECTED" for f in risk_factors):
            fire_factor = next((f for f in risk_factors if f["type"] == "FIRE_DETECTED"), {})
            zone_id = zone_alerts[0]["zone_id"] if zone_alerts else None
            await self._maybe_publish_incident(
                incident_type="FIRE_DETECTED",
                severity="CRITICAL",
                zone_id=zone_id,
                details={
                    "description": "Possible fire detected by edge vision pipeline.",
                    "score": fire_factor.get("score", 0.0),
                },
                frame=frame,
            )

        if any(f["type"] == "ENTRAPMENT_DETECTED" for f in risk_factors):
            ent_factor = next((f for f in risk_factors if f["type"] == "ENTRAPMENT_DETECTED"), {})
            await self._maybe_publish_incident(
                incident_type="ENTRAPMENT_DETECTED",
                severity="CRITICAL",
                zone_id=ent_factor.get("zone_id"),
                details={
                    "description": "Possible entrapment risk detected while conveyor is running.",
                    "person_index": ent_factor.get("person_index"),
                    "score": ent_factor.get("score"),
                },
                frame=frame,
            )

        if any(f["type"] == "POSTURE_FALLING" for f in risk_factors):
            zone_id = zone_alerts[0]["zone_id"] if zone_alerts else None
            await self._maybe_publish_incident(
                incident_type="FALL_DETECTED",
                severity="CRITICAL",
                zone_id=zone_id,
                details={"description": "A person falling has been detected."},
                frame=frame,
            )

    async def run(self) -> None:
        self._running = True
        loop = asyncio.get_running_loop()
        target_fps = 15
        frame_interval = 1.0 / target_fps

        while self._running:
            try:
                frame_start = time.monotonic()
                await self._handle_commands()

                frame = await loop.run_in_executor(None, self.camera.read)
                if frame is None:
                    await asyncio.sleep(0.1)
                    continue

                is_locked_now = self.state.is_locked_status()
                if is_locked_now and not self._was_locked:
                    self.conveyor.power_off("System LOCKED")

                if not self.state.is_active():
                    if self.conveyor.get_status().get("conveyor_is_on"):
                        self.conveyor.power_off("System inactive")

                    heartbeat = {
                        **self.state.get_status(),
                        **self.conveyor.get_status(),
                        **self.buzzer.get_status(),
                        "risk_level": RiskLevel.SAFE.value,
                    }
                    await self.cloud_client.report_heartbeat(heartbeat)
                    display_frame = frame
                    if self.overlay_renderer is not None:
                        try:
                            display_frame = self.overlay_renderer.render(
                                frame=frame,
                                persons=[],
                                zones=self.state.zones,
                                zone_alerts=[],
                                risk_level=RiskLevel.SAFE.value,
                            )
                        except Exception as exc:
                            logger.warning(f"비활성 상태 오버레이 렌더 실패(원본 전송): {exc}")
                            display_frame = frame

                    self.webrtc_peer.send_frame(display_frame)
                    self._was_locked = is_locked_now
                    await asyncio.sleep(0.1)
                    continue

                conveyor_status = self.conveyor.get_status()
                conveyor_is_on = bool(conveyor_status.get("conveyor_is_on", False))

                persons = await loop.run_in_executor(None, self.person_detector.detect, frame)
                persons = await loop.run_in_executor(None, self.fall_detector.analyze, frame, persons)
                zone_alerts = self.zone_checker.check(persons, self.state.zones)
                fire_detection = await loop.run_in_executor(None, self.fire_detector.analyze, frame)
                entrapment_detection = self.entrapment_detector.analyze(
                    persons=persons,
                    zone_alerts=zone_alerts,
                    conveyor_is_on=conveyor_is_on,
                )

                detection_result = {
                    "persons": persons,
                    "danger_zone_alerts": zone_alerts,
                    "fire_detection": fire_detection,
                    "entrapment_detection": entrapment_detection,
                }

                risk_analysis = self.risk_evaluator.evaluate(
                    detection_result=detection_result,
                    sensor_data={"sensors": {}},
                    conveyor_status=conveyor_is_on,
                )
                risk_factors = risk_analysis.get("risk_factors", [])

                await self._maybe_publish_incidents(
                    risk_factors=risk_factors,
                    zone_alerts=zone_alerts,
                    frame=frame,
                )

                mode = self.state.get_mode()
                actions = self.rule_engine.decide_actions(
                    mode=mode.value,
                    risk_analysis=risk_analysis,
                    conveyor_is_on=conveyor_is_on,
                    current_speed_percent=int(conveyor_status.get("conveyor_speed", 0)),
                )

                await self._execute_actions(actions, risk_factors, mode)

                risk_level = self._compute_risk_level(risk_factors, mode)
                heartbeat = {
                    **self.state.get_status(),
                    **self.conveyor.get_status(),
                    **self.buzzer.get_status(),
                    "risk_level": risk_level,
                }
                await self.cloud_client.report_heartbeat(heartbeat)

                display_frame = frame
                if self.overlay_renderer is not None:
                    try:
                        display_frame = self.overlay_renderer.render(
                            frame=frame,
                            persons=persons,
                            zones=self.state.zones,
                            zone_alerts=zone_alerts,
                            risk_level=risk_level,
                        )
                    except Exception as exc:
                        logger.warning(f"오버레이 렌더 실패(원본 전송): {exc}")
                        display_frame = frame

                self.webrtc_peer.send_frame(display_frame)
                self._was_locked = is_locked_now
                elapsed = time.monotonic() - frame_start
                await asyncio.sleep(max(0.0, frame_interval - elapsed))
            except Exception as exc:
                logger.error(f"파이프라인 루프 예외: {exc}")
                await self.cloud_client.report_log(
                    {
                        "event_type": "LOG_SYSTEM_ERROR",
                        "details": {"message": str(exc)},
                        "log_risk_level": "ERROR",
                        "operation_mode": self.state.get_mode().value,
                    }
                )
                await asyncio.sleep(1.0)

    def stop(self) -> None:
        self._running = False
