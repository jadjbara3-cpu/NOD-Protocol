"""NØD Cognitive Navigation Layer.

Turns the discovery graph into machine-readable discovery infrastructure:
agents ask "what discoveries relate to X?" and receive ranked, verified
answers (Most Verified / Most Used / Fastest Growing / Most Foundational).
"""

from nod_protocol.navigation.navigator import CognitiveNavigator, SemanticIndex, NavigationResult

__all__ = ["CognitiveNavigator", "SemanticIndex", "NavigationResult"]
