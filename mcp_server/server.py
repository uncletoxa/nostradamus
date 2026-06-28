"""Nostradamus MCP server — exposes app data operations as MCP tools."""
import sys
import os
from datetime import datetime, timezone

# Bootstrap Django before importing any app models
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nostradamus.settings")

import django
django.setup()

from mcp.server.fastmcp import FastMCP
from predictions.models import Coefficient
from matches.models import Match, Team

mcp = FastMCP("nostradamus")


@mcp.tool()
def write_odds(
    match_id: int,
    home_win: float,
    guest_win: float,
    tie: float | None = None,
    tie_home_win: float | None = None,
    tie_guest_win: float | None = None,
    score: dict | None = None,
) -> str:
    """Create or update betting odds for a match (saved as unpublished).

    Always saves with coef_ready=False. Call publish_odds() separately to make
    the odds visible to users. Fields tie/tie_home_win/tie_guest_win are only
    relevant for playoff matches.

    Args:
        match_id: Primary key of the Match.
        home_win: Decimal odds for a home-team win (e.g. 2.10).
        guest_win: Decimal odds for a guest-team win.
        tie: Decimal odds for a draw (regular-time). None for playoff matches.
        tie_home_win: Odds for home team advancing after a draw.
        tie_guest_win: Odds for guest team advancing after a draw.
        score: JSON dict of score-line odds (e.g. {"1:0": 5.5, "0:0": 8.0}).
    """
    try:
        match = Match.objects.get(pk=match_id)
    except Match.DoesNotExist:
        return f"Error: match with id={match_id} does not exist."

    coef, created = Coefficient.objects.update_or_create(
        match_id=match,
        defaults=dict(
            home_win=home_win,
            guest_win=guest_win,
            tie=tie,
            tie_home_win=tie_home_win,
            tie_guest_win=tie_guest_win,
            score=score or {},
            coef_ready=False,
            update_time=datetime.now(timezone.utc)))

    action = "Created" if created else "Updated"
    return (
        f"{action} odds for match '{match}' (id={match_id}): "
        f"home_win={home_win}, guest_win={guest_win}, tie={tie}. "
        f"Call publish_odds({match_id}) to make them visible."
    )


@mcp.tool()
def write_knockout_odds(
    match_id: int,
    odds_1: float,
    odds_x: float,
    odds_2: float,
    odds_home_qualify: float,
    odds_away_qualify: float,
    score: dict | None = None,
) -> str:
    """Calculate and save knockout-match odds from 1X2 and To Qualify markets.

    Derives home_win, guest_win, tie_home_win, tie_guest_win from 5 market
    values. Regular-time 1X2 gives the base result probabilities; To Qualify
    captures who actually advances, so the penalty-shootout probability equals
    P(team qualifies) − P(team wins in regular time). All probabilities are
    normalised before arithmetic to remove the bookmaker margin. tie is always
    saved as None for knockout matches. Saves with coef_ready=False.

    Args:
        match_id: Primary key of the Match.
        odds_1: Regular-time home win odds (1X2 market).
        odds_x: Regular-time draw odds (1X2 market).
        odds_2: Regular-time away win odds (1X2 market).
        odds_home_qualify: Home team to qualify (advance) odds.
        odds_away_qualify: Away team to qualify (advance) odds.
        score: JSON dict of score-line odds (e.g. {"1:0": 5.5, "0:0": 8.0}).
    """
    try:
        match = Match.objects.get(pk=match_id)
    except Match.DoesNotExist:
        return f"Error: match with id={match_id} does not exist."

    # Convert to probabilities
    p1, px, p2 = 1 / odds_1, 1 / odds_x, 1 / odds_2
    p_hq, p_aq = 1 / odds_home_qualify, 1 / odds_away_qualify

    # Normalise to remove bookmaker margin
    total_12 = p1 + px + p2
    p1_n, p2_n = p1 / total_12, p2 / total_12

    total_q = p_hq + p_aq
    p_hq_n, p_aq_n = p_hq / total_q, p_aq / total_q

    # Penalty-shootout probabilities = qualifier share minus regular-time win share
    p_home_pen = p_hq_n - p1_n
    p_away_pen = p_aq_n - p2_n

    if p_home_pen <= 0 or p_away_pen <= 0:
        return (
            f"Error: implied penalty probability is non-positive "
            f"(home={p_home_pen:.4f}, away={p_away_pen:.4f}). "
            "Check that To Qualify odds are shorter than the 1X2 win odds."
        )

    home_win = round(1 / p1_n, 2)
    guest_win = round(1 / p2_n, 2)
    tie_home_win = round(1 / p_home_pen, 2)
    tie_guest_win = round(1 / p_away_pen, 2)

    coef, created = Coefficient.objects.update_or_create(
        match_id=match,
        defaults=dict(
            home_win=home_win,
            guest_win=guest_win,
            tie=None,
            tie_home_win=tie_home_win,
            tie_guest_win=tie_guest_win,
            score=score or {},
            coef_ready=False,
            update_time=datetime.now(timezone.utc)))

    action = "Created" if created else "Updated"
    return (
        f"{action} knockout odds for match '{match}' (id={match_id}): "
        f"home_win={home_win}, guest_win={guest_win}, "
        f"tie_home_win={tie_home_win}, tie_guest_win={tie_guest_win}. "
        f"Call publish_odds({match_id}) to make them visible."
    )


@mcp.tool()
def publish_odds(match_id: int) -> str:
    """Publish odds for a match, making them visible to users.

    Odds must have been written first with write_odds(). Requires a separate
    explicit call to prevent accidental publishing.

    Args:
        match_id: Primary key of the Match.
    """
    try:
        coef = Coefficient.objects.get(match_id=match_id)
    except Coefficient.DoesNotExist:
        return f"Error: no odds found for match id={match_id}. Call write_odds() first."

    coef.coef_ready = True
    coef.save()
    return f"Odds for match id={match_id} are now published (coef_ready=True)."


@mcp.tool()
def list_matches() -> list[dict]:
    """Return all matches ordered by start time."""
    return [
        {
            "id": m.match_id,
            "home_team": str(m.home_team),
            "guest_team": str(m.guest_team),
            "start_time": m.start_time.isoformat(),
            "status": m.status,
            "result": m.result if m.home_score is not None else None,
            "is_playoff": m.is_playoff,
        }
        for m in Match.objects.select_related("home_team", "guest_team").order_by("start_time")]


@mcp.tool()
def list_odds(match_id: int) -> dict | str:
    """Return the current odds for a specific match.

    Args:
        match_id: Primary key of the Match.
    """
    try:
        coef = Coefficient.objects.select_related("match_id").get(match_id=match_id)
    except Coefficient.DoesNotExist:
        return f"Error: no odds found for match id={match_id}."

    return {
        "match": str(coef.match_id),
        "home_win": coef.home_win,
        "guest_win": coef.guest_win,
        "tie": coef.tie,
        "tie_home_win": coef.tie_home_win,
        "tie_guest_win": coef.tie_guest_win,
        "score": coef.score,
        "coef_ready": coef.coef_ready,
        "update_time": coef.update_time.isoformat(),
    }


@mcp.tool()
def list_teams() -> list[dict]:
    """Return all teams with their id, name, code, and emoji."""
    return [
        {
            "id": t.team_id,
            "name": t.name,
            "code": t.code,
            "emoji": t.emoji_symbol,
        }
        for t in Team.objects.order_by("name")]


if __name__ == "__main__":
    mcp.run()
