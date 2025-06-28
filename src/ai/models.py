from typing import Dict, List, Optional, Union, Literal
from pydantic import BaseModel, Field, validator


class EpisodeMapping(BaseModel):
    """单个剧集映射"""
    local_file: str = Field(..., description="本地文件名")
    tmdb_season: int = Field(..., ge=0, description="TMDB季号")
    tmdb_episode: int = Field(..., ge=1, description="TMDB集号")
    episode_type: Literal["regular", "special", "ova", "movie"] = Field(
        default="regular", description="剧集类型"
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度")


class AIAnalysisResult(BaseModel):
    """AI分析结果"""
    confidence: float = Field(..., ge=0.0, le=1.0, description="总体置信度")
    reason: str = Field(..., description="分析理由说明")
    season_mapping: Dict[str, Union[int, List[int]]] = Field(
        default_factory=dict, 
        description="季度映射，本地季对应TMDB季的映射关系"
    )
    mapping: List[EpisodeMapping] = Field(
        default_factory=list, description="剧集映射列表"
    )
    special_notes: Optional[str] = Field(
        default=None, description="特殊情况说明"
    )

    @validator('season_mapping')
    def validate_season_mapping(cls, v):
        """验证season_mapping格式"""
        if not isinstance(v, dict):
            raise ValueError("season_mapping必须是字典类型")
        
        for key, value in v.items():
            # 键必须是字符串格式的本地季号
            if not key.startswith('local_season_'):
                raise ValueError(f"season_mapping的键必须以'local_season_'开头: {key}")
            
            # 值必须是整数或整数列表
            if isinstance(value, int):
                if value < 0:
                    raise ValueError(f"季号不能为负数: {value}")
            elif isinstance(value, list):
                if not all(isinstance(x, int) and x >= 0 for x in value):
                    raise ValueError(f"季号列表必须包含非负整数: {value}")
            else:
                raise ValueError(f"season_mapping的值必须是整数或整数列表: {value}")
        
        return v

    @validator('mapping')
    def validate_mapping_not_empty(cls, v, values):
        """验证映射列表不为空（当置信度足够高时）"""
        confidence = values.get('confidence', 0)
        if confidence > 0.5 and not v:
            raise ValueError("高置信度结果必须包含映射信息")
        return v

    class Config:
        # 允许额外字段，但会发出警告
        extra = "forbid"
        # JSON序列化时使用字段别名
        allow_population_by_field_name = True