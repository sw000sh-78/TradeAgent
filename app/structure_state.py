from collections import defaultdict

class MarketStructureState:
    def __init__(self):
        self._states = defaultdict(lambda: "unknown")

    def transition(self, symbol: str, structure: str) -> str:
        previous = self._states[symbol]
        if previous == structure:
            return f"unchanged ({structure})"

        self._states[symbol] = structure
        if previous == "unknown":
            return f"initialized to {structure}"
        return f"changed from {previous} to {structure}"

    def current(self, symbol: str) -> str:
        return self._states[symbol]
