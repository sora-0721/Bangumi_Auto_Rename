from pathlib import Path
from typing import Dict, List, Optional
from tinytag import TinyTag

from ..logger import logger


class VideoAnalyzer:
    """视频文件分析器，使用tinytag获取视频时长等信息"""
    
    @staticmethod
    def get_video_duration(file_path: Path) -> Optional[float]:
        """
        获取视频文件时长（分钟）
        
        Args:
            file_path: 视频文件路径
            
        Returns:
            视频时长（分钟），失败返回None
        """
        try:
            tag = TinyTag.get(str(file_path))
            if tag.duration:
                return tag.duration / 60.0  # 转换为分钟
            return None
        except Exception as e:
            logger.warning(f'[视频分析] 无法获取 {file_path.name} 的时长: {str(e)}')
            return None
    
    @staticmethod
    def analyze_video_files(file_paths: List[Path]) -> List[Dict]:
        """
        分析多个视频文件
        
        Args:
            file_paths: 视频文件路径列表
            
        Returns:
            包含文件信息的字典列表
        """
        results = []
        
        for file_path in file_paths:
            if not file_path.exists():
                continue
                
            file_info = {
                'filename': file_path.name,
                'path': str(file_path),
                'size': file_path.stat().st_size,
                'duration': VideoAnalyzer.get_video_duration(file_path)
            }
            
            results.append(file_info)
            
        logger.info(f'[视频分析] 分析了 {len(results)} 个视频文件')
        return results
    
    @staticmethod
    def get_video_info(file_path: Path) -> Optional[Dict]:
        """
        获取单个视频文件的详细信息
        
        Args:
            file_path: 视频文件路径
            
        Returns:
            视频信息字典
        """
        try:
            tag = TinyTag.get(str(file_path))
            
            info = {
                'filename': file_path.name,
                'path': str(file_path),
                'size': file_path.stat().st_size,
                'duration': tag.duration / 60.0 if tag.duration else None,
                'bitrate': tag.bitrate,
                'width': getattr(tag, 'width', None),
                'height': getattr(tag, 'height', None),
                'video_codec': getattr(tag, 'video_codec', None),
                'audio_codec': getattr(tag, 'audio_codec', None),
                'channels': getattr(tag, 'channels', None),
                'samplerate': getattr(tag, 'samplerate', None),
            }
            
            return info
            
        except Exception as e:
            logger.error(f'[视频分析] 获取 {file_path.name} 信息失败: {str(e)}')
            return None