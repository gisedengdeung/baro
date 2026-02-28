from __future__ import annotations

import argparse
import asyncio
from typing import Optional

from loguru import logger

from edge.capture.camera import Camera
from edge.capture.serial_comm import SerialComm
from edge.cloud_client import CloudClient
from edge.config import EdgeConfig, load_config
from edge.control.buzzer import BuzzerController
from edge.control.conveyor import ConveyorController
from edge.decide.risk_evaluator import RiskEvaluator
from edge.decide.rule_engine import RuleEngine
from edge.detect.entrapment_detector import EntrapmentDetector
from edge.detect.fall_detector import FallDetector
from edge.detect.fire_detector import FireDetector
from edge.detect.person_detector import PersonDetector
from edge.detect.zone_checker import ZoneChecker
from edge.pipeline import SafetyPipeline
from edge.state import SystemStateManager
from edge.visualize.overlay_renderer import OverlayRenderer
from edge.webrtc.peer import WebRTCPeer



def _build_config_from_args() -> EdgeConfig:
    cfg = load_config()
    parser = argparse.ArgumentParser(description="Edge 안전 서버")
    parser.add_argument("--camera", type=int, default=cfg.camera_source)
    parser.add_argument("--serial", type=str, default=cfg.serial_port)
    parser.add_argument("--cloud-url", type=str, default=cfg.cloud_base_url)
    parser.add_argument("--edge-id", type=str, default=cfg.edge_id)
    args = parser.parse_args()

    return EdgeConfig(
        edge_id=args.edge_id,
        cloud_base_url=args.cloud_url,
        camera_source=args.camera,
        serial_port=args.serial,
        serial_baud_rate=cfg.serial_baud_rate,
        serial_mock_mode=cfg.serial_mock_mode,
        command_poll_interval=cfg.command_poll_interval,
        zone_poll_interval=cfg.zone_poll_interval,
        heartbeat_interval=cfg.heartbeat_interval,
        person_model_path=cfg.person_model_path,
        fall_model_path=cfg.fall_model_path,
        person_conf_threshold=cfg.person_conf_threshold,
        fall_conf_threshold=cfg.fall_conf_threshold,
        fire_ratio_threshold=cfg.fire_ratio_threshold,
        entrapment_frame_threshold=cfg.entrapment_frame_threshold,
        incident_cooldown_sec=cfg.incident_cooldown_sec,
        visual_overlay_enabled=cfg.visual_overlay_enabled,
        draw_zone_polygons=cfg.draw_zone_polygons,
        draw_label_confidence=cfg.draw_label_confidence,
    )


async def main() -> None:
    cfg = _build_config_from_args()
    logger.info(f"Edge 시작: edge_id={cfg.edge_id}, cloud={cfg.cloud_base_url}")

    camera = Camera(source=cfg.camera_source)
    serial = SerialComm(port=cfg.serial_port, baud_rate=cfg.serial_baud_rate, mock_mode=cfg.serial_mock_mode)

    state = SystemStateManager()
    cloud_client = CloudClient(
        base_url=cfg.cloud_base_url,
        edge_id=cfg.edge_id,
        command_poll_interval=cfg.command_poll_interval,
        zone_poll_interval=cfg.zone_poll_interval,
        heartbeat_interval=cfg.heartbeat_interval,
    )

    loop = asyncio.get_running_loop()

    def on_hardware_emergency(reason: str) -> None:
        state.lock_system(reason)
        loop.call_soon_threadsafe(
            lambda: asyncio.create_task(
                cloud_client.report_log(
                    {
                        "event_type": "LOG_CRITICAL_SENSOR",
                        "details": {"description": f"하드웨어 비상 신호 감지: {reason}"},
                        "log_risk_level": "CRITICAL",
                        "operation_mode": state.get_mode().value,
                    }
                )
            )
        )

    serial.set_lock_system_callback(on_hardware_emergency)
    serial.set_is_locked_checker(state.is_locked_status)
    serial.start_listening()

    person_detector = PersonDetector(model_path=cfg.person_model_path, conf_threshold=cfg.person_conf_threshold)
    fall_detector = FallDetector(model_path=cfg.fall_model_path, conf_threshold=cfg.fall_conf_threshold)
    fire_detector = FireDetector(ratio_threshold=cfg.fire_ratio_threshold)
    entrapment_detector = EntrapmentDetector(frame_threshold=cfg.entrapment_frame_threshold)
    zone_checker = ZoneChecker()

    risk_evaluator = RiskEvaluator()
    rule_engine = RuleEngine()

    conveyor = ConveyorController(serial=serial)
    buzzer = BuzzerController(serial=serial)

    webrtc_peer = WebRTCPeer(cloud_client=cloud_client, edge_id=cfg.edge_id)
    overlay_renderer = OverlayRenderer(
        enabled=cfg.visual_overlay_enabled,
        draw_zone_polygons=cfg.draw_zone_polygons,
        draw_label_confidence=cfg.draw_label_confidence,
    )

    pipeline = SafetyPipeline(
        camera=camera,
        person_detector=person_detector,
        fall_detector=fall_detector,
        fire_detector=fire_detector,
        entrapment_detector=entrapment_detector,
        zone_checker=zone_checker,
        risk_evaluator=risk_evaluator,
        rule_engine=rule_engine,
        conveyor=conveyor,
        buzzer=buzzer,
        state=state,
        cloud_client=cloud_client,
        webrtc_peer=webrtc_peer,
        overlay_renderer=overlay_renderer,
        incident_cooldown_sec=cfg.incident_cooldown_sec,
    )

    await cloud_client.start()
    await webrtc_peer.start()

    try:
        await pipeline.run()
    finally:
        pipeline.stop()
        await webrtc_peer.stop()
        await cloud_client.stop()
        serial.close()
        camera.release()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Edge 서버 종료")
