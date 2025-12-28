from mukitodo.actions import Result, EmptyResult

class MessageHolder:
    """Shared message holder that all states can access."""
    def __init__(self):
        self._last_result: Result = EmptyResult
    
    @property
    def last_result(self) -> Result:
        return self._last_result
    
    def set(self, result: Result) -> None:
        self._last_result = result
    
    def clear(self) -> None:
        self._last_result = EmptyResult

