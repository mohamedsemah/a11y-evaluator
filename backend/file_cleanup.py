"""
File cleanup job for managing temporary session files
Automatically removes expired session directories and files
"""
import asyncio
import logging
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import os

from config import get_settings
from database import delete_expired_sessions, SessionLocal, AnalysisSession

logger = logging.getLogger(__name__)
settings = get_settings()


class FileCleanupJob:
    """Background job for cleaning up temporary files and expired sessions"""
    
    def __init__(
        self,
        temp_sessions_dir: str = None,
        cleanup_interval_seconds: int = 3600,  # 1 hour
        session_expiry_hours: int = 24,
        max_file_age_hours: int = 48
    ):
        self.temp_sessions_dir = Path(temp_sessions_dir or settings.TEMP_SESSIONS_DIR)
        self.cleanup_interval_seconds = cleanup_interval_seconds
        self.session_expiry_hours = session_expiry_hours
        self.max_file_age_hours = max_file_age_hours
        self.running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the cleanup job"""
        if self.running:
            logger.warning("Cleanup job is already running")
            return
        
        self.running = True
        logger.info(f"Starting file cleanup job (interval: {self.cleanup_interval_seconds}s)")
        
        # Run initial cleanup
        await self.cleanup()
        
        # Schedule periodic cleanup
        self._task = asyncio.create_task(self._run_periodic())
    
    async def stop(self):
        """Stop the cleanup job"""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("File cleanup job stopped")
    
    async def _run_periodic(self):
        """Run cleanup periodically"""
        while self.running:
            try:
                await asyncio.sleep(self.cleanup_interval_seconds)
                if self.running:
                    await self.cleanup()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {str(e)}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def cleanup(self) -> Dict[str, Any]:
        """
        Perform cleanup of expired sessions and temporary files
        
        Returns:
            Dictionary with cleanup statistics
        """
        stats = {
            "sessions_deleted": 0,
            "files_deleted": 0,
            "directories_removed": 0,
            "space_freed_bytes": 0,
            "start_time": datetime.utcnow().isoformat(),
            "errors": []
        }
        
        try:
            logger.info("Starting file cleanup...")
            
            # 1. Delete expired sessions from database
            try:
                deleted_count = delete_expired_sessions()
                stats["sessions_deleted"] = deleted_count
                logger.info(f"Deleted {deleted_count} expired sessions from database")
            except Exception as e:
                error_msg = f"Failed to delete expired sessions: {str(e)}"
                logger.error(error_msg)
                stats["errors"].append(error_msg)
            
            # 2. Clean up session directories
            if self.temp_sessions_dir.exists():
                session_dirs = [d for d in self.temp_sessions_dir.iterdir() if d.is_dir()]
                
                for session_dir in session_dirs:
                    try:
                        # Check if session exists in database
                        session_id = session_dir.name
                        db = SessionLocal()
                        try:
                            session = db.query(AnalysisSession).filter(
                                AnalysisSession.id == session_id
                            ).first()
                            
                            if session is None:
                                # Session doesn't exist in DB, check age
                                if self._is_directory_old(session_dir):
                                    space_freed = self._get_directory_size(session_dir)
                                    shutil.rmtree(session_dir)
                                    stats["directories_removed"] += 1
                                    stats["space_freed_bytes"] += space_freed
                                    logger.info(f"Removed orphaned session directory: {session_dir}")
                            elif session.expires_at < datetime.utcnow():
                                # Session expired, remove directory
                                space_freed = self._get_directory_size(session_dir)
                                shutil.rmtree(session_dir)
                                stats["directories_removed"] += 1
                                stats["space_freed_bytes"] += space_freed
                                logger.info(f"Removed expired session directory: {session_dir}")
                        finally:
                            db.close()
                    
                    except Exception as e:
                        error_msg = f"Failed to process session directory {session_dir}: {str(e)}"
                        logger.error(error_msg)
                        stats["errors"].append(error_msg)
            
            # 3. Clean up orphaned files in temp directory
            if self.temp_sessions_dir.exists():
                for item in self.temp_sessions_dir.iterdir():
                    if item.is_file():
                        try:
                            if self._is_file_old(item):
                                file_size = item.stat().st_size
                                item.unlink()
                                stats["files_deleted"] += 1
                                stats["space_freed_bytes"] += file_size
                                logger.info(f"Removed orphaned file: {item}")
                        except Exception as e:
                            error_msg = f"Failed to remove file {item}: {str(e)}"
                            logger.error(error_msg)
                            stats["errors"].append(error_msg)
            
            stats["end_time"] = datetime.utcnow().isoformat()
            stats["space_freed_mb"] = stats["space_freed_bytes"] / (1024 * 1024)
            
            logger.info(
                f"Cleanup completed: {stats['sessions_deleted']} sessions, "
                f"{stats['directories_removed']} directories, "
                f"{stats['files_deleted']} files, "
                f"{stats['space_freed_mb']:.2f} MB freed"
            )
            
            return stats
        
        except Exception as e:
            error_msg = f"Cleanup job failed: {str(e)}"
            logger.error(error_msg)
            stats["errors"].append(error_msg)
            return stats
    
    def _is_directory_old(self, directory: Path) -> bool:
        """Check if directory is older than max_file_age_hours"""
        try:
            mtime = datetime.fromtimestamp(directory.stat().st_mtime)
            age_hours = (datetime.utcnow() - mtime).total_seconds() / 3600
            return age_hours > self.max_file_age_hours
        except Exception:
            return False
    
    def _is_file_old(self, file_path: Path) -> bool:
        """Check if file is older than max_file_age_hours"""
        try:
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            age_hours = (datetime.utcnow() - mtime).total_seconds() / 3600
            return age_hours > self.max_file_age_hours
        except Exception:
            return False
    
    def _get_directory_size(self, directory: Path) -> int:
        """Calculate total size of directory in bytes"""
        total_size = 0
        try:
            for item in directory.rglob("*"):
                if item.is_file():
                    total_size += item.stat().st_size
        except Exception as e:
            logger.warning(f"Failed to calculate directory size for {directory}: {str(e)}")
        return total_size


# Global cleanup job instance
cleanup_job: Optional[FileCleanupJob] = None


def get_cleanup_job() -> FileCleanupJob:
    """Get or create the global cleanup job instance"""
    global cleanup_job
    if cleanup_job is None:
        cleanup_job = FileCleanupJob()
    return cleanup_job

