from abc import ABC, abstractmethod

class BaseAnalyzer(ABC):
    @abstractmethod
    def eda(self, file_path: str) -> dict:
        pass

    @abstractmethod
    def drift(self, base_path: str, target_path: str) -> dict:
        pass