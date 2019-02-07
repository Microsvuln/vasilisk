from abc import ABC, abstractmethod


class BaseFuzzer(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def generate(self):
        """ Generates Test Case From Grammar"""
        pass

    @abstractmethod
    def validate(self, output):
        pass
