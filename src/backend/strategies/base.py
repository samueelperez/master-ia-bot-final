from abc import ABC, abstractmethod
import pandas as pd
from typing import List, Dict, Any

class BaseStrategy(ABC):
    metadata: Dict[str, Any]

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> List[Dict[str, float]]:
        """
        Recibe un DataFrame OHLCV y devuelve una lista de señales:
          [{"entry":…, "sl":…, "tp":…}, …]
        """
        pass
