from __future__ import annotations

import argparse
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

from loguru import logger

from edge.capture.camera import Camera
from edge.clip_recorder import EdgeClipRecorder
from edge.capture.serial_comm import SerialComm
from edge.cloud_client import CloudClient
from edge.config import EdgeConfig, load_config
from edge.control.buzzer import BuzzerController
from edge.control.conveyor import ConveyorController
from edge.decide.risk_evaluator import RiskEvaluator
from edge.decide.rule_engine import RuleEngine
from edge.detect.action_recognizer import ActionRecognizer
from edge.detect.keypoint_detector import KeypointDetector
from edge.detect.object_detector import ObjectDetector
from edge.detect.zone_checker import ZoneChecker
from edge.pipeline import SafetyPipeline
from edge.state import SystemStateManager
from edge.visualize.overlay_renderer import OverlayRenderer
from edge.webrtc.peer import WebRTCPeer

KST = ZoneInfo("Asia/Seoul")



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
        shared_secret=cfg.shared_secret,
        camera_source=args.camera,
        camera_width=cfg.camera_width,
        camera_height=cfg.camera_height,
        serial_port=args.serial,
        serial_baud_rate=cfg.serial_baud_rate,
        serial_mock_mode=cfg.serial_mock_mode,
        command_poll_interval=cfg.command_poll_interval,
        zone_poll_interval=cfg.zone_poll_interval,
        heartbeat_interval=cfg.heartbeat_interval,
        object_model_path=cfg.object_model_path,
        keypoint_model_path=cfg.keypoint_model_path,
        action_model_path=cfg.action_model_path,
        inference_device_request=cfg.inference_device_request,
        object_conf_threshold=cfg.object_conf_threshold,
        keypoint_conf_threshold=cfg.keypoint_conf_threshold,
        action_conf_threshold=cfg.action_conf_threshold,
        visual_overlay_enabled=cfg.visual_overlay_enabled,
        draw_zone_polygons=cfg.draw_zone_polygons,
        draw_label_confidence=cfg.draw_label_confidence,
        clip_pre_seconds=cfg.clip_pre_seconds,
        clip_post_seconds=cfg.clip_post_seconds,
        clip_target_fps=cfg.clip_target_fps,
        clip_width=cfg.clip_width,
        clip_height=cfg.clip_height,
        clip_output_dir=cfg.clip_output_dir,
        clip_min_trigger_level=cfg.clip_min_trigger_level,
    )


async def main() -> None:
    cfg = _build_config_from_args()
    logger.info(
        "Edge 시작: "
        f"edge_id={cfg.edge_id}, "
        f"cloud={cfg.cloud_base_url}, "
        f"inference_device_request={cfg.inference_device_request}"
    )

    camera = Camera(
        source=cfg.camera_source,
        width=cfg.camera_width,
        height=cfg.camera_height,
    )
    serial = SerialComm(port=cfg.serial_port, baud_rate=cfg.serial_baud_rate, mock_mode=cfg.serial_mock_mode)

    state = SystemStateManager()
    cloud_client = CloudClient(
        base_url=cfg.cloud_base_url,
        edge_id=cfg.edge_id,
        shared_secret=cfg.shared_secret,
        command_poll_interval=cfg.command_poll_interval,
        zone_poll_interval=cfg.zone_poll_interval,
        heartbeat_interval=cfg.heartbeat_interval,
    )
    clip_recorder = EdgeClipRecorder(
        cloud_client=cloud_client,
        edge_id=cfg.edge_id,
        output_dir=cfg.clip_output_dir,
        pre_seconds=cfg.clip_pre_seconds,
        post_seconds=cfg.clip_post_seconds,
        target_fps=cfg.clip_target_fps,
        width=cfg.clip_width,
        height=cfg.clip_height,
        min_trigger_level=cfg.clip_min_trigger_level,
    )

    loop = asyncio.get_running_loop()

    def on_hardware_emergency(reason: str) -> None:
        state.lock_system(reason)
        event_time = datetime.now(KST)

        async def _report_hardware_emergency() -> None:
            clip_uid = clip_recorder.trigger(event_time=event_time)
            await cloud_client.report_log(
                {
                    "event_type": "LOG_CRITICAL_SENSOR",
                    "details": {"description": f"하드웨어 비상 신호 감지: {reason}"},
                    "log_risk_level": "CRITICAL",
                    "operation_mode": state.get_mode().value,
                    "timestamp": event_time.isoformat(),
                    "event_uid": clip_uid,
                    "clip_status": "PENDING",
                }
            )

        loop.call_soon_threadsafe(lambda: asyncio.create_task(_report_hardware_emergency()))

    serial.set_lock_system_callback(on_hardware_emergency)
    serial.set_is_locked_checker(state.is_locked_status)
    serial.start_listening()

    object_detector = ObjectDetector(
        model_path=cfg.object_model_path,
        conf_threshold=cfg.object_conf_threshold,
        inference_device_request=cfg.inference_device_request,
    )
    keypoint_detector = KeypointDetector(
        model_path=cfg.keypoint_model_path,
        conf_threshold=cfg.keypoint_conf_threshold,
        inference_device_request=cfg.inference_device_request,
    )
    action_recognizer = ActionRecognizer(
        model_path=cfg.action_model_path,
        conf_threshold=cfg.action_conf_threshold,
        inference_device_request=cfg.inference_device_request,
    )
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
        object_detector=object_detector,
        keypoint_detector=keypoint_detector,
        action_recognizer=action_recognizer,
        zone_checker=zone_checker,
        risk_evaluator=risk_evaluator,
        rule_engine=rule_engine,
        conveyor=conveyor,
        buzzer=buzzer,
        state=state,
        cloud_client=cloud_client,
        webrtc_peer=webrtc_peer,
        overlay_renderer=overlay_renderer,
        clip_recorder=clip_recorder,
    )

    await cloud_client.start()
    await webrtc_peer.start()

    try:
        await pipeline.run()
    finally:
        pipeline.stop()
        await clip_recorder.shutdown()
        await webrtc_peer.stop()
        await cloud_client.stop()
        serial.close()
        camera.release()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Edge 서버 종료")
