import re
from time import sleep
from typing import Dict, List, Optional, Any

import tmdbsimple as tmdb

from ..logger import logger
from ..config.config_manager import cm
from .cleaner import is_chinese_percentage_sufficient


class Search:
    def __init__(self) -> None:
        self.TMDB_KEY = cm.get_config('api_key')
        tmdb.API_KEY = self.TMDB_KEY

    def get_season_info(self, tv_id: int, season_number: int) -> Optional[Dict[str, Any]]:
        """
        获取指定季度的详细信息，包括剧集列表
        
        Args:
            tv_id: 电视剧ID
            season_number: 季度号
            
        Returns:
            筛选后的季度信息字典，失败返回None
        """
        for i in range(3):
            try:
                season = tmdb.TV_Seasons(tv_id, season_number)
                season_info = season.info()
                
                if not season_info:
                    logger.warning(f'[季度信息] 未获取到Season {season_number}的信息')
                    return None
                
                # 筛选季度信息，只保留需要的字段
                filtered_season = {
                    'air_date': season_info.get('air_date'),
                    'episode_count': season_info.get('episode_count', 0),
                    'id': season_info.get('id'),
                    'name': season_info.get('name', ''),
                    'overview': season_info.get('overview', ''),
                    'season_number': season_info.get('season_number', season_number),
                    'episodes': []
                }
                
                # 处理剧集信息
                episodes = season_info.get('episodes', [])
                for episode in episodes:
                    filtered_episode = {
                        'air_date': episode.get('air_date'),
                        'episode_number': episode.get('episode_number'),
                        'episode_type': episode.get('episode_type', 'regular'),
                        'name': episode.get('name', ''),
                        'overview': episode.get('overview', ''),
                        'runtime': episode.get('runtime'),
                        'season_number': episode.get('season_number', season_number)
                    }
                    filtered_season['episodes'].append(filtered_episode)
                
                logger.info(f'[季度信息] 获取Season {season_number}信息成功，包含{len(filtered_season["episodes"])}集')
                return filtered_season
                
            except Exception as e:
                logger.warning(f'[季度信息] 获取Season {season_number}信息失败，重试第{i + 1}次: {str(e)}')
                sleep(5)
        
        logger.error(f'[季度信息] 获取Season {season_number}信息最终失败')
        return None

    def get_tv_info_with_seasons(self, query: str, year: int) -> tuple[str, Optional[Dict[str, Any]]]:
        """
        获取电视剧信息，包含详细的季度和剧集信息
        
        Args:
            query: 搜索关键词
            year: 年份
            
        Returns:
            (剧集名称, 包含详细季度信息的tv_info字典)
        """
        # 首先获取基本的电视剧信息
        name, tv_info = self.get_tv_info(query, year)
        
        if not name or not tv_info:
            return name, tv_info
        
        # 获取电视剧ID
        tv_id = tv_info.get('id')
        if not tv_id:
            logger.error('[季度信息] 无法获取电视剧ID')
            return name, tv_info
        
        # 获取原始季度列表
        original_seasons = tv_info.get('seasons', [])
        if not original_seasons:
            logger.warning('[季度信息] 电视剧没有季度信息')
            return name, tv_info
        
        # 获取每个季度的详细信息
        detailed_seasons = []
        for season in original_seasons:
            season_number = season.get('season_number')
            if season_number is None:
                logger.warning(f'[季度信息] 跳过无效季度: {season}')
                continue
            
            logger.info(f'[季度信息] 正在获取Season {season_number}的详细信息...')
            detailed_season = self.get_season_info(tv_id, season_number)
            
            if detailed_season:
                detailed_seasons.append(detailed_season)
            else:
                # 如果获取详细信息失败，使用原始信息但添加空的episodes列表
                fallback_season = {
                    'air_date': season.get('air_date'),
                    'episode_count': season.get('episode_count', 0),
                    'id': season.get('id'),
                    'name': season.get('name', ''),
                    'overview': season.get('overview', ''),
                    'season_number': season.get('season_number'),
                    'episodes': []
                }
                detailed_seasons.append(fallback_season)
                logger.warning(f'[季度信息] Season {season_number}使用基础信息')
        
        # 用详细的季度信息替换原始的seasons字段
        tv_info['seasons'] = detailed_seasons
        
        logger.info(f'[季度信息] 电视剧《{name}》详细信息获取完成，共{len(detailed_seasons)}个季度')
        return name, tv_info

    def get_movie_info(
        self,
        query: str,
        year: int,
    ):
        for i in range(3):
            try:
                search = tmdb.Search()
                search.movie(
                    query=query,
                    language='zh-CN',
                    year=year if year != 0 else None,
                )
                target_list = search.__dict__['results']
                if target_list:
                    target = target_list[0]
                    name = target['title']
                    movie = tmdb.Movies(target['id'])
                    movie.info()
                    logger.debug(str(movie.__dict__))
                    return name, movie.__dict__
                return '', None
            except:  # noqa:E722, B001
                sleep(5)
                logger.warning(f'[电影搜索] 网络错误, 重试第{i + 1}次中...')
        return '', None

    def get_tv_info(
        self,
        query: str,
        year: int,
    ):
        for i in range(3):
            try:
                for _ in range(3):
                    search = tmdb.Search()
                    search.tv(
                        query=query,
                        language='zh-CN',
                        first_air_date_year=year if year != 0 else None,
                    )
                    target_list = search.__dict__['results']
                    if target_list:
                        target = target_list[0]
                        name = target['name']
                        tv = tmdb.TV(target['id'])
                        tv.info()
                        logger.debug(str(tv.__dict__))
                        return name, tv.__dict__
                    else:
                        if is_chinese_percentage_sufficient(query):
                            query = re.sub(r'[a-zA-Z]', '', query)
                return '', None
            except:  # noqa:E722, B001
                sleep(5)
                logger.warning(f'[电视剧搜索] 网络错误, 重试第{i + 1}次中...')
        return '', None