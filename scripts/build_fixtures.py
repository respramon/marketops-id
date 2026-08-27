"""Regenerate the sanitized fixture set.

The fixtures are a **sanitized historical replay**: the JSON shapes are exactly
what Sectors API v2 returns (verified against docs.sectors.app/schema.json),
the tickers are real IDX names, and every number - transaction values,
percentages, price changes, flow figures - is synthetic and chosen to exercise
a specific scoring path. Nothing here is live market data and nothing here is
a claim about what any company actually did.

Running this script is deterministic: no clock, no randomness. Re-running it
produces byte-identical files, which is what lets the demo and the test-suite
depend on exact scores.

    python scripts/build_fixtures.py
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "fixtures" / "sanitized"

AS_OF = date(2026, 8, 25)
LABEL = "SANITIZED HISTORICAL REPLAY - NOT LIVE MARKET DATA"
NOTE = (
    "Shapes verified against https://docs.sectors.app/schema.json (OpenAPI 3.0.3, "
    "Sectors API v2.0.0). Tickers are real IDX symbols; all figures are synthetic "
    "and exist only to exercise deterministic scoring paths."
)


def meta(extra: str = "") -> dict[str, object]:
    return {
        "label": LABEL,
        "as_of": AS_OF.isoformat(),
        "note": (NOTE + (" " + extra if extra else "")).strip(),
    }


def weekdays_back(anchor: date, count: int) -> list[date]:
    """The ``count`` most recent weekdays ending at ``anchor``, oldest first."""
    days: list[date] = []
    cursor = anchor
    while len(days) < count:
        if cursor.weekday() < 5:
            days.append(cursor)
        cursor -= timedelta(days=1)
    return sorted(days)


def pagination(n: int) -> dict[str, object]:
    return {
        "total_count": n,
        "showing": n,
        "limit": 30,
        "offset": 0,
        "has_next": False,
        "has_previous": False,
        "next_offset": None,
        "previous_offset": None,
    }


# ---------------------------------------------------------------------------
# filings  -> GET /v2/filings/
# ---------------------------------------------------------------------------
def build_filings() -> dict[str, object]:
    results = [
        {
            # ANTM: big insider accumulation. Crosses BOTH filing thresholds.
            "title": "Dana Investasi Nusantara raises stake in Aneka Tambang",
            "body": (
                "Dana Investasi Nusantara acquired 1,412,800,000 shares of Aneka Tambang "
                "at a weighted average price of IDR 2,920, lifting its holding from "
                "6.24% to 8.09% of issued capital."
            ),
            "source": "https://www.idx.co.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_KSEI/LK-24082026-0001-00.pdf",
            "timestamp": "2026-08-24T15:42:11",
            "sector": "basic-materials",
            "sub_sector": "basic-materials",
            "tags": ["insider-trading", "ownership"],
            "symbol": "ANTM.JK",
            "transaction_type": "buy",
            "holder_type": "institution",
            "holder_name": "Dana Investasi Nusantara",
            "holding_before": 14990000000,
            "holding_after": 16402800000,
            "amount_transaction": 1412800000,
            "price": 2920.0,
            "transaction_value": 412537600000.0,
            "price_transaction": [
                {
                    "date": "2026-08-24",
                    "type": "buy",
                    "price": 2920,
                    "amount_transacted": 1412800000,
                }
            ],
            "share_percentage_before": 6.24,
            "share_percentage_after": 8.09,
            "share_percentage_transaction": 1.85,
            "idx_investor_slug": None,
            "idx_conglomerates_group_slug": None,
        },
        {
            # ADRO: ownership threshold crossed, value threshold NOT crossed.
            "title": "Commissioner discloses share purchase in Alamtri Resources",
            "body": (
                "A member of the board of commissioners disclosed the purchase of "
                "4,150,000 shares at an average price of IDR 2,145."
            ),
            "source": "https://www.idx.co.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_KSEI/LK-24082026-0002-00.pdf",
            "timestamp": "2026-08-24T11:08:53",
            "sector": "energy",
            "sub_sector": "oil-gas-coal",
            "tags": ["insider-trading"],
            "symbol": "ADRO.JK",
            "transaction_type": "buy",
            "holder_type": "insider",
            "holder_name": "Board of Commissioners member",
            "holding_before": 21400000,
            "holding_after": 25550000,
            "amount_transaction": 4150000,
            "price": 2145.0,
            "transaction_value": 8901750000.0,
            "price_transaction": [
                {"date": "2026-08-24", "type": "buy", "price": 2145, "amount_transacted": 4150000}
            ],
            "share_percentage_before": 0.00,
            "share_percentage_after": 0.62,
            "share_percentage_transaction": 0.62,
            "idx_investor_slug": None,
            "idx_conglomerates_group_slug": None,
        },
        {
            # Deliberately malformed: null symbol. Proves normalisation counts
            # and drops bad rows instead of failing the whole run.
            "title": "Filing with an unresolvable issuer reference",
            "body": "Issuer symbol was not present in the source notice.",
            "source": None,
            "timestamp": "2026-08-23T09:15:00",
            "sector": "industrials",
            "sub_sector": "industrial-goods",
            "tags": [],
            "symbol": None,
            "transaction_type": "others",
            "holder_type": None,
            "holder_name": None,
            "holding_before": None,
            "holding_after": None,
            "amount_transaction": None,
            "price": 0.0,
            "transaction_value": None,
            "price_transaction": None,
            "share_percentage_before": None,
            "share_percentage_after": None,
            "share_percentage_transaction": None,
            "idx_investor_slug": None,
            "idx_conglomerates_group_slug": None,
        },
    ]
    return {
        "_meta": meta("Row 3 is intentionally malformed."),
        "results": results,
        "pagination": pagination(len(results)),
    }


# ---------------------------------------------------------------------------
# suspensions -> GET /v2/suspensions/
# ---------------------------------------------------------------------------
def build_suspensions() -> dict[str, object]:
    results = [
        {
            "symbol": "FLMC.JK",
            "suspension_date": "2026-08-25",
            "reason": (
                "Terjadinya peningkatan harga kumulatif yang signifikan pada saham FLMC "
                "(unusual market activity)"
            ),
            "pdf_url": "https://www.idx.co.id/Portals/0/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/Exchange/2026/AUG/20260825-Peng-SPT-FLMC.pdf",
        }
    ]
    return {"_meta": meta(), "results": results, "pagination": pagination(len(results))}


# ---------------------------------------------------------------------------
# movers -> GET /v2/companies/top-changes/?periods=1d
# ---------------------------------------------------------------------------
def build_movers() -> dict[str, object]:
    close = AS_OF.isoformat()
    gainers = [
        # ANTM: >= 7% band
        {
            "name": "PT Aneka Tambang Tbk",
            "symbol": "ANTM.JK",
            "price_change": 0.0842,
            "last_close_price": 3010,
            "latest_close_date": close,
        },
        # BBCA: 3-7% band, and on the analyst watchlist
        {
            "name": "PT Bank Central Asia Tbk",
            "symbol": "BBCA.JK",
            "price_change": 0.034,
            "last_close_price": 9425,
            "latest_close_date": close,
        },
        # Below every threshold - present to prove the queue filters noise out
        {
            "name": "PT Indofood Sukses Makmur Tbk",
            "symbol": "INDF.JK",
            "price_change": 0.0182,
            "last_close_price": 7950,
            "latest_close_date": close,
        },
    ]
    losers = [
        # MDKA: >= 7% band, pairs with a foreign-flow anomaly
        {
            "name": "PT Merdeka Copper Gold Tbk",
            "symbol": "MDKA.JK",
            "price_change": -0.0761,
            "last_close_price": 1815,
            "latest_close_date": close,
        },
        # Below every threshold
        {
            "name": "PT Astra International Tbk",
            "symbol": "ASII.JK",
            "price_change": -0.0114,
            "last_close_price": 5200,
            "latest_close_date": close,
        },
    ]
    return {
        "_meta": meta("INDF and ASII sit below every threshold on purpose."),
        "top_gainers": {"1d": gainers},
        "top_losers": {"1d": losers},
    }


# ---------------------------------------------------------------------------
# news -> GET /v2/news/?symbols=...
# ---------------------------------------------------------------------------
def build_news() -> dict[str, object]:
    results = [
        {
            "title": "Aneka Tambang confirms expanded nickel processing capacity at Halmahera",
            "body": (
                "The company said commissioning of the additional line is scheduled for "
                "the fourth quarter, adding to installed processing capacity."
            ),
            "source": "https://www.example-news.co.id/2026/08/25/antam-halmahera-capacity",
            "thumbnail": None,
            "timestamp": "2026-08-25T08:12:00",
            "sector": "basic-materials",
            "sub_sector": ["basic-materials"],
            "tags": ["Corporate Action", "Operations", "Bullish"],
            "symbols": ["ANTM.JK"],
            "dimension": {
                "future": 1,
                "dividend": 0,
                "ownership": 0,
                "technical": 0,
                "valuation": 0,
                "financials": 1,
                "management": 0,
                "sustainability": 0,
            },
        },
        {
            "title": "Merdeka Copper Gold responds to reports on Tujuh Bukit production guidance",
            "body": (
                "Management issued a clarification to the exchange regarding circulating "
                "reports about full-year production guidance."
            ),
            "source": "https://www.example-news.co.id/2026/08/25/mdka-guidance-clarification",
            "thumbnail": None,
            "timestamp": "2026-08-25T07:40:00",
            "sector": "basic-materials",
            "sub_sector": ["basic-materials"],
            "tags": ["Risk & Compliance", "Operations"],
            "symbols": ["MDKA.JK"],
            "dimension": {
                "future": 0,
                "dividend": 0,
                "ownership": 0,
                "technical": 0,
                "valuation": 0,
                "financials": 0,
                "management": 1,
                "sustainability": 0,
            },
        },
        {
            # Broad-market story naming no candidate: must be ignored, not counted
            # as malformed.
            "title": "Rupiah steadies as Bank Indonesia holds the policy rate",
            "body": "The central bank kept its benchmark rate unchanged at the August meeting.",
            "source": "https://www.example-news.co.id/2026/08/25/bi-rate-hold",
            "thumbnail": None,
            "timestamp": "2026-08-25T06:55:00",
            "sector": "financials",
            "sub_sector": ["banks"],
            "tags": ["Politics & Regulation"],
            "symbols": [],
            "dimension": None,
        },
    ]
    return {
        "_meta": meta("Article 3 names no candidate and is ignored by design."),
        "results": results,
        "pagination": pagination(len(results)),
    }


# ---------------------------------------------------------------------------
# foreign_flow -> GET /v2/foreign-flow/{symbol}/   (keyed by bare ticker)
# ---------------------------------------------------------------------------
def build_foreign_flow() -> dict[str, object]:
    days = weekdays_back(AS_OF, 10)
    start, end = days[0], days[-1]

    def series(values: list[int]) -> dict[str, object]:
        return [
            {"date": d.isoformat(), "net_foreign_inflow": v}
            for d, v in zip(days, values, strict=True)
        ]

    # ANTM: steady flow, latest in line with the baseline -> ratio ~1.0, no event.
    antm = [
        11_200_000_000,
        -9_800_000_000,
        10_400_000_000,
        -11_900_000_000,
        12_100_000_000,
        -10_600_000_000,
        11_500_000_000,
        -9_400_000_000,
        10_900_000_000,
        11_050_000_000,
    ]
    # MDKA: quiet baseline then a very large outflow -> ratio ~4.7 -> +20.
    mdka = [
        2_050_000_000,
        -1_900_000_000,
        2_200_000_000,
        -1_750_000_000,
        2_400_000_000,
        -2_100_000_000,
        1_850_000_000,
        -2_250_000_000,
        2_000_000_000,
        -9_650_000_000,
    ]
    # ADRO: unremarkable.
    adro = [
        3_100_000_000,
        -2_900_000_000,
        3_050_000_000,
        -3_200_000_000,
        2_980_000_000,
        -3_150_000_000,
        3_020_000_000,
        -2_870_000_000,
        3_090_000_000,
        3_180_000_000,
    ]
    # BBCA: large but stable - proves absolute size alone is not an anomaly.
    bbca = [
        52_000_000_000,
        -48_000_000_000,
        51_500_000_000,
        -49_800_000_000,
        53_100_000_000,
        -47_600_000_000,
        50_900_000_000,
        -52_400_000_000,
        49_700_000_000,
        41_200_000_000,
    ]
    # ASII: unremarkable, present so every enriched candidate resolves.
    asii = [
        7_400_000_000,
        -7_100_000_000,
        7_250_000_000,
        -7_600_000_000,
        7_050_000_000,
        -7_350_000_000,
        7_180_000_000,
        -6_980_000_000,
        7_310_000_000,
        7_120_000_000,
    ]
    # INDF: only two usable days -> too little history, must yield no event.
    indf_days = days[-2:]

    out: dict[str, object] = {
        "_meta": meta("Keyed by bare ticker. MDKA is the only genuine anomaly."),
        "ANTM": {
            "symbol": "ANTM.JK",
            "start": start.isoformat(),
            "end": end.isoformat(),
            "data": series(antm),
        },
        "MDKA": {
            "symbol": "MDKA.JK",
            "start": start.isoformat(),
            "end": end.isoformat(),
            "data": series(mdka),
        },
        "ADRO": {
            "symbol": "ADRO.JK",
            "start": start.isoformat(),
            "end": end.isoformat(),
            "data": series(adro),
        },
        "BBCA": {
            "symbol": "BBCA.JK",
            "start": start.isoformat(),
            "end": end.isoformat(),
            "data": series(bbca),
        },
        "ASII": {
            "symbol": "ASII.JK",
            "start": start.isoformat(),
            "end": end.isoformat(),
            "data": series(asii),
        },
        "INDF": {
            "symbol": "INDF.JK",
            "start": indf_days[0].isoformat(),
            "end": indf_days[-1].isoformat(),
            "data": [
                {"date": indf_days[0].isoformat(), "net_foreign_inflow": 1_400_000_000},
                {"date": indf_days[1].isoformat(), "net_foreign_inflow": -8_900_000_000},
            ],
        },
    }
    return out


# ---------------------------------------------------------------------------
# corporate_actions -> GET /v2/company/corporate-actions/{symbol}/
# ---------------------------------------------------------------------------
def build_corporate_actions() -> dict[str, object]:
    soon = (AS_OF + timedelta(days=4)).isoformat()
    payment = (AS_OF + timedelta(days=25)).isoformat()
    return {
        "_meta": meta("Only BBCA has an action inside the 7-day window."),
        "BBCA": {
            "symbol": "BBCA.JK",
            "corporate_actions": {
                "agm": [],
                "bonus": None,
                "warrant": None,
                "dividend": [
                    {
                        "ex_date": "2025-12-03",
                        "payment_date": "2025-12-22",
                        "dividend_yield": 0.00641717,
                        "dividend_amount": 55,
                    }
                ],
                "right_issue": None,
                "stock_split": [{"date": "2021-10-13", "split_ratio": 5}],
                "upcoming_dividend": [
                    {
                        "ex_date": soon,
                        "payment_date": payment,
                        "dividend_yield": 0.0121,
                        "dividend_amount": 114,
                    }
                ],
            },
        },
        "ANTM": {
            "symbol": "ANTM.JK",
            "corporate_actions": {
                "agm": [
                    {
                        "agm_date": "2026-05-14",
                        "agm_time": "14:00:00",
                        "agm_place": "Jakarta",
                        "agm_result": None,
                    }
                ],
                "bonus": None,
                "warrant": None,
                "dividend": [
                    {
                        "ex_date": "2026-06-11",
                        "payment_date": "2026-07-02",
                        "dividend_yield": 0.0289,
                        "dividend_amount": 84,
                    }
                ],
                "right_issue": None,
                "stock_split": None,
                "upcoming_dividend": None,
            },
        },
        "MDKA": {
            "symbol": "MDKA.JK",
            "corporate_actions": {
                "agm": [],
                "bonus": None,
                "warrant": None,
                "dividend": [],
                "right_issue": None,
                "stock_split": None,
                "upcoming_dividend": None,
            },
        },
        "ADRO": {
            "symbol": "ADRO.JK",
            "corporate_actions": {
                "agm": [],
                "bonus": None,
                "warrant": None,
                "dividend": [
                    {
                        "ex_date": "2026-04-08",
                        "payment_date": "2026-04-29",
                        "dividend_yield": 0.0912,
                        "dividend_amount": 196,
                    }
                ],
                "right_issue": None,
                "stock_split": None,
                "upcoming_dividend": None,
            },
        },
        "INDF": {
            "symbol": "INDF.JK",
            "corporate_actions": {
                "agm": [],
                "bonus": None,
                "warrant": None,
                "dividend": [],
                "right_issue": None,
                "stock_split": None,
                "upcoming_dividend": None,
            },
        },
        "ASII": {
            "symbol": "ASII.JK",
            "corporate_actions": {
                "agm": [],
                "bonus": None,
                "warrant": None,
                "dividend": [
                    {
                        "ex_date": "2026-05-20",
                        "payment_date": "2026-06-10",
                        "dividend_yield": 0.0642,
                        "dividend_amount": 334,
                    }
                ],
                "right_issue": None,
                "stock_split": None,
                "upcoming_dividend": None,
            },
        },
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    files = {
        "_meta": {
            "label": LABEL,
            "as_of": AS_OF.isoformat(),
            "note": NOTE,
            "scenarios": {
                "FLMC": "IDX trading suspension -> score override to 100 (P1)",
                "ANTM": "filing + large ownership + large value + >=7% move + news -> 75 (P1)",
                "MDKA": ">=7% move + 4.7x foreign-flow anomaly + news -> 50 (P2)",
                "ADRO": "filing + ownership threshold only -> 35 (P3)",
                "BBCA": "3-7% move + upcoming dividend + watchlist bonus -> 25 (P3)",
                "INDF": "below every threshold -> not queued",
                "ASII": "below every threshold -> not queued",
            },
        },
        "filings": build_filings(),
        "suspensions": build_suspensions(),
        "movers": build_movers(),
        "news": build_news(),
        "foreign_flow": build_foreign_flow(),
        "corporate_actions": build_corporate_actions(),
    }
    for name, payload in files.items():
        path = OUT / f"{name}.json"
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=False) + "\n",
            encoding="utf-8",
        )
        print(f"wrote {path.relative_to(REPO)}")


if __name__ == "__main__":
    main()
