import ffmpeg
from pathlib import Path
from typing import Dict, List, Optional

from ..logger import logger


class VideoAnalyzer:
    """视频文件分析器，用于获取视频时长等信息"""
    
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
            probe = ffmpeg.probe(str(file_path))
            duration = float(probe['streams'][0]['duration'])
            return duration / 60.0  # 转换为分钟
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
            
            # 根据时长推测文件类型
            if file_info['duration']:
                if file_info['duration'] > 15:  # 大于15分钟认为是正片
                    file_info['estimated_type'] = 'regular'
                elif file_info['duration'] > 5:  # 5-15分钟可能是特典
                    file_info['estimated_type'] = 'special'
                else:  # 小于5分钟可能是PV/CM
                    file_info['estimated_type'] = 'preview'
            else:
                file_info['estimated_type'] = 'unknown'
            
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
            probe = ffmpeg.probe(str(file_path))
            
            video_stream = None
            audio_stream = None
            
            for stream in probe['streams']:
                if stream['codec_type'] == 'video' and video_stream is None:
                    video_stream = stream
                elif stream['codec_type'] == 'audio' and audio_stream is None:
                    audio_stream = stream
            
            info = {
                'filename': file_path.name,
                'path': str(file_path),
                'size': file_path.stat().st_size,
                'duration': float(probe['format']['duration']) / 60.0 if 'duration' in probe['format'] else None,
                'bitrate': int(probe['format']['bit_rate']) if 'bit_rate' in probe['format'] else None,
            }
            
            if video_stream:
                info.update({
                    'width': video_stream.get('width'),
                    'height': video_stream.get('height'),
                    'video_codec': video_stream.get('codec_name'),
                    'fps': eval(video_stream.get('r_frame_rate', '0/1'))
                })
            
            if audio_stream:
                info.update({
                    'audio_codec': audio_stream.get('codec_name'),
                    'audio_channels': audio_stream.get('channels'),
                    'sample_rate': audio_stream.get('sample_rate')
                })
            
            return info
            
        except Exception as e:
            logger.error(f'[视频分析] 获取 {file_path.name} 信息失败: {str(e)}')
            return None