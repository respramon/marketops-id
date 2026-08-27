"""MarketOps ID - Autonomous IDX research triage.

Monitors Indonesian market events through the Sectors Financial API v2,
correlates evidence per ticker, scores what deserves an analyst's attention
first, and delivers a deduplicated research queue on a schedule.

This package performs monitoring, correlation, triage, scoring and alerting.
It does not produce buy/sell recommendations, price targets, trading signals,
or brokerage execution of any kind.
"""

__version__ = "1.0.0"

DISCLAIMER = (
    "Research triage only. MarketOps ID does not provide investment "
    "recommendations and does not execute trades."
)

__all__ = ["DISCLAIMER", "__version__"]
