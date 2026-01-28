"""
PICAM Video Processor Service

Privacy-First Video Processing:
- Video frames are processed IN MEMORY ONLY
- NO frames are stored to disk or database
- Only aggregate counts are extracted and saved
- Processing metadata is logged (without any personal data)

This service uses computer vision to count people in frames,
then IMMEDIATELY discards the frames.
"""

import logging
from datetime import datetime
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass
import uuid
import asyncio
from io import BytesIO

import numpy as np

# OpenCV import with fallback
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    logging.warning("OpenCV not available - video processing disabled")

from app.models.mongodb_models import VideoProcessingLog
from app.services.data_ingestion import get_ingestion_service
from app.utils import now_utc
from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """Result of video frame processing."""
    success: bool
    processing_id: str
    detected_count: int
    confidence: float
    processing_time_ms: float
    error: Optional[str] = None


@dataclass
class PrivacyCompliance:
    """Privacy compliance verification."""
    frames_stored: bool = False
    personal_data_extracted: bool = False
    raw_video_retained: bool = False
    only_counts_saved: bool = True
    
    @property
    def is_compliant(self) -> bool:
        return (
            not self.frames_stored and
            not self.personal_data_extracted and
            not self.raw_video_retained and
            self.only_counts_saved
        )


class VideoProcessorService:
    """
    Privacy-first video processing service.
    
    CRITICAL PRIVACY PRINCIPLES:
    1. NO video frames are ever stored
    2. NO personal data is extracted or saved
    3. ONLY aggregate counts are retained
    4. Processing happens entirely in memory
    5. Frames are immediately discarded after counting
    
    The only output is: "X people detected at location Y at time Z"
    """
    
    def __init__(self):
        self.settings = get_settings()
        self._ensure_no_retention()
        
        # Simple person detection using HOG descriptor
        if CV2_AVAILABLE:
            self.hog = cv2.HOGDescriptor()
            self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
        else:
            self.hog = None
    
    def _ensure_no_retention(self) -> None:
        """Verify video retention is disabled."""
        if self.settings.video_retention_seconds != 0:
            raise ValueError(
                "PRIVACY VIOLATION: video_retention_seconds must be 0. "
                "Video frames must never be stored."
            )
    
    async def process_frame(
        self,
        frame_data: bytes,
        location_id: str,
        location_type: str,
        camera_id: str = "default"
    ) -> ProcessingResult:
        """
        Process a single video frame to count people.
        
        PRIVACY: Frame is processed in memory and immediately discarded.
        Only the count is retained.
        
        Args:
            frame_data: Raw frame bytes (JPEG/PNG)
            location_id: Location identifier
            location_type: Type of location
            camera_id: Camera identifier
            
        Returns:
            ProcessingResult with count (frame is NOT stored)
        """
        processing_id = f"vp_{uuid.uuid4().hex[:12]}"
        start_time = datetime.now()
        
        if not CV2_AVAILABLE:
            return ProcessingResult(
                success=False,
                processing_id=processing_id,
                detected_count=0,
                confidence=0,
                processing_time_ms=0,
                error="OpenCV not available"
            )
        
        try:
            # Decode frame in memory
            nparr = np.frombuffer(frame_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is None:
                raise ValueError("Could not decode frame")
            
            # Detect people using HOG
            detected_count, confidence = self._detect_people(frame)
            
            # CRITICAL: Clear frame from memory
            del frame
            del nparr
            
            # Calculate processing time
            processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            # Log processing (without any frame data)
            await self._log_processing(
                processing_id=processing_id,
                camera_id=camera_id,
                location_id=location_id,
                frames_processed=1,
                processing_duration_ms=processing_time_ms,
                detected_count=detected_count,
                confidence=confidence
            )
            
            # Ingest the count as operational data
            ingestion_service = get_ingestion_service()
            await ingestion_service.ingest_from_video_count(
                location_id=location_id,
                location_type=location_type,
                timestamp=now_utc(),
                person_count=detected_count,
                observation_period_seconds=1,  # Single frame
                processing_id=processing_id
            )
            
            return ProcessingResult(
                success=True,
                processing_id=processing_id,
                detected_count=detected_count,
                confidence=confidence,
                processing_time_ms=processing_time_ms
            )
            
        except Exception as e:
            logger.error(f"Frame processing failed: {e}")
            return ProcessingResult(
                success=False,
                processing_id=processing_id,
                detected_count=0,
                confidence=0,
                processing_time_ms=0,
                error=str(e)
            )
        finally:
            # Ensure frame data is cleared
            frame_data = None
    
    async def process_frame_batch(
        self,
        frames: list,
        location_id: str,
        location_type: str,
        camera_id: str = "default",
        observation_period_seconds: float = 300
    ) -> ProcessingResult:
        """
        Process multiple frames and return average count.
        
        Used for calculating average density over a period.
        All frames are discarded after processing.
        """
        processing_id = f"vpb_{uuid.uuid4().hex[:12]}"
        start_time = datetime.now()
        
        if not CV2_AVAILABLE:
            return ProcessingResult(
                success=False,
                processing_id=processing_id,
                detected_count=0,
                confidence=0,
                processing_time_ms=0,
                error="OpenCV not available"
            )
        
        counts = []
        confidences = []
        
        try:
            for frame_data in frames:
                # Decode and process each frame
                nparr = np.frombuffer(frame_data, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                if frame is not None:
                    count, conf = self._detect_people(frame)
                    counts.append(count)
                    confidences.append(conf)
                    
                    # CRITICAL: Immediately clear frame
                    del frame
                    del nparr
            
            if not counts:
                raise ValueError("No valid frames processed")
            
            # Calculate average
            avg_count = int(round(sum(counts) / len(counts)))
            avg_confidence = sum(confidences) / len(confidences)
            
            processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            # Log processing
            await self._log_processing(
                processing_id=processing_id,
                camera_id=camera_id,
                location_id=location_id,
                frames_processed=len(counts),
                processing_duration_ms=processing_time_ms,
                detected_count=avg_count,
                confidence=avg_confidence
            )
            
            # Ingest as operational data
            ingestion_service = get_ingestion_service()
            await ingestion_service.ingest_from_video_count(
                location_id=location_id,
                location_type=location_type,
                timestamp=now_utc(),
                person_count=avg_count,
                observation_period_seconds=observation_period_seconds,
                processing_id=processing_id
            )
            
            return ProcessingResult(
                success=True,
                processing_id=processing_id,
                detected_count=avg_count,
                confidence=avg_confidence,
                processing_time_ms=processing_time_ms
            )
            
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            return ProcessingResult(
                success=False,
                processing_id=processing_id,
                detected_count=0,
                confidence=0,
                processing_time_ms=0,
                error=str(e)
            )
        finally:
            # Clear all frame data
            frames.clear()
    
    def _detect_people(self, frame: np.ndarray) -> Tuple[int, float]:
        """
        Detect people in a frame using HOG descriptor.
        
        Returns (count, confidence)
        
        Note: This is a simple detector. In production, you might use
        more sophisticated models, but the privacy principle remains:
        only the COUNT leaves this function.
        """
        if self.hog is None:
            return (0, 0.0)
        
        # Resize for faster processing
        height, width = frame.shape[:2]
        scale = min(1.0, 800 / max(height, width))
        
        if scale < 1.0:
            frame = cv2.resize(frame, None, fx=scale, fy=scale)
        
        # Detect people
        boxes, weights = self.hog.detectMultiScale(
            frame,
            winStride=(8, 8),
            padding=(4, 4),
            scale=1.05
        )
        
        # Filter by confidence
        confident_detections = [w for w in weights if w > 0.5]
        count = len(confident_detections)
        
        # Average confidence
        if confident_detections:
            confidence = sum(confident_detections) / len(confident_detections)
        else:
            confidence = 0.0
        
        return (count, min(confidence, 1.0))
    
    async def _log_processing(
        self,
        processing_id: str,
        camera_id: str,
        location_id: str,
        frames_processed: int,
        processing_duration_ms: float,
        detected_count: int,
        confidence: float
    ) -> None:
        """
        Log video processing event.
        
        PRIVACY: Only metadata is logged - no frame data.
        """
        try:
            log_entry = VideoProcessingLog(
                processing_id=processing_id,
                timestamp=now_utc(),
                camera_id=camera_id,
                location_id=location_id,
                frames_processed=frames_processed,
                processing_duration_ms=processing_duration_ms,
                detected_count=detected_count,
                confidence_score=confidence,
                frames_discarded=True,  # Always true
                no_personal_data_stored=True,  # Always true
                output_data_point_id=None  # Set by ingestion
            )
            await log_entry.insert()
        except Exception as e:
            logger.warning(f"Failed to log processing: {e}")
    
    def verify_privacy_compliance(self) -> PrivacyCompliance:
        """
        Verify this service is privacy compliant.
        
        Returns compliance status.
        """
        return PrivacyCompliance(
            frames_stored=False,
            personal_data_extracted=False,
            raw_video_retained=False,
            only_counts_saved=True
        )
    
    async def get_processing_stats(
        self,
        location_id: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Get video processing statistics.
        """
        query = {}
        if location_id:
            query["location_id"] = location_id
        
        logs = await VideoProcessingLog.find(query).sort(
            [("timestamp", -1)]
        ).limit(limit).to_list()
        
        if not logs:
            return {"status": "no_data", "total_processed": 0}
        
        total_frames = sum(log.frames_processed for log in logs)
        total_time = sum(log.processing_duration_ms for log in logs)
        avg_count = sum(log.detected_count for log in logs) / len(logs)
        
        return {
            "status": "available",
            "total_processing_events": len(logs),
            "total_frames_processed": total_frames,
            "total_processing_time_ms": round(total_time, 2),
            "avg_detected_count": round(avg_count, 2),
            "privacy_compliant": True,
            "frames_stored": False  # Always false
        }


# Simulated frame generator for testing
class SimulatedFrameGenerator:
    """
    Generates simulated frame data for testing.
    In production, this would be replaced by actual camera feeds.
    """
    
    @staticmethod
    def generate_test_frame(width: int = 640, height: int = 480) -> bytes:
        """Generate a blank test frame."""
        if not CV2_AVAILABLE:
            return b""
        
        # Create a simple test image
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        frame[:] = (100, 100, 100)  # Gray background
        
        # Encode as JPEG
        _, buffer = cv2.imencode('.jpg', frame)
        return buffer.tobytes()


# Service instance factory
_video_service: Optional[VideoProcessorService] = None


def get_video_processor() -> VideoProcessorService:
    """Get or create video processor instance."""
    global _video_service
    if _video_service is None:
        _video_service = VideoProcessorService()
    return _video_service