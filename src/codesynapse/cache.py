# src/codesynapse/cache.py

import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class ParseCache:
    """파싱 결과를 캐싱하는 클래스"""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        if cache_dir is None:
            cache_dir = Path.home() / '.cache' / 'codesynapse'
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / 'parse_cache.json'
        self.cache = self._load_cache()
    
    def _load_cache(self) -> Dict[str, Any]:
        """캐시 파일 로드"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}")
        return {}
    
    def _save_cache(self):
        """캐시 파일 저장"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2, default=str)
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")
    
    def get_file_hash(self, file_path: Path) -> str:
        """파일의 해시값 계산"""
        stat = file_path.stat()
        # 파일 경로, 크기, 수정 시간을 조합하여 해시 생성
        key = f"{file_path}:{stat.st_size}:{stat.st_mtime}"
        return hashlib.md5(key.encode()).hexdigest()
    
    def get(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """캐시된 파싱 결과 조회"""
        file_hash = self.get_file_hash(file_path)
        cache_key = str(file_path)
        
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if cached.get('hash') == file_hash:
                logger.debug(f"Cache hit for {file_path}")
                return cached.get('data')
        
        logger.debug(f"Cache miss for {file_path}")
        return None
    
    def set(self, file_path: Path, data: Dict[str, Any]):
        """파싱 결과 캐싱"""
        file_hash = self.get_file_hash(file_path)
        cache_key = str(file_path)
        
        self.cache[cache_key] = {
            'hash': file_hash,
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        
        self._save_cache()
        logger.debug(f"Cached result for {file_path}")
    
    def clear(self):
        """캐시 초기화"""
        self.cache = {}
        self._save_cache()
        logger.info("Cache cleared")