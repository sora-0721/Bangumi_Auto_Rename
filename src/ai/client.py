import json
from typing import Dict, List, Optional, Tuple
from openai import OpenAI

from ..logger import logger
from ..config.config_manager import cm


class AIClient:
    def __init__(self):
        self.api_key = cm.get_config('ai_api_key')
        self.base_url = cm.get_config('ai_base_url')
        self.model = cm.get_config('ai_model')
        self.enabled = cm.get_config('ai_enabled')
        self.confidence_threshold = float(cm.get_config('ai_confidence_threshold') or 0.7)
        
        if self.enabled and self.api_key:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
        else:
            self.client = None

    def is_available(self) -> bool:
        """检查AI客户端是否可用"""
        return self.enabled and self.client is not None and bool(self.api_key)

    def analyze_episode_mapping(
        self,
        anime_info: Dict,
        local_files: List[Dict],
        season_info: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        分析本地文件与TMDB剧集的映射关系
        
        Args:
            anime_info: TMDB动漫信息
            local_files: 本地文件信息列表，包含文件名、路径、时长等
            season_info: 特定季度信息（可选）
            
        Returns:
            包含映射结果、置信度和理由的字典
        """
        if not self.is_available():
            logger.warning('[AI识别] AI功能未启用或配置不完整')
            return None

        try:
            prompt = self._build_analysis_prompt(anime_info, local_files, season_info)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的动漫文件重命名助手。你需要分析本地动漫文件与TMDB数据库中剧集信息的对应关系，特别关注动漫BD发布与官方分季的差异。请以JSON格式返回分析结果。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # 记录低置信度结果
            if result.get('confidence', 0) < self.confidence_threshold:
                logger.warning(
                    f'[AI识别] 低置信度结果 (置信度: {result.get("confidence", 0):.2f}): '
                    f'{result.get("reason", "无理由说明")}'
                )
            
            logger.info(f'[AI识别] 分析完成，置信度: {result.get("confidence", 0):.2f}')
            return result
            
        except Exception as e:
            logger.error(f'[AI识别] 分析失败: {str(e)}')
            return None

    def _build_analysis_prompt(
        self,
        anime_info: Dict,
        local_files: List[Dict],
        season_info: Optional[Dict] = None
    ) -> str:
        """构建分析提示词"""
        
        # 构建TMDB信息
        tmdb_info = f"""
动漫名称: {anime_info.get('name', '未知')}
首播日期: {anime_info.get('first_air_date', '未知')}
总季数: {anime_info.get('number_of_seasons', 0)}
总集数: {anime_info.get('number_of_episodes', 0)}
"""
        
        # 构建季度信息
        seasons_info = ""
        if anime_info.get('seasons'):
            seasons_info = "季度信息:\n"
            for season in anime_info['seasons']:
                seasons_info += f"  第{season['season_number']}季: {season['name']} ({season['episode_count']}集)\n"
        
        # 构建本地文件信息
        files_info = "本地文件信息:\n"
        for i, file_info in enumerate(local_files, 1):
            duration_str = ""
            if file_info.get('duration'):
                duration_str = f" (时长: {file_info['duration']:.1f}分钟)"
            files_info += f"  {i}. {file_info['filename']}{duration_str}\n"
        
        prompt = f"""
请分析以下动漫的本地文件与TMDB数据的对应关系：

{tmdb_info}

{seasons_info}

{files_info}

请特别注意以下常见情况：
1. 字幕组可能将多季合并为一个目录
2. OVA/特典可能被放在正片季度末尾，而非第0季
3. 不同季度可能仅用名称区分，没有明确季号
4. 剧场版可能被混在TV版中
5. 根据文件时长判断是否为正片（通常20-25分钟）还是特典/PV等

请返回JSON格式的分析结果，包含以下字段：
{{
    "confidence": 0.85,  // 置信度 (0-1)
    "reason": "分析理由说明",
    "mapping": [
        {{
            "local_file": "文件名",
            "tmdb_season": 1,
            "tmdb_episode": 1,
            "episode_type": "regular|special|ova|movie",
            "confidence": 0.9
        }}
    ],
    "season_mapping": {{
        "local_season_1": 1,  // 本地第1季对应TMDB第1季
        "local_season_2": 2
    }},
    "special_notes": "特殊情况说明"
}}
"""
        return prompt