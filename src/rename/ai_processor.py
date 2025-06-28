from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..logger import logger
from ..ai.client import AIClient
from ..ai.video_analyzer import VideoAnalyzer
from ..ai.models import AIAnalysisResult
from .utils import VIDEO_SUFFIX


class AIProcessor:
    """AI辅助处理器，用于智能分析和重命名"""
    
    def __init__(self):
        self.ai_client = AIClient()
        self.video_analyzer = VideoAnalyzer()
    
    def analyze_anime_files(
        self,
        path: Path,
        anime_info: Dict,
        season_info: Optional[Dict] = None
    ) -> Optional[AIAnalysisResult]:
        """
        使用AI分析动漫文件的映射关系
        
        Args:
            path: 本地文件路径
            anime_info: TMDB动漫信息
            season_info: 特定季度信息
            
        Returns:
            验证后的AI分析结果
        """
        if not self.ai_client.is_available():
            logger.info('[AI处理] AI功能未启用，跳过AI分析')
            return None
        
        # 收集视频文件
        video_files = self._collect_video_files(path)
        if not video_files:
            logger.warning('[AI处理] 未找到视频文件')
            return None
        
        # 分析视频文件
        file_analysis = self.video_analyzer.analyze_video_files(video_files)
        
        # 使用AI分析映射关系
        ai_result = self.ai_client.analyze_episode_mapping(
            anime_info, file_analysis, season_info
        )
        
        if ai_result:
            logger.info(f'[AI处理] AI分析完成，置信度: {ai_result.confidence:.2f}')
            
            # 记录低置信度结果到单独日志
            if ai_result.confidence < self.ai_client.confidence_threshold:
                self._log_low_confidence_result(path, ai_result)
        
        return ai_result
    
    def apply_ai_mapping(
        self,
        ai_result: AIAnalysisResult,
        work_path: Path,
        original_mapping: Dict[Path, Path]
    ) -> Dict[Path, Path]:
        """
        应用AI分析结果到文件映射
        
        Args:
            ai_result: 验证后的AI分析结果
            work_path: 工作目录路径
            original_mapping: 原始文件映射
            
        Returns:
            更新后的文件映射
        """
        if not ai_result or not ai_result.mapping:
            return original_mapping
        
        updated_mapping = original_mapping.copy()
        
        try:
            # 记录季度映射信息
            if ai_result.season_mapping:
                logger.info(f'[AI处理] 季度映射: {ai_result.season_mapping}')
            
            for mapping in ai_result.mapping:
                local_file = mapping.local_file
                tmdb_season = mapping.tmdb_season
                tmdb_episode = mapping.tmdb_episode
                episode_type = mapping.episode_type
                confidence = mapping.confidence
                
                # 找到对应的本地文件
                source_path = None
                for path in original_mapping.keys():
                    if local_file in path.name:
                        source_path = path
                        break
                
                if not source_path:
                    logger.warning(f'[AI处理] 未找到本地文件: {local_file}')
                    continue
                
                # 根据类型确定目标目录
                if episode_type == 'special' or episode_type == 'ova':
                    target_dir = work_path / 'Season0'
                elif episode_type == 'movie':
                    target_dir = work_path / 'Movies'
                else:
                    target_dir = work_path / f'Season{tmdb_season}'
                
                target_dir.mkdir(parents=True, exist_ok=True)
                
                # 生成新的文件名
                if episode_type in ['special', 'ova']:
                    new_filename = f'S00E{tmdb_episode:02d} - {source_path.name}'
                elif episode_type == 'movie':
                    new_filename = source_path.name
                else:
                    new_filename = f'S{tmdb_season:02d}E{tmdb_episode:02d} - {source_path.name}'
                
                updated_mapping[source_path] = target_dir / new_filename
                
                logger.info(
                    f'[AI处理] AI映射: {source_path.name} -> {new_filename} '
                    f'(类型: {episode_type}, 置信度: {confidence:.2f})'
                )
        
        except Exception as e:
            logger.error(f'[AI处理] 应用AI映射失败: {str(e)}')
            return original_mapping
        
        return updated_mapping
    
    def _collect_video_files(self, path: Path) -> List[Path]:
        """收集指定路径下的所有视频文件"""
        video_files = []
        
        if path.is_file():
            if path.suffix.lower() in VIDEO_SUFFIX:
                video_files.append(path)
        else:
            for item in path.rglob('*'):
                if item.is_file() and item.suffix.lower() in VIDEO_SUFFIX:
                    video_files.append(item)
        
        return sorted(video_files)
    
    def _log_low_confidence_result(self, path: Path, ai_result: AIAnalysisResult):
        """记录低置信度结果到单独日志"""
        confidence = ai_result.confidence
        reason = ai_result.reason
        
        logger.warning(
            f'[AI低置信度] 路径: {path} | 置信度: {confidence:.2f} | '
            f'理由: {reason} | 映射数量: {len(ai_result.mapping)}'
        )
        
        # 记录季度映射
        if ai_result.season_mapping:
            logger.warning(f'[AI低置信度] 季度映射: {ai_result.season_mapping}')
        
        # 详细记录每个映射的置信度
        for mapping in ai_result.mapping:
            if mapping.confidence < self.ai_client.confidence_threshold:
                logger.warning(
                    f'[AI低置信度文件] {mapping.local_file} -> '
                    f'S{mapping.tmdb_season:02d}E{mapping.tmdb_episode:02d} '
                    f'(类型: {mapping.episode_type}, 置信度: {mapping.confidence:.2f})'
                )
        
        # 记录特殊说明
        if ai_result.special_notes:
            logger.warning(f'[AI低置信度] 特殊说明: {ai_result.special_notes}')