"""
VideoIndexProcessor class for managing queues and background processing
"""
import logging
import threading
import queue
import time
import os
from typing import Optional
from .database import Database, ProcessingStatus, FrameStatus
from .video_index import VideoIndex
from .video_processor import VideoProcessor
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class VideoIndexProcessor:
    """
    Class to manage queues and process videos/images in the background
    """
    
    def __init__(self, num_workers: int = 2):
        """
        Initialize VideoIndexProcessor with queue and workers
        
        Args:
            num_workers: Number of worker threads to process items
        """
        self.task_queue = queue.Queue()
        self.num_workers = num_workers
        self.workers = []
        self.running = False
        self.video_index = VideoIndex()
        self.video_processor = VideoProcessor(video_index=self.video_index)
    
    def start(self):
        """Start the worker threads"""
        if self.running:
            logger.warning("Processor is already running")
            return
        
        self.running = True
        for i in range(self.num_workers):
            worker = threading.Thread(target=self._worker, daemon=True, name=f"Worker-{i+1}")
            worker.start()
            self.workers.append(worker)
            logger.info(f"Started worker thread: {worker.name}")
    
    def stop(self):
        """Stop the worker threads"""
        self.running = False
        # Add None to queue to signal workers to stop
        for _ in range(self.num_workers):
            self.task_queue.put(None)
        
        for worker in self.workers:
            worker.join(timeout=5)
        
        self.workers = []
        logger.info("Stopped all worker threads")
    
    def add_image_task(self, image_url: str, prompt: str = "What's in this image?", 
                      task_id: Optional[str] = None):
        """
        Add an image processing task to the queue
        
        Args:
            image_url: URL of image to process
            prompt: Prompt for LLM
            task_id: Optional task identifier
        """
        task = {
            "type": "image",
            "image_url": image_url,
            "prompt": prompt,
            "task_id": task_id or f"img_{int(time.time())}"
        }
        self.task_queue.put(task)
        logger.info(f"Added image task to queue: {task_id}")
    
    def add_video_task(self, video_id: str, video_url: str, granularity_seconds: float = 1.0,
                      prompt: str = "What's in this image?", model: str = "google/gemini-2.0-flash-001"):
        """
        Add a video processing task to the queue
        
        Args:
            video_id: Unique identifier for the video (UUID format)
            video_url: URL of video to process
            granularity_seconds: Interval between frames
            prompt: Prompt for LLM
            model: Model to use
        """
        task = {
            "type": "video",
            "video_id": video_id,
            "video_url": video_url,
            "granularity_seconds": granularity_seconds,
            "prompt": prompt,
            "model": model
        }
        self.task_queue.put(task)
        logger.info(f"Added video task to queue: {video_id}")
    
    def _worker(self):
        """Worker thread that processes tasks from the queue"""
        logger.info(f"Worker {threading.current_thread().name} started")
        
        while self.running:
            try:
                task = self.task_queue.get(timeout=1)
                
                # None is a signal to stop
                if task is None:
                    break
                
                if task["type"] == "image":
                    self._process_image_task(task)
                elif task["type"] == "video":
                    self._process_video_task(task)
                
                self.task_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in worker {threading.current_thread().name}: {str(e)}")
        
        logger.info(f"Worker {threading.current_thread().name} stopped")
    
    def _process_image_task(self, task: dict):
        """Process a single image task"""
        try:
            logger.info(f"Processing image task: {task.get('task_id')}")
            
            result = self.video_index.process_image_from_url(
                task["image_url"],
                task["prompt"]
            )
            
            logger.info(f"Image task completed: {task.get('task_id')}")
            return result
            
        except Exception as e:
            logger.error(f"Error processing image task: {str(e)}")
            raise
    
    def _process_video_task(self, task: dict):
        """Process a video task with database tracking"""
        db: Session = get_db_session()
        try:
            video_id = task["video_id"]
            logger.info(f"Processing video task: {video_id}")
            
            # Import Media and VideoProcessing
            from .database import Media, VideoProcessing
            
            # Get or create Media record
            media = db.query(Media).filter(Media.video_id == video_id).first()
            if not media:
                media = Media(
                    video_id=video_id,
                    video_url=task["video_url"],
                    media_type="video"
                )
                db.add(media)
                db.commit()
                db.refresh(media)
            
            # Get or create VideoProcessing record
            video_processing = db.query(VideoProcessing).filter(
                VideoProcessing.video_id == video_id
            ).first()
            if not video_processing:
                video_processing = VideoProcessing(
                    video_id=video_id,
                    status=ProcessingStatus.PROCESSING,
                    granularity_seconds=task["granularity_seconds"],
                    prompt=task["prompt"],
                    model=task["model"]
                )
                db.add(video_processing)
                db.commit()
                db.refresh(video_processing)
            
            # Keep Video for backward compatibility
            video = db.query(Video).filter(Video.video_id == video_id).first()
            if not video:
                video = Video(
                    video_id=video_id,
                    video_url=task["video_url"],
                    granularity_seconds=task["granularity_seconds"],
                    prompt=task["prompt"],
                    model=task["model"],
                    status=ProcessingStatus.PROCESSING
                )
                db.add(video)
                db.commit()
                db.refresh(video)
            
            # Update status
            video_processing.status = ProcessingStatus.PROCESSING
            video.status = ProcessingStatus.PROCESSING
            db.commit()
            
            self._log(db, video.id, None, "INFO", f"Starting video processing: {video_id}")
            
            # Download and split video
            video_path = self.video_processor.download_video(task["video_url"])
            frames = self.video_processor.split_video_by_granularity(
                video_path, 
                task["granularity_seconds"]
            )
            
            video_processing.total_frames = len(frames)
            Database.update_video_processing(video_id, total_frames=len(frames))
            
            Database.create_log(video_id, None, "INFO", f"Extracted {len(frames)} frames")
            
            # Create frame records
            frame_records = []
            for frame_num, timestamp, frame_bytes in frames:
                base64_image = self.video_processor.frame_bytes_to_base64(frame_bytes)
                frame_record = Frame(
                    video_id=video.id,
                    frame_number=frame_num,
                    timestamp_seconds=timestamp,
                    base64_image=base64_image,
                    status=FrameStatus.PENDING
                )
                frame_records.append((frame_record, base64_image))
                db.add(frame_record)
            
            db.commit()
            self._log(db, video.id, None, "INFO", f"Created {len(frame_records)} frame records")
            
            # Process each frame
            for frame_record, base64_image in frame_records:
                try:
                    frame_record.status = FrameStatus.PROCESSING
                    db.commit()
                    
                    self._log(db, video.id, frame_record.id, "INFO", 
                             f"Processing frame {frame_record.frame_number}")
                    
                    # Call LLM API
                    result = self.video_index.process_image_from_base64(
                        base64_image,
                        task["prompt"]
                    )
                    
                    frame_record.llm_response = result.get("response", "")
                    frame_record.status = FrameStatus.COMPLETED
                    video_processing.processed_frames += 1
                    video.processed_frames += 1
                    
                    self._log(db, video.id, frame_record.id, "INFO", 
                             f"Frame {frame_record.frame_number} processed successfully")
                    
                except Exception as e:
                    frame_record.status = FrameStatus.FAILED
                    frame_record.error_message = str(e)
                    video_processing.failed_frames += 1
                    video.failed_frames += 1
                    
                    self._log(db, video.id, frame_record.id, "ERROR", 
                             f"Frame {frame_record.frame_number} failed: {str(e)}")
                
                db.commit()
            
            # Update video status
            if video_processing.failed_frames == 0:
                video_processing.status = ProcessingStatus.COMPLETED
                video.status = ProcessingStatus.COMPLETED
            elif video_processing.processed_frames > 0:
                video_processing.status = ProcessingStatus.COMPLETED  # Partial success
                video.status = ProcessingStatus.COMPLETED  # Partial success
            else:
                video_processing.status = ProcessingStatus.FAILED
                video.status = ProcessingStatus.FAILED
            
            self._log(db, video.id, None, "INFO", 
                     f"Video processing completed: {video_processing.processed_frames}/{video_processing.total_frames} frames processed")
            
            db.commit()
            
            # Clean up video file
            if video_path and os.path.exists(video_path):
                try:
                    os.remove(video_path)
                except Exception as e:
                    logger.warning(f"Could not remove video file: {str(e)}")
            
        except Exception as e:
            logger.error(f"Error processing video task: {str(e)}")
            if 'video_id' in locals():
                Database.update_video_processing(video_id, 
                    status=ProcessingStatus.FAILED.value,
                    error_message=str(e)
                )
                Database.create_log(video_id, None, "ERROR", f"Video processing failed: {str(e)}")
        finally:
            db.close()
    
    def _log(self, db: Session, video_id: int, frame_id: Optional[int], 
            level: str, message: str):
        """Add a log entry to the database"""
        log_entry = ProcessingLog(
            video_id=video_id,
            frame_id=frame_id,
            log_level=level,
            message=message
        )
        db.add(log_entry)
        db.commit()
        logger.log(
            getattr(logging, level, logging.INFO),
            f"[Video {video_id}] {message}"
        )

