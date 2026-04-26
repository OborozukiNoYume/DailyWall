import argparse
import sys
from datetime import datetime

from app.config import settings
from app.database import init_db
from app.logging_utils import configure_logging, get_component_logger
from crawler.crawler import Crawler

logger = get_component_logger("crawl", __name__)

SCHEDULED_MARKET_GROUPS = {
    "00:10": ["zh-CN"],
    "02:40": ["en-IN"],
    "06:10": ["de-DE", "fr-FR", "it-IT", "es-ES"],
    "07:10": ["en-GB"],
    "11:10": ["pt-BR"],
    "12:10": ["en-CA"],
    "15:10": ["en-US"],
    "23:10": ["ja-JP"],
}

DEFAULT_SCHEDULE_WINDOW_MINUTES = 30


def setup_logging():
    return configure_logging("crawl", log_dir=settings.LOG_DIR)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run DailyWall crawl job.")
    parser.add_argument(
        "--markets",
        nargs="+",
        help=(
            "Only crawl specified markets. Accepts space-separated values "
            "or comma-separated groups, for example: zh-CN en-US or zh-CN,en-US."
        ),
    )
    parser.add_argument(
        "--scheduled-markets",
        action="store_true",
        help="Select markets by the current systemd schedule time window.",
    )
    parser.add_argument(
        "--schedule-window-minutes",
        type=int,
        default=DEFAULT_SCHEDULE_WINDOW_MINUTES,
        help=(
            "Allowed delay window for --scheduled-markets. "
            f"Default: {DEFAULT_SCHEDULE_WINDOW_MINUTES}."
        ),
    )
    parser.add_argument(
        "--schedule-time",
        help=(
            "Simulate a local schedule time for --scheduled-markets, "
            "formatted as HH:MM. Example: --schedule-time 06:10."
        ),
    )
    return parser.parse_args(argv)


def _normalize_markets(raw_markets: list[str]) -> list[str]:
    markets: list[str] = []
    for raw in raw_markets:
        for market in raw.split(","):
            market = market.strip()
            if market:
                markets.append(market)
    return markets


def select_scheduled_markets(
    now: datetime | None = None,
    window_minutes: int = DEFAULT_SCHEDULE_WINDOW_MINUTES,
) -> list[str]:
    if window_minutes <= 0:
        raise ValueError("schedule window must be greater than 0 minutes")

    current = now or datetime.now().astimezone()
    current_minutes = current.hour * 60 + current.minute

    for time_text, markets in SCHEDULED_MARKET_GROUPS.items():
        hour, minute = (int(part) for part in time_text.split(":", 1))
        schedule_minutes = hour * 60 + minute
        if schedule_minutes <= current_minutes < schedule_minutes + window_minutes:
            return markets

    return []


def parse_schedule_time(time_text: str) -> datetime:
    try:
        hour_text, minute_text = time_text.split(":", 1)
        hour = int(hour_text)
        minute = int(minute_text)
    except ValueError as e:
        raise ValueError("schedule time must use HH:MM format") from e

    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError("schedule time must be between 00:00 and 23:59")

    return datetime.now().astimezone().replace(
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0,
    )


def resolve_markets(args: argparse.Namespace) -> list[str]:
    if args.markets and args.scheduled_markets:
        raise ValueError("use either --markets or --scheduled-markets, not both")

    if args.markets:
        markets = _normalize_markets(args.markets)
    elif args.scheduled_markets:
        scheduled_now = (
            parse_schedule_time(args.schedule_time)
            if args.schedule_time
            else None
        )
        markets = select_scheduled_markets(
            now=scheduled_now,
            window_minutes=args.schedule_window_minutes
        )
        if not markets:
            raise ValueError(
                "current time is outside configured scheduled market windows"
            )
    elif args.schedule_time:
        raise ValueError("--schedule-time requires --scheduled-markets")
    else:
        markets = list(settings.MARKETS)

    unsupported = [mkt for mkt in markets if mkt not in settings.MARKETS]
    if unsupported:
        raise ValueError(f"unsupported markets: {', '.join(unsupported)}")

    return markets


def main(argv: list[str] | None = None):
    setup_logging()
    settings.ensure_dirs()
    init_db()
    try:
        args = parse_args(argv or [])
        markets = resolve_markets(args)
    except ValueError as e:
        logger.error("Invalid crawl arguments: %s", e)
        return 1

    logger.info(
        "Starting crawl run for %d markets: %s",
        len(markets),
        ",".join(markets),
    )
    crawler = Crawler(markets=markets)
    result = crawler.run()
    logger.info(
        "Crawl script exit status=%s success=%d fail=%d",
        result.status,
        result.success_count,
        result.fail_count,
    )

    if result.status == "success":
        return 0
    if result.status == "partial":
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
