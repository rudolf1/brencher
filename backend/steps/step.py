from abc import ABC, abstractmethod

class AbstractStep(ABC):

    @abstractmethod
    def progress(self):
        pass
